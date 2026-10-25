"""Actual last round -> native cost failure; no synthetic AutoReload grant."""
import copy
import time
import traceback
import unreal_engine as ue
from uep_lyra_abilities import reload_weapon_fixture as fixtures,reload_magazine_mixin as ammo
from uep_lyra_network_io import atomic_write,read_json
from . import netshooter_ability_validation as single,netshooter_network_validation as net
from . import netshooter_ability_mixin as policy
from .netshooter_ammo_contract import validate_standalone

FAILURE = 'ScriptOnAbilityFailedToActivate'


def costs(ability):
    return [dict(native_class=value.get_class().get_path_name(),tag=str(value.get_property('Tag').TagName),
                 failure_tag=str(value.get_property('FailureTag').TagName),quantity=float(value.get_property('Quantity').Value))
            for value in ability.get_property('AdditionalCosts')
            if value.get_class().get_name()=='LyraAbilityCost_ItemTagStack']


def observe_failure(owner,cls):
    owner.failure_function=cls.get_cdo().find_function(FAILURE)
    row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls]
    for profile,record in row['profiles'].items():
        def failed(actor,FailedReason):
            if getattr(owner,'recording',False) or getattr(owner,'armed',False):
                owner.failure_events.append(dict(native_ability=actor.get_path_name(),native_class=actor.get_class().get_path_name(),
                    tags=[str(tag.TagName) for tag in FailedReason.GameplayTags]))
            return actor.call_mixin_original(FAILURE,FailedReason)
        failed.override=FAILURE
        methods={name:value for name,value in vars(record['python_class']).items() if not name.startswith('__') and callable(value)}
        methods['NativeCostFailure']=failed
        ue.register_mixin_profile(cls,profile,type('ObservedNetAmmo'+profile,(),methods))


