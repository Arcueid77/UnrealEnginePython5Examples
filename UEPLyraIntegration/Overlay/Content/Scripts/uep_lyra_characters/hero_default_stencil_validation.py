"""Actual parent/derived UFunction dispatch and native recursive stencil setters."""
import atexit,hashlib,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from . import hero_default_stencil_mixin as policy,stencil_mixin as stencil
from .hero_default_stencil_contract import FALSE_FIELDS,KINDS,TEAMS,require,validate
CLASSES={'parent':policy.CLASS,'simple-base':'/Game/Characters/Heroes/B_SimpleHeroPawn.B_SimpleHeroPawn_C','simple':'/ShooterExplorer/Blueprint/B_SimpleFollowPawn.B_SimpleFollowPawn_C','big':'/ShooterExplorer/Blueprint/B_SimpleFollowPawn_Big.B_SimpleFollowPawn_Big_C','explorer-hero':'/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C','explorer-pawn':'/ShooterExplorer/Blueprint/B_Pawn_Explorer.B_Pawn_Explorer_C'}
def path(v):return v.get_path_name() if valid(v) else None
def components(a):return list(lib('LyraSystemStatics').call_function('FindComponentsByClass',a,ue.find_class('PrimitiveComponent'),True))
def count(a):return stencil.evidence(a)['python_calls']+stencil.evidence(a)['fallback_calls']
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.actors=[];self.owner=None;self.old_pawn=None;self.state=None;self.rooted=False;self.selector=None;self.index=0
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();self.primary_stencil={path(c):int(c.get_property('CustomDepthStencilValue')) for c in components(self.pawn)};self.shooter_owner_before=ue.describe_function(self.pawn.get_class(),'UpdateCustomStencilFromTeamID')['owner'];self.cls=ue.load_class(policy.CLASS);self.selector=self.cls.get_cdo().get_property(policy.SELECTOR);self.rooted=self.cls.is_rooted()
        if not self.rooted:self.cls.add_to_root()
        ue.register_declared_mixin(self.cls);self.classes={key:ue.load_class(value) for key,value in CLASSES.items()};self.start_profile()
    def spawn(self,kind):
        actor=self.world.actor_spawn(self.classes[kind],ue.FVector(200000.+len(self.actors)*1000.,200000.,2000.));self.actors.append(actor);actor.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);return actor
    def exercise(self,actor,kind):
        ue.set_mixin_profile(actor,self.profile);child_component=actor.add_actor_component(ue.find_class('ChildActorComponent'),'UEPParentStencilChild',actor.get_property('RootComponent'));child_component.call_function('SetChildActorClass',ue.find_class('StaticMeshActor'),None);child=child_component.get_property('ChildActor');require(valid(child),'recursive native ChildActor fixture missing');targets=components(actor);child_targets=components(child);require(child_targets,'recursive child primitive fixture missing');enabled={path(c):bool(c.get_property('bRenderCustomDepth')) for c in targets};row=dict(profile=self.profile,kind=kind,target_function_is_parent_router=actor.find_function('UpdateCustomStencilFromTeamID').get_class().get_name()=='PythonFunction' and ue.describe_function(actor.get_class(),'UpdateCustomStencilFromTeamID')['owner']==policy.CLASS,recursive_child_primitives_present=all(c in targets for c in child_targets),native_locally_and_player_controlled=bool(actor.call_function('IsLocallyControlled')) and bool(actor.call_function('IsPlayerControlled')),values=[])
        for team in TEAMS:
            before=count(actor);actor.call_function('UpdateCustomStencilFromTeamID',team);expected=0 if row['native_locally_and_player_controlled'] else max(0,min(255,team));row['values'].append(dict(team=team,all_components_match_source=all(int(c.get_property('CustomDepthStencilValue'))==expected for c in targets),render_custom_depth_enable_flags_unchanged=all(bool(c.get_property('bRenderCustomDepth'))==enabled[path(c)] for c in targets),parent_route_delta=count(actor)-before))
        self.report['cases'].append(row);ue.clear_mixin_profile(actor)
    def start_profile(self):
        self.profile=('BlueprintFallback','Python')[self.index]
        for kind in KINDS[:-1]:self.exercise(self.spawn(kind),kind)
        self.local=self.spawn('parent');self.owner=self.statics.call_function('CreatePlayer',self.world,-1,True)
        for widget in ue.tobject_iterator(ue.find_class('CommonActivatableWidget')):
            if valid(widget) and widget.call_function('GetOwningPlayer')==self.owner:widget.call_function('DeactivateWidget')
        self.old_pawn=self.owner.get_controlled_pawn();self.state=self.owner.get_property('PlayerState');self.enter('owned-controller')
    def observe(self):
        require(time.monotonic()-self.phase_started<30.,'parent stencil local-controller timeout')
        for widget in ue.tobject_iterator(ue.find_class('CommonActivatableWidget')):
            if valid(widget) and widget.call_function('GetOwningPlayer')==self.owner:widget.call_function('DeactivateWidget')
        if time.monotonic()-self.phase_started<.2:return
        self.owner.call_function('UnPossess')
        if valid(self.old_pawn):self.old_pawn.actor_destroy()
        self.owner.call_function('Possess',self.local);self.exercise(self.local,'local-parent');self.close_player();self.index+=1
        if self.index<2:self.start_profile()
        else:self.finish()
    def close_player(self):
        if valid(self.owner):self.statics.call_function('RemovePlayer',self.owner,True)
        for actor in (self.old_pawn,self.state):
            if valid(actor):actor.actor_destroy()
    def cleanup(self):
        self.close_player()
        for actor in self.actors:
            if valid(actor):ue.clear_mixin_profile(actor);actor.actor_destroy()
        if self.selector is not None:self.cls.get_cdo().set_property(policy.SELECTOR,self.selector)
        if not self.rooted:self.cls.remove_from_root()
        self.report['existing_shooter_child_router_owner_preserved']=ue.describe_function(self.pawn.get_class(),'UpdateCustomStencilFromTeamID')['owner']==self.shooter_owner_before;self.report['primary_player_inventory_health_and_stencil_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before and {path(c):int(c.get_property('CustomDepthStencilValue')) for c in components(self.pawn)}==self.primary_stencil;self.report['owned_contexts_primitives_profiles_roots_and_selectors_restored']=all(not valid(a) for a in self.actors) and all(not valid(a) for a in (self.owner,self.old_pawn,self.state)) and (self.rooted or not self.cls.is_rooted()) and self.cls.get_cdo().get_property(policy.SELECTOR)==self.selector
        baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroStencilDescendantHashes=')));hashes=json.loads(baseline.read_text(encoding='utf-8-sig'));self.report['original_descendant_file_hashes_unchanged']=all(hashlib.sha256(Path(file).read_bytes()).hexdigest().upper()==value.upper() for file,value in hashes.items())
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'parent stencil readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HERO_PARENT_STENCIL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HERO_PARENT_STENCIL_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroParentStencilResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
