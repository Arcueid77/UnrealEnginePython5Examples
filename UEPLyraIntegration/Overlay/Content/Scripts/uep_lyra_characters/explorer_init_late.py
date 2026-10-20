"""Test-owned delayed controller/component availability; native latent actions run."""
import copy,time
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .health_changed_observation import OwnedAI
from .inventory_wait_transitions import end_owned_respawn
from .inventory_clear_mixin import components
from . import explorer_helpers_mixin as grants,inventory_wait_mixin as waiting
from .explorer_init_mixin import EXPERIENCE_BIND
from .explorer_callbacks_contract import require

SCENARIOS=(('controller',0,False,False),('inventory',1,False,False),('quickbar',2,False,False),('switch-pending',0,True,False),('destroy-pending',0,False,True))
def path(obj):return obj.get_path_name() if valid(obj) else None
def count(actor):return sum(grants.evidence(actor)[n] for n in ('python_grants','fallback_grants'))
def frame():return int(lib('KismetSystemLibrary').call_function('GetFrameCount'))

class LateCase:
    def __init__(self,validation,scenario):
        self.validation,self.world,self.scenario=validation,validation.world,scenario;self.owner=None;self.actor=None;self.started=self.phase_started=time.monotonic();self.phase='owner-ready';self.closed=False
        try:
            validation.pawndata.set_property('PawnClass',validation.classes[validation.kind]);self.owner=OwnedAI(self.world)
        finally:validation.pawndata.set_property('PawnClass',validation.pawnclass)
        self.row=dict(name=scenario[0],kind=validation.kind,initial_profile=validation.profile,final_profile=validation.profile,stage=scenario[1],native_readiness_released=False,grants_while_missing=0,native_wait_resumed_after_availability=False,owned_cleanup=False)
    def enter(self,phase):self.phase,self.phase_started=phase,time.monotonic()
    def spawn(self):
        v=self.validation;stage=self.scenario[1];old=self.owner.pawn;end_owned_respawn(old);old.call_function('ClearInventory');self.owner.controller.call_function('UnPossess')
        mode=lib('GameplayStatics').call_function('GetGameMode',self.world)
        try:
            v.pawndata.set_property('PawnClass',v.classes[v.kind]);self.actor=mode.call_function('SpawnDefaultPawnAtTransform',self.owner.controller,ue.FTransform(ue.FVector(200000.,200000.,2000.)))
        finally:v.pawndata.set_property('PawnClass',v.pawnclass)
        require(valid(self.actor) and self.actor.get_class()==v.classes[v.kind],'native late-ready spawn class differs');old.actor_destroy();self.owner.pawn=self.actor;self.actor.set_property('InitialInventoryItems',[]);ue.set_mixin_profile(self.actor,v.profile);self.actor.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
        if stage:
            cls=ue.find_class(('','LyraInventoryManagerComponent','LyraQuickBarComponent')[stage]);component=self.owner.controller.get_component_by_type(cls);require(valid(component),'owned late-ready component missing before removal');self.removed_class=component.get_class();component.destroy_component();require(not valid(self.owner.controller.get_component_by_type(cls)),'owned component removal failed');self.owner.controller.call_function('Possess',self.actor)
        self.before=count(self.actor);self.wait_values=waiting.evidence(self.actor);self.grant_values=grants.evidence(self.actor);self.row['requests']=2
        for _ in range(2):
            proxy=ue.find_class('AsyncAction_ExperienceReady').get_cdo().call_function('WaitForExperienceReady',self.actor);require(valid(proxy),'native late-ready Experience proxy missing');self.actor.call_function(EXPERIENCE_BIND,proxy);proxy.call_function('Activate')
        self.enter('missing')
    def step(self):
        require(time.monotonic()-self.started<35.,'native late-ready case timeout: '+self.scenario[0]+'/'+self.phase)
        if self.phase=='owner-ready':
            if self.owner.ready():self.spawn()
        elif self.phase=='missing':
            require(count(self.actor)==self.before,'native grant ran while readiness was missing');self.row['grants_while_missing']=count(self.actor)-self.before
            if time.monotonic()-self.phase_started<.12:return False
            if self.scenario[2]:
                target='Python' if self.validation.profile=='BlueprintFallback' else 'BlueprintFallback';ue.set_mixin_profile(self.actor,target);self.row['final_profile']=target
            if self.scenario[3]:
                self.wait_snapshot=copy.deepcopy(self.wait_values);self.grant_snapshot=copy.deepcopy(self.grant_values);self.actor.actor_destroy();self.actor=None;self.owner.pawn=None;self.enter('destroyed');return False
            self.row['available_frame']=frame()
            if self.scenario[1]==0:self.owner.controller.call_function('Possess',self.actor)
            else:self.added=self.owner.controller.add_actor_component(self.removed_class,'UEPExplorerLateReadyComponent')
            self.row['native_readiness_released']=True;self.enter('released')
        elif self.phase=='released':
            expected=2 if self.scenario[1]==0 else 1;actual=count(self.actor)-self.before;require(actual<=expected,'native readiness repeated requests produced extra grants')
            if actual!=expected or time.monotonic()-self.phase_started<.2:return False
            self.row.update(native_grants=actual,native_wait_resumed_after_availability=frame()>=self.row['available_frame'],wait=copy.deepcopy(self.wait_values));self.close();return True
        elif self.phase=='destroyed':
            if time.monotonic()-self.phase_started<.15:return False
            self.row.update(native_grants=0,no_late_work_after_destroy=(self.wait_values,self.grant_values)==(self.wait_snapshot,self.grant_snapshot),native_wait_resumed_after_availability=True);self.close();return True
        return False
    def close(self):
        if self.closed:return
        if valid(self.actor):end_owned_respawn(self.actor)
        if self.owner is not None:
            if self.owner.pawn is None:
                # The intentionally destroyed pending pawn has no live wrapper.
                for actor in (self.owner.controller,self.owner.state):
                    if valid(actor):actor.actor_destroy()
                producer=self.owner.creator
                if valid(producer):producer.call_function('K2_DestroyComponent',producer)
                self.row['owned_cleanup']=all(not valid(a) for a in (self.owner.controller,self.owner.state,producer))
            else:
                result=self.owner.close();self.row['owned_cleanup']=result['owned_pawn_controller_playerstate_producer_destroyed'] and result['original_bot_producer_list_preserved']
            self.owner.creator=None
        self.closed=True
