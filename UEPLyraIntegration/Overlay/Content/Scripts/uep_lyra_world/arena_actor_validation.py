"""Owned native restart, team/parts delegates, GAS death and physical pickup collision."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities import death_damage
from uep_lyra_characters.team_cosmetics_validation import primitives,material_state
from uep_lyra_weapons import hero_burst_cue_mixin as death_cue
from .effect_pad_mixin import valid,ability_system
from . import arena_actor_mixin as policy
from .arena_actor_contract import validate
FINISH='OnFinish_01E106CD44A9DE9122B131B0ABF28DAC'
EFFECT='/TopDownArena/Game/Pickups/GE_BombRangeUp.GE_BombRangeUp_C'
def arg(n):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'='))
def path(o):return o.get_path_name() if valid(o) else None
def frame():return int(policy.lib('KismetSystemLibrary').call_function('GetFrameCount'))
def game(o):return float(policy.lib('GameplayStatics').call_function('GetTimeSeconds',o))
def visual(actor):
    rows=[]
    for component in primitives(actor):
        materials=component.call_function('GetMaterials') if component.is_a(ue.find_class('MeshComponent')) else []
        rows.append(dict(component=component.get_path_name().replace(actor.get_path_name(),'Actor',1),materials=[material_state(v) for v in materials]))
    return sorted(rows,key=lambda row:row['component'])
class Validation:
    def __init__(self,result):
        self.path=Path(result);self.mode=arg('UEPArenaActorsMode');self.started=time.monotonic();self.finished=False;self.stage='natural';self.roots=[];self.actors=[];self.selectors={};self.controller=None;self.hero=None;self.pickup=None;self.death_counts=None;self.death_started=None;self.death_finished=None
        self.report=dict(status='running',error=None,mode=self.mode,team_cases=[])
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','callbacks_replayed','death_event_sent_by_fixture','health_properties_written','replication_verified','native_tasks_or_delays_replaced'):self.report[k]=False
        self.parent_begins={};self.retained_parent=ue.load_class('/Game/Characters/Character_Default.Character_Default_C');self.root(self.retained_parent);owner=self
        class RetainedParentTrace:
            def ReceiveBeginPlay(actor):
                key=path(actor);owner.parent_begins[key]=owner.parent_begins.get(key,0)+1;return actor.call_mixin_original('ReceiveBeginPlay')
        for profile in ('Python','BlueprintFallback'):ue.register_mixin_profile(self.retained_parent,profile,RetainedParentTrace,make_default=(profile=='Python'))
        cls=ue.load_class('/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default_C');self.root(cls);ue.register_declared_mixin(cls)
        self.classes={k:ue.load_class(v) for k,v in (('hero',policy.HERO),('death',policy.DEATH),('pickup',policy.PICKUP))}
        self.death_cue_class=ue.load_class(death_cue.CLASSES['death']);self.root(self.death_cue_class);ue.register_declared_mixin(self.death_cue_class)
        for cls in self.classes.values():self.root(cls)
        if self.mode!='Baseline':
            for k,cls in self.classes.items():
                selector=policy.SELECTOR if k=='hero' else 'PythonMixinProfile';self.selectors[k]=(selector,cls.get_cdo().get_property(selector));cls.get_cdo().set_property(selector,self.mode);ue.register_declared_mixin(cls)
    def death_sources(self):return dict(Python=policy.LyraArenaDeathPythonProfile,BlueprintFallback=policy.LyraArenaDeathBlueprintFallbackProfile)
    def root(self,o):
        if not o.is_rooted():o.add_to_root();self.roots.append(o)
    def write(self):atomic_write(self.path,self.report)
    def enter(self,name):self.stage=name;self.since=time.monotonic();self.start_frame=frame()
    def discover(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'TopDown' not in world.get_name():continue
            controller=policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
            if not valid(controller):continue
            pawn=controller.get_controlled_pawn();phases=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',world,ue.find_class('LyraGamePhaseSubsystem'))
            if not valid(pawn) or not pawn.is_a(self.classes['hero']) or not phases.call_function('IsPhaseActive',policy.GameplayTag(TagName='ShooterGame.GamePhase.Playing')):continue
            self.world=world;self.report['natural_arena_avatar']=True;self.controller=world.actor_spawn(ue.find_class('LyraPlayerController'));self.actors.append(self.controller);self.state=self.controller.get_property('PlayerState');self.actors.append(self.state);transform=ue.FTransform();transform.translation=ue.FVector(250000.,250000.,3000.);policy.lib('GameplayStatics').call_function('GetGameMode',world).call_function('RestartPlayerAtTransform',self.controller,transform);self.hero=self.controller.get_controlled_pawn();self.actors.append(self.hero)
            if not valid(self.hero):raise RuntimeError('native RestartPlayerAtTransform did not create avatar')
            self.report['owned_avatar_class_preserved']=self.hero.is_a(self.classes['hero']);self.report['visibility']=dict(initially_hidden=bool(self.hero.get_property('bHidden')),created_frame=frame());self.hero.get_property('CharacterMovement').call_function('DisableMovement');self.enter('ready');return
    def ready(self):
        if self.hero.get_property('bHidden') or not valid(ability_system(self.hero)):return
        self.report['visibility'].update(shown=True,shown_frame=frame());self.report['retained_parent_begin_calls']=self.parent_begins.get(path(self.hero),0);manager=ue.new_object(ue.find_class('CheatManager'),self.controller);self.root(manager);self.cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);self.root(self.cheats);self.team_index=0;self.set_team()
    def set_team(self):self.cheats.call_function('SetTeam',(1,2,1)[self.team_index]);self.enter('team')
    def team(self):
        if frame()-self.start_frame<3:return
        result=policy.lib('LyraTeamStatics').call_function('FindTeamFromObject',self.hero,False);team=int(result[1]);asset=result[2];parts=self.hero.get_component_by_type(ue.find_class('LyraPawnComponent_CharacterParts'));spawned=parts.call_function('GetCharacterPartActors');spawned=spawned[0] if isinstance(spawned,tuple) and len(spawned)==1 else spawned;self.report['team_cases'].append(dict(team=team,display_asset=path(asset),visible_parts=len(spawned),visual=visual(self.hero)));self.team_index+=1
        if self.team_index<3:self.set_team();return
        visuals=[r['visual'] for r in self.report['team_cases']];self.report['team_visuals_changed']=visuals[0]!=visuals[1];self.report['team_visuals_restored']=visuals[0]==visuals[2];handle=parts.call_function('AddCharacterPart',LyraCharacterPart(PartClass=ue.find_class('Actor')));parts.call_function('RemoveCharacterPart',handle);self.report['native_parts_add_remove']=True;self.report['hero_counts']=copy.deepcopy(policy.evidence(self.hero));health=self.hero.get_component_by_type(ue.find_class('LyraHealthComponent'));self.report['owned_ability_specs_before_death']=self.specs(self.hero);self.death_target=policy.lib('GameplayStatics').call_function('GetPlayerController',self.world,0).get_controlled_pawn();self.report['natural_ability_specs']=self.specs(self.death_target);self.health_component=self.death_target.get_component_by_type(ue.find_class('LyraHealthComponent'));before=float(self.health_component.call_function('GetHealth'));spec=next(s for s in ability_system(self.death_target).get_property('ActivatableAbilities').Items if valid(s.Ability) and s.Ability.is_a(self.classes['death']));self.death_ability=next(a for a in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(a));self.saved_death_counts=policy.evidence(self.death_ability);self.death_started=game(self.world);self.cues_before=self.cue_counts();death_damage.apply(ability_system(self.death_target),before);self.death_activated=valid(self.death_ability) and bool(self.death_ability.get_property('bIsActive'));self.cue_seen=any(v>self.cues_before.get(k,0) for k,v in self.cue_counts().items());self.enter('death')
    def specs(self,pawn):
        rows=[]
        for spec in ability_system(pawn).get_property('ActivatableAbilities').Items:
            ability=spec.Ability
            if not valid(ability):continue
            rows.append(dict(class_path=ability.get_class().get_path_name(),group=int(ability.get_property('ActivationGroup')),instances=[path(v) for v in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(v)]))
        return rows
    def cue_counts(self):
        result={}
        for actor in ue.tobject_iterator(self.death_cue_class):
            if valid(actor) and valid(actor.call_function('GetOwner')):
                counts=death_cue.evidence(actor);result[path(actor)]=counts['python_burst']+counts['fallback_burst']
        return result
    def dying(self):
        if valid(self.death_ability) and self.death_ability.get_property('bIsActive'):return
        self.death_finished=game(self.world);counts=copy.deepcopy(self.saved_death_counts);self.report['death']=dict(native_lethal_effect=True,ability_class_preserved=True,activated=self.death_activated,finished=True,duration=self.death_finished-self.death_started,dead_or_removed_avatar=not valid(self.death_target) or int(self.health_component.get_property('DeathState'))!=0,native_cue_executed=self.cue_seen,counts=counts);self.enter('pickup-setup')
    def spawn_pickup(self,effect,position):
        t=ue.FTransform();t.translation=position;a=policy.lib('GameplayStatics').call_function('BeginDeferredActorSpawnFromClass',self.world,self.classes['pickup'],t,1,None);self.actors.append(a);a.set_property('GameplayEffectToApply',effect);policy.lib('GameplayStatics').call_function('FinishSpawningActor',a,t);return a
    def pickup_setup(self):
        self.test_pawn=self.world.actor_spawn(ue.find_class('AbilitySystemTestPawn'),ue.FVector(300000.,300000.,3000.));self.actors.append(self.test_pawn);self.test_asc=self.test_pawn.get_property('AbilitySystemComponent');self.test_asc.call_function('K2_InitStats',ue.find_class('TopDownArenaAttributeSet'),None);self.invalid_pawn=self.world.actor_spawn(ue.find_class('LyraCharacter'),ue.FVector(310000.,300000.,3000.));self.actors.append(self.invalid_pawn);self.invalid_pawn.get_property('CharacterMovement').call_function('DisableMovement');self.effect=ue.load_class(EFFECT);self.pickup=self.spawn_pickup(self.effect,ue.FVector(310300.,300000.,3000.));data=policy.lib('AbilitySystemBlueprintLibrary').call_function('GetGameplayEffectUIData',self.effect,ue.find_class('TopDownArenaPickupUIData'));fx=data.get_property('PickupVFX');actual=self.pickup.get_property('VFX').call_function('GetAsset');self.report['pickup']=dict(authority_vfx_matches_ui_data=actual==fx);self.pickup.call_function('OnRep_GameplayEffectToApply');self.report['pickup']['authority_rep_notify_noop']=self.pickup.get_property('VFX').call_function('GetAsset')==actual;self.invalid_pawn.set_actor_location(ue.FVector(310300.,300000.,3000.));self.enter('invalid-overlap')
    def invalid_overlap(self):
        if frame()-self.start_frame<3:return
        self.report['pickup']['no_asc_overlap_keeps_actor']=valid(self.pickup);self.invalid_pawn.set_actor_location(ue.FVector(310000.,300000.,3000.));self.test_pawn.set_actor_location(ue.FVector(310000.,300000.,3000.));self.attribute=next(a for a in self.test_asc.call_function('GetAllAttributes')[0] if str(a.AttributeName)=='BombRange') if isinstance(self.test_asc.call_function('GetAllAttributes'),tuple) else next(a for a in self.test_asc.call_function('GetAllAttributes') if str(a.AttributeName)=='BombRange');self.report['pickup']['attribute_before']=float(policy.lib('AbilitySystemBlueprintLibrary').call_function('GetFloatAttribute',self.test_pawn,self.attribute)[0]);self.pickup_counts=policy.evidence(self.pickup);self.test_pawn.set_actor_location(ue.FVector(310300.,300000.,3000.));self.enter('valid-overlap')
    def valid_overlap(self):
        if frame()-self.start_frame<3:return
        r=self.report['pickup'];r['successful_overlap_destroys_actor']=not valid(self.pickup);r['attribute_after']=float(policy.lib('AbilitySystemBlueprintLibrary').call_function('GetFloatAttribute',self.test_pawn,self.attribute)[0]);r['counts']=copy.deepcopy(self.pickup_counts);empty=self.spawn_pickup(None,ue.FVector(320000.,300000.,3000.));previous=empty.get_property('VFX').call_function('GetAsset');empty.call_function('ChangePickupEffect');r['null_effect_noop']=empty.get_property('VFX').call_function('GetAsset')==previous;self.finish()
    def cleanup(self):
        for a in reversed(self.actors):
            if valid(a):a.actor_destroy()
        if self.mode!='Baseline':
            for key,(selector,value) in self.selectors.items():self.classes[key].get_cdo().set_property(selector,value)
        ue.unregister_mixin(self.retained_parent)
        self.report['selectors_restored']=all(self.classes[k].get_cdo().get_property(s)==v for k,(s,v) in self.selectors.items())
        for o in reversed(self.roots):o.remove_from_root()
        self.report['owned_roots_removed']=all(not o.is_rooted() for o in self.roots);self.report['cleanup_complete']=self.report['selectors_restored'] and self.report['owned_roots_removed']
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>160.:raise RuntimeError('Arena actor validation timeout: '+self.stage)
            {'natural':self.discover,'ready':self.ready,'team':self.team,'death':self.dying,'pickup-setup':self.pickup_setup,'invalid-overlap':self.invalid_overlap,'valid-overlap':self.valid_overlap}[self.stage]();self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_ACTORS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_ACTORS_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaActorsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
