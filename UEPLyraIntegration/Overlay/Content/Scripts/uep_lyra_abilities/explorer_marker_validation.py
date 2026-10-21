"""Native GAS -> original instant single-line target actor -> real payload/draw."""
import atexit,sys,time,traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_world.inventory_pad_network_state import capture
from uep_lyra_characters.explorer_helpers_validation import Validation as Helpers
from .auto_respawn_helpers_validation import instances
from . import explorer_marker_mixin as policy
from .explorer_marker_contract import FALSE_FIELDS,require,validate
def path(v):return v.get_path_name() if valid(v) else None
def total(a,key):return sum(policy.evidence(a)[p+'_'+key] for p in ('python','fallback'))
class Validation(Ready):
    silence_owned_ui=Helpers.silence_owned_ui
    cancel_owned_abilities=Helpers.cancel_owned_abilities
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.owner=None;self.subject=None;self.state=None;self.ability=None;self.box=None;self.index=0;self.selector=None;self.rooted=False
    def native_targets(self):return [a for a in ue.tobject_iterator(ue.find_class('GameplayAbilityTargetActor_SingleLineTrace')) if valid(a) and a.get_property('PrimaryPC')==self.owner]
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.rooted=self.cls.is_rooted()
        if not self.rooted:self.cls.add_to_root()
        self.start_profile()
    def start_profile(self):
        self.profile=('BlueprintFallback','Python')[self.index];self.current_profile=self.profile;self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True);self.silence_owned_ui();self.subject=self.owner.get_controlled_pawn();self.state=self.owner.get_property('PlayerState');require(valid(self.subject),'owned marker local player missing');self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);self.subject.call_function('K2_SetActorLocation',NewLocation=ue.FVector(200000.,200000.,2000.),bSweep=False,bTeleport=True);self.owner.call_function('SetControlRotation',ue.FRotator());self.owner.call_function('SetViewTargetWithBlend',self.subject,0.,0,0.,False);self.enter('owned-ready')
    def aim(self,name,hit):
        if valid(self.box):self.box.actor_destroy()
        self.box=None
        if hit:
            self.box=self.world.actor_spawn(ue.find_class('Actor'));root=self.box.add_actor_root_component(ue.find_class('BoxComponent'),'UEPMarkerHitBox');root.call_function('SetBoxExtent',ue.FVector(200.,200.,200.),True);root.call_function('SetCollisionProfileName','BlockAll',True);root.call_function('SetCollisionEnabled',1);self.box.call_function('K2_SetActorLocation',NewLocation=ue.FVector(201000.,200000.,2100.),bSweep=False,bTeleport=True)
        self.owner.call_function('SetControlRotation',ue.FRotator(0.,0. if hit else 75.,0.));self.name=name;self.enter('aim')
    def observe(self):
        self.silence_owned_ui();require(time.monotonic()-self.phase_started<25.,'marker phase timeout: '+self.phase)
        if self.phase=='owned-ready':
            asc=ability_system(self.subject)
            if not valid(asc) or asc.get_property('AvatarActor')!=self.subject:return
            if any(spec.ActiveCount and valid(spec.Ability) and spec.Ability.get_class().get_name()=='GA_SpawnEffect_C' for spec in asc.get_property('ActivatableAbilities').Items):self.cancel_owned_abilities(asc,True);return
            self.asc=asc;self.handle=asc.call_function('K2_GiveAbility',self.cls,1,-1);found=instances(asc,self.cls);require(len(found)==1,'unique native marker instance required');self.ability=found[0];ue.set_mixin_profile(self.ability,self.profile);self.aim('hit',True)
        elif self.phase=='aim':
            if time.monotonic()-self.phase_started<.25:return
            self.before={key:total(self.ability,key) for key in ('activate','data','draw')};self.profile_before={p:policy.evidence(self.ability)[p+'_data'] for p in ('python','fallback')};self.activation=bool(self.asc.call_function('TryActivateAbilityByClass',self.cls,False));self.enter('data')
        elif self.phase=='data':
            if total(self.ability,'data')-self.before['data']!=1:return
            values=policy.evidence(self.ability);data=values['last_data'];api=lib('AbilitySystemBlueprintLibrary');has_actor=bool(api.call_function('TargetDataHasActor',data,0));endpoint=api.call_function('GetTargetDataEndPoint',data,0);actors=list(api.call_function('GetActorsFromTargetData',data,0));prefix='python' if self.current_profile=='Python' else 'fallback';center=values['last_center'];row=dict(profile=self.profile,name=self.name,native_activation_succeeded=self.activation,activation_delta=total(self.ability,'activate')-self.before['activate'],data_delta=total(self.ability,'data')-self.before['data'],draw_delta=total(self.ability,'draw')-self.before['draw'],has_actor=has_actor,has_endpoint=bool(api.call_function('TargetDataHasEndPoint',data,0)),expected_box_in_target_data=self.box in actors if valid(self.box) else False,ability_still_active=bool(self.ability.get_property('bIsActive')),draw_center_matches_target_endpoint=center is not None and all(abs(a-b)<.01 for a,b in zip(center,[endpoint.x,endpoint.y,endpoint.z])),current_profile_used=values[prefix+'_data']-self.profile_before[prefix]==1,native_target_actors_and_tasks_closed=not self.ability.get_property('ActiveTasks') and not self.native_targets());self.report['cases'].append(row)
            if self.name=='hit':self.aim('miss',False)
            elif self.name=='miss':self.enter('retry')
            else:
                self.close_context();self.index+=1
                if self.index<2:self.start_profile()
                else:self.finish()
        elif self.phase=='retry':
            before={key:total(self.ability,key) for key in ('activate','data','draw')};accepted=bool(self.asc.call_function('TryActivateAbilityByClass',self.cls,False));self.report['cases'].append(dict(profile=self.profile,name='retry-while-miss-active',native_reactivation_rejected=not accepted,activation_delta=total(self.ability,'activate')-before['activate'],data_delta=total(self.ability,'data')-before['data'],draw_delta=total(self.ability,'draw')-before['draw'],ability_still_active=bool(self.ability.get_property('bIsActive')),native_target_actors_and_tasks_closed=not self.ability.get_property('ActiveTasks') and not self.native_targets()));self.ability.call_function('K2_CancelAbility');self.current_profile='Python' if self.profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(self.ability,self.current_profile);self.aim('switched-reactivation-hit',True)
    def close_context(self):
        if valid(self.ability):
            if self.ability.get_property('bIsActive'):self.ability.call_function('K2_CancelAbility')
            ue.clear_mixin_profile(self.ability)
        if valid(self.box):self.box.actor_destroy()
        if valid(self.owner):self.statics.call_function('RemovePlayer',self.owner,True)
        for actor in (self.subject,self.state):
            if valid(actor):actor.actor_destroy()
    def cleanup(self):
        self.close_context()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        if not self.rooted:self.cls.remove_from_root()
        self.report['owned_contexts_target_actors_roots_and_selectors_restored']=all(not valid(v) for v in (self.owner,self.subject,self.state,self.box)) and (self.rooted or not self.cls.is_rooted()) and self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector;self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'marker readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_MARKER_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_MARKER_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerMarkerResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
