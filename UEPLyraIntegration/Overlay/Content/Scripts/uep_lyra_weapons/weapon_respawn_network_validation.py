"""Opt-in real PvP death/respawn;no health writes,manual restart or spawn."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture,services
from uep_lyra_abilities import reload_magazine_mixin as ammo
from uep_lyra_hud.notification_relays_network_validation import Network as Relays,identity
from .hero_burst_cue_mixin import lib
from .weapon_lethal_network_validation import Network as Weapon,arg,ability_for,WEAPONS,firing
from .tdm_lethal_network_validation import Network as Lethal,scoring
from .weapon_respawn_network_contract import require,validate,FORBIDDEN

SELECTORS=('/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C',
    '/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C',
    '/Game/Characters/Heroes/Abilities/GA_Hero_Death.GA_Hero_Death_C',
    '/ShooterCore/Game/Respawn/W_RespawnTimer.W_RespawnTimer_C')

class Network(Weapon):
    def __init__(self,result,peer,run):
        super().__init__(result,peer,run)
        self.report.update(dict.fromkeys(FORBIDDEN,False));self.report.update(natural_respawn=True,respawn_scope_closed=False)
        self.life_scope=SubscriptionScope();self.death=None;self.ended=False;self.new_wire=None;self.post_events=[]
        self.post_item=None;self.post_before=None;self.post_actions=[];self.post_pressed=False;self.post_gestures=0
        for path in SELECTORS:
            cls=ue.load_class(path);require('PythonMixinProfile' in cls.get_cdo().properties(),'Missing retained lifecycle selector: '+path)
            if not cls.is_rooted():cls.add_to_root();self.weapon_boot_roots.append(cls)
            self.boot_selectors.append((cls,cls.get_cdo().get_property('PythonMixinProfile')));cls.get_cdo().set_property('PythonMixinProfile',self.profile)

    def setup(self):
        # Reuse the actual typed relay observers,but undo their pre-arm score
        # suppression. Do not take the lethal/postgame fixture's target=1 path.
        Relays.setup(self)
        self.phase_system=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraGamePhaseSubsystem'))
        if self.peer=='server':
            self.scoring.set_property('TargetScore',self.target_score)
            self.authored_target=int(self.target_score);require(self.authored_target>1,'Authored match must allow natural respawn')
            self.initial_tdm=copy.deepcopy(scoring.evidence(self.scoring))
        else:self.scoring=self.state.get_component_by_type(ue.load_class(scoring.CLASS))
        for component in self.components.values():ue.set_mixin_profile(component,self.profile)
        self.stage='roster'

    def arm(self):
        super().arm();pawn=self.players[self.victim]['pawn'];self.old_victim_class=pawn.get_class().get_path_name()
        self.old_victim_wire=copy.deepcopy(self.roster[self.victim]['pawn_wire'])
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
        self.life_scope.bind_event(health,'OnDeathStarted',self.on_death)
        self.life_scope.bind_event(pawn,'OnEndPlay',self.on_old_end)
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.weapon_cls]
        for profile,value in row['profiles'].items():
            base=value['python_class'];attrs={k:v for k,v in vars(base).items() if not k.startswith('__')}
            def observe(handler,selected,kind):
                def invoke(ability,*args):
                    source=identity(ability.call_function('GetAvatarActorFromActorInfo'))
                    if self.stage=='postfire' and source==self.new_wire:
                        self.post_events.append(dict(kind=kind,profile=selected,source_wire=source,authority=bool(ability.call_function('K2_HasAuthority'))))
                    return handler(ability,*args)
                invoke.override='K2_ActivateAbility' if kind=='activate' else 'OnRangedWeaponTargetDataReady';return invoke
            attrs['Activate']=observe(base.Activate,profile,'activate');attrs['TargetData']=observe(base.TargetData,profile,'target-data')
            ue.register_mixin_profile(self.weapon_cls,profile,type('ObservedNewLifeFire'+self.peer+profile,(),attrs))
        self.target_at_arm=int(self.scoring.get_property('TargetScore'))
        self.report['temporary_target_suppression_undone_before_arm']=self.target_at_arm>1

    def on_death(self,pawn):
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
        self.death=dict(observed=True,pawn_wire=identity(pawn),health=float(health.call_function('GetHealth')),zero_health_observed=False,elapsed=time.monotonic()-self.started)
        self.report['death_observation']=copy.deepcopy(self.death)

    def on_old_end(self,pawn,reason):
        self.ended=True;self.life_scope.close();self.report['old_pawn_end_play_observed']=True

    def observe_zero_health(self):
        if self.death is None or self.death['zero_health_observed']:return
        pawn=self.players[self.victim]['pawn']
        if not valid(pawn):return
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
        if valid(health) and float(health.call_function('GetHealth'))==0.:
            self.death['zero_health_observed']=True;self.death['zero_observed_elapsed']=time.monotonic()-self.started
            self.report['death_observation']=copy.deepcopy(self.death)
            atomic_write(self.root/(self.peer+'-native-death-zero.json'),dict(run_id=self.run,death=self.death))

    def pawn_row(self,peer):
        state=self.players[peer]['state'];pawn=state.call_function('GetPawn')
        details=dict(player_state=state.get_path_name(),canonical_pawn_valid=valid(pawn),cached_original_pawn_valid=valid(self.players[peer]['pawn']))
        self.report.setdefault('binding_details',{})[peer]=details
        if valid(pawn):
            location=pawn.get_actor_location();details.update(pawn=pawn.get_path_name(),pawn_wire=identity(pawn),position=[float(location.x),float(location.y),float(location.z)],
                native_role=int(pawn.call_function('GetLocalRole')),destroying=bool(pawn.call_function('IsActorBeingDestroyed')))
        if self.peer!='server' and valid(self.controller.get_controlled_pawn()):
            own=self.controller.get_controlled_pawn().get_actor_location();details['local_position']=[float(own.x),float(own.y),float(own.z)]
        if not valid(pawn) or identity(pawn) is None:return None
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'));asc=ability_system(pawn);state_asc=state.get_property('AbilitySystemComponent')
        details.update(health_component_valid=valid(health),actor_asc_valid=valid(asc),state_asc_valid=valid(state_asc),attribute_health=self.attribute_health(state))
        if valid(health):details.update(health=float(health.call_function('GetHealth')),death_state=int(health.call_function('GetDeathState')),health_set_valid=valid(health.get_property('HealthSet')))
        if not valid(health) or not valid(asc):return None
        return dict(state_wire=identity(state),pawn_wire=identity(pawn),native_class=pawn.get_class().get_path_name(),
            health=float(health.call_function('GetHealth')),attribute_health=self.attribute_health(state),death_state=int(health.call_function('GetDeathState')),
            asc_bound=asc==state_asc and health.get_property('AbilitySystemComponent')==asc and valid(health.get_property('HealthSet')),
            avatar_wire=identity(state_asc.get_property('AvatarActor')),profile=str(ue.get_mixin_profile(pawn)))

    def ready_respawn(self):
        rows={peer:self.pawn_row(peer) for peer in ('A','B0')};self.report['pending_respawn']=rows
        if not self.ended or not all(rows.values()):return None
        if rows[self.victim]['pawn_wire']==self.old_victim_wire:return None
        if not all(r['health']==r['attribute_health']==100. and r['asc_bound'] and r['avatar_wire']==r['pawn_wire'] and r['death_state']==0 for r in rows.values()):return None
        if self.peer in ('server',self.victim):
            controller=self.players[self.victim]['controller'] if self.peer=='server' else self.controller
            pawn=controller.get_controlled_pawn();item=services(controller)[1].call_function('GetActiveSlotItem')
            if not valid(pawn) or identity(pawn)!=rows[self.victim]['pawn_wire'] or not valid(item) or not valid(ability_for(pawn,ue.load_class(WEAPONS['pistol']))):return None
            if not valid(pawn.get_property('InputComponent')) and self.peer==self.victim:return None
            if 'ID_Pistol' not in capture(controller)['definition']:return None
            self.post_item=item;self.post_before=ammo.ammo(item)[0]
        return rows

    def begin_postfire(self):
        self.stage='postfire';self.post_started=time.monotonic()
        if self.peer==self.victim:
            self.post_original_control=self.controller.call_function('GetControlRotation')
            camera=self.controller.get_property('PlayerCameraManager');origin=camera.call_function('GetCameraLocation')
            upward=ue.FVector(origin.x,origin.y,origin.z+10000.)
            self.controller.call_function('SetControlRotation',lib('KismetMathLibrary').call_function('FindLookAtRotation',origin,upward))
            self.post_actions=[ue.load_object(ue.find_class('InputAction'),'/Game/Input/Actions/'+n+'.'+n) for n in ('IA_Weapon_Fire','IA_Weapon_Fire_Auto')]

    def postfire_tick(self):
        if self.peer==self.victim:
            if self.post_pressed:
                for action in self.post_actions:self.controller.inject_enhanced_input_for_action(action,False)
                self.post_pressed=False
            elif not self.post_gestures:
                for action in self.post_actions:self.controller.inject_enhanced_input_for_action(action,True)
                self.post_pressed=True;self.post_gestures=1
        fired=self.token('new-life-fired.json')
        if self.peer in ('server',self.victim):
            current=ammo.ammo(self.post_item)[0]
            if current==self.post_before or not any(e['kind']=='target-data' for e in self.post_events):
                require(time.monotonic()-self.post_started<12.,'New-life real owner fire did not reach native ammo/target data');return
            require(self.post_before-current==1,'New-life gesture consumed more than one native pistol round')
            if self.peer==self.victim:
                if self.post_pressed:return
                atomic_write(self.root/'new-life-fired.json',dict(run_id=self.run,ammo_before=self.post_before,ammo_after=current))
            elif fired is None:return
        elif fired is None:return
        if not all(self.pawn_row(peer) and self.pawn_row(peer)['health']==100. for peer in ('A','B0')):return
        self.make_result()
        atomic_write(self.root/('captured-'+self.peer+'.json'),dict(run_id=self.run))
        self.stage='snapshot-barrier'

    def snapshot_tick(self):
        # Authority cleanup restores scores and poses. Every replica must take
        # its result before that mutation, including the non-firing attacker.
        if not all(self.token('captured-'+peer+'.json') for peer in ('server','A','B0')):return
        self.cleanup();self.report['status']='awaiting_release'
        atomic_write(self.root/('ready-'+self.peer+'.json'),dict(run_id=self.run));self.stage='release'

    def observe_life(self):
        self.observe_zero_health()
        if self.stage=='observe':
            if self.peer==self.attacker:self.drive_weapon()
            if self.death is None:return
            if self.pressed:self.inject(False)
            self.stage='respawn';self.respawn_started=time.monotonic()
        if self.stage=='respawn':
            rows=self.ready_respawn()
            if rows is None:
                require(time.monotonic()-self.respawn_started<45.,'Natural respawn did not restore canonical Pawn/ASC/input/inventory');return
            self.after_respawn=rows;self.new_wire=rows[self.victim]['pawn_wire'];self.respawn_seconds=time.monotonic()-self.respawn_started
            atomic_write(self.root/('respawn-ready-'+self.peer+'.json'),dict(run_id=self.run,pawn_wire=self.new_wire))
            self.stage='respawn-barrier'
        if self.stage=='respawn-barrier':
            if self.peer=='server':
                rows=[self.token('respawn-ready-'+p+'.json') for p in ('A','B0')]
                if not all(rows):return
                require(all(row['pawn_wire']==self.new_wire for row in rows),'Replicated natural replacement identities differ')
                atomic_write(self.root/'respawn-fire.json',dict(run_id=self.run,pawn_wire=self.new_wire))
            command=self.token('respawn-fire.json')
            if command is None:return
            require(command['pawn_wire']==self.new_wire,'Post-respawn fire requested for wrong Pawn');self.begin_postfire()
        if self.stage=='postfire':self.postfire_tick()
        if self.stage=='snapshot-barrier':self.snapshot_tick()

    def make_result(self):
        after=self.stats();before=self.baseline_stats
        row=dict(roster=copy.deepcopy(self.roster),death=copy.deepcopy(self.death),old_pawn_end_play_observed=self.ended,
            old_victim_class=self.old_victim_class,after_respawn=copy.deepcopy(self.after_respawn),after_new_life_fire={p:self.pawn_row(p) for p in ('A','B0')},
            respawn_seconds=self.respawn_seconds,authored_target_score=self.target_at_arm,target_score_at_arm=self.target_at_arm,
            playing_active=False,phase_state_authoritative=self.peer=='server',
            postgame_active=False,score_before=copy.deepcopy(before),score_after=copy.deepcopy(after),
            score_delta={k:after[k]-before[k] for k in ('kills','deaths','team','other')},foreign_inventory_sampled=False)
        from unreal_engine.structs import GameplayTag
        row['playing_active']=bool(self.phase_system.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.Playing')))
        row['postgame_active']=bool(self.phase_system.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.PostGame')))
        if self.peer in ('server',self.attacker):
            row['first_kill_fire']=dict(ammo_before=self.ammo_before,ammo_after=ammo.ammo(self.weapon_item)[0],gestures=self.gestures,
                activation_events=copy.deepcopy(self.weapon_events),target_data_events=copy.deepcopy(self.weapon_data))
            self.report['native_weapon_damage_observed']=any(event['target_hits']>0 for event in self.weapon_data)
        if self.peer in ('server',self.victim):
            row['new_life_fire']=dict(definition_is_pistol=True,ammo_before=self.post_before,ammo_after=ammo.ammo(self.post_item)[0],
                activation_entries=sum(e['kind']=='activate' for e in self.post_events),target_data_entries=sum(e['kind']=='target-data' for e in self.post_events),
                events=copy.deepcopy(self.post_events),gestures=self.post_gestures,input_released=not self.post_pressed)
        self.report['result']=row

    def server_tick(self):
        if self.stage in ('roster','armed'):Lethal.server_tick(self);return
        if self.stage=='release':Lethal.server_tick(self);return
        blocked=self.token('weapon-aim-blocked.json')
        if self.stage=='observe' and not self.weapon_data and blocked and blocked['attempt']==self.pose_attempt:self.pose_attempt+=1;self.place_target()
        self.observe_life()

    def client_tick(self):
        if self.stage=='roster':Lethal.client_tick(self);return
        if self.stage=='release':
            if self.token('release.json'):self.finish()
            return
        self.observe_life()

    def cleanup(self):
        self.life_scope.close();self.report['respawn_scope_closed']=self.life_scope.closed
        for action in self.post_actions:self.controller.inject_enhanced_input_for_action(action,False)
        self.post_pressed=False
        if hasattr(self,'post_original_control'):self.controller.call_function('SetControlRotation',self.post_original_control)
        super().cleanup()

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_WEAPON_RESPAWN_NETWORK_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_WEAPON_RESPAWN_NETWORK_SHUTDOWN_'+self.report['status'].upper())

if any(value.startswith('-UEPWeaponRespawnNetworkResult=') for value in sys.argv):
    validation=Network(arg('UEPWeaponRespawnNetworkResult'),arg('UEPTDMNetworkPeer'),arg('UEPTDMNetworkRun'));atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