class Standalone(single.Validation):
    def cue_bindings(self):
        return {name:value['python_class'] for row in ue.get_registered_mixins() if row['target_class']==self.cue_cls for name,value in row['profiles'].items()}

    def observe_cue(self):
        self.cue_cls=ue.load_class(single.CUE);ue.register_declared_mixin(self.cue_cls)
        self.cue_before=self.cue_bindings();self.cue_native_before=self.cue_cls.get_cdo().find_function('OnBurst')
        self.cue_default_before=str(ue.get_mixin_profile(self.cue_cls.get_cdo()))

    def observe(self):
        super().observe();self.failure_events=[];observe_failure(self,self.cls)

    def start_case(self):
        self.profile=('BlueprintFallback','Python')[self.index];self.kind='complete-default'
        ue.set_mixin_profile(self.ability,self.profile)
        self.ability.set_property('CharacterFireMontage',self.original_montage)
        self.ability.set_property('OffsetGCN',self.original_offset)
        self.report['native_cost_configuration']=costs(self.ability)
        self.auto_count=len(fixtures.auto_instances(self.controller));single.require(self.auto_count==0,'Prototype unexpectedly grants AutoReload')
        single.set_stat(self.item,ammo.MAGAZINE,1);single.set_stat(self.item,ammo.SPARE,0)
        self.failure_events=[];self.empty_started=None;self.before_policy=copy.deepcopy(policy.evidence(self.ability))
        self.controller.call_function('SetControlRotation',ue.FRotator(0.,55.,80.));self.enter('aim')

    def case_tick(self):
        self.inject(False)
        if self.empty_started is None:
            if self.game_time()-self.case_started<1.2 or self.ability.get_property('bIsActive'):return
            single.require(ammo.ammo(self.item)[0]==0 and self.activations==self.data_entries==self.spawn_count==1,'Last native round did not exhaust the magazine')
            self.first=dict(activations=self.activations,target_data=self.data_entries,projectiles=self.spawn_count,callbacks=copy.deepcopy(self.callbacks))
            self.failure_events=[];self.empty_started=self.game_time();self.inject(True);return
        if self.game_time()-self.empty_started<1.2:return
        current=policy.evidence(self.ability)
        self.report['cases'].append(dict(profile=self.profile,native_selected_profile=str(ue.get_mixin_profile(self.ability)),
            native_autoreload_grant_count_before=self.auto_count,native_autoreload_grant_count=len(fixtures.auto_instances(self.controller)),input_gestures=2,input_released=True,ammo_before=self.ammo_before,
            ammo_after_last_round=0,ammo_after_empty_attempt=ammo.ammo(self.item)[0],first_shot=self.first,
            after_empty=dict(activations=self.activations,target_data=self.data_entries,projectiles=self.spawn_count,callbacks=copy.deepcopy(self.callbacks)),
            native_failure_events=copy.deepcopy(self.failure_events),ability_ended=not self.ability.get_property('bIsActive'),
            policy_activations={name:current[name]-self.before_policy[name] for name in ('activations','fallback_activations')}))
        self.recording=False;self.index+=1
        if self.index==2:self.finish()
        else:self.start_case()

    def cleanup(self):
        super().cleanup()
        self.report['failure_observer_restored']=self.cls.get_cdo().find_function(FAILURE)==self.failure_function
        self.report['production_cue_binding_preserved']=(self.cue_bindings()==self.cue_before and
            self.cue_cls.get_cdo().find_function('OnBurst')==self.cue_native_before and
            str(ue.get_mixin_profile(self.cue_cls.get_cdo()))==self.cue_default_before)

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate_standalone(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NETSHOOTER_ABILITY_SHUTDOWN_'+self.report['status'].upper())


class AmmoWitness:
    def install(self):
        super().install();self.failure_events=[];self.ammo_cls=ue.load_class(policy.CLASS);observe_failure(self,self.ammo_cls)
        self.report['ammo_exhaustion_only']=True

    def arm(self):
        super().arm();self.failure_events=[]
        controller=self.owners[self.command['owner']]['controller'] if self.peer=='server' else self.controller
        self.auto_count=len(fixtures.auto_instances(controller))
        net.require(self.auto_count==0,'Prototype unexpectedly grants AutoReload')
        ability=self.owners[self.command['owner']]['ability'] if self.peer=='server' else self.own_ability
        self.report['native_cost_configuration']=costs(ability)

    def snapshot(self):
        row=super().snapshot();row.update(native_autoreload_grant_count=self.auto_count,native_failure_events=copy.deepcopy(self.failure_events))
        if self.peer=='server':
            ack=self.acks('done')[self.command['owner']]['row'];row['empty_probe']=copy.deepcopy(ack['empty_probe'])
        return row

    def close_observers(self):
        super().close_observers()
        self.report['failure_observer_restored']=self.ammo_cls.get_cdo().find_function(FAILURE)==self.failure_function


class NetworkClient(AmmoWitness,net.Client):
    def prepare(self):
        result=super().prepare()
        if result:self.empty_started=None;self.empty_probe=None
        return result

    def collect(self):
        if self.pending_row is None:
            owner=self.peer==self.command['owner']
            if owner:
                if self.empty_started is None:
                    if net.base.ammo_policy.ammo(self.item)[0]!=0 or self.own_ability.get_property('bIsActive'):return
                    net.require(len(self.activations)==len(self.target_data)==1,'Last native owner shot missing')
                    self.failure_events=[];self.empty_started=self.game_time();self.input_gestures+=1;self.released=False;self.inject(True);return
                if self.game_time()-self.empty_started<1.2:return
                if self.empty_probe is None:
                    self.empty_probe=dict(owner=self.peer,profile=self.command['profile'],ammo_after=net.base.ammo_policy.ammo(self.item)[0],
                        native_failure_events=copy.deepcopy(self.failure_events),activations=len(self.activations),target_data=len(self.target_data),
                        input_gestures=self.input_gestures,input_released=self.released,native_autoreload_grant_count=len(fixtures.auto_instances(self.controller)))
                    atomic_write(self.root/('empty-'+str(self.position)+'.json'),dict(run_id=self.run,position=self.position,owner=self.peer,profile=self.command['profile']))
            else:
                token=read_json(self.root/('empty-'+str(self.position)+'.json'))
                if token is None:return
                net.require((token['run_id'],token['position'],token['owner'],token['profile'])==(self.run,self.position,self.command['owner'],self.command['profile']),'Foreign empty-input scheduling token')
        super().collect()
        if self.pending_row is not None and self.empty_probe is not None:self.pending_row['empty_probe']=copy.deepcopy(self.empty_probe)

    def acknowledge(self,stage,row):
        if stage=='done' and self.peer==self.command['owner']:row=dict(row,empty_probe=copy.deepcopy(self.empty_probe))
        return super().acknowledge(stage,row)


class NetworkServer(AmmoWitness,net.Server):
    def start(self):
        owner,profile=net.PLAN[self.position];selected=self.owners[owner]
        if selected['ability'].get_property('bIsActive'):return
        self.select_profile(selected['ability'],profile);net.base.set_stat(selected['item'],net.base.ammo_policy.MAGAZINE,1)
        other=next(peer for peer in net.PEERS if peer!=owner)
        self.command=dict(owner=owner,profile=profile,source_identity=net.base.wire.read(selected['pawn']),
            target_identity=net.base.wire.read(self.owners[other]['pawn']),
            ammo_before={peer:net.base.ammo_policy.ammo(value['item'])[0] for peer,value in self.owners.items()},
            players={peer:dict(player_id=value['player_id'],identity=net.base.wire.read(value['pawn'])) for peer,value in self.owners.items()})
        self.arm();self.ammo_before=net.base.ammo_policy.ammo(selected['item'])[0];self.clearing=False;self.publish('prepare')
