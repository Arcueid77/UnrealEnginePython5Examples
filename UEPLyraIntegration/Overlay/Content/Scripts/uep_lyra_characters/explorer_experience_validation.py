"""Actual Explorer inventory Experience, fresh worlds, native input and menus."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_hud import explorer_screens_mixin as screens
from . import begin_play_mixin as beginning
from .explorer_experience_contract import MAP,PROFILES,require,validate

def path(v):return v.get_path_name() if valid(v) else None
def vector(v):return [float(v.x),float(v.y),float(v.z)]

class Validation:
    def __init__(self,result):
        self.path=Path(result);self.started=time.monotonic();self.finished=False;self.phase='warmup';self.phase_started=self.started
        self.world=None;self.pc=None;self.pawn=None;self.input=None;self.action=None;self.classes={};self.roots=[];self.index=0;self.old=[]
        self.profile=next((a.split('=',1)[1] for a in sys.argv if a.startswith('-UEPExplorerExperienceProfile=')),'Python');require(self.profile in PROFILES,'explicit supported Explorer profile required')
        self.report=dict(status='running',error=None,cases=[],selected_class_paths=[],native_level_open_requests=0,
            full_acceptance=False,network_acceptance=False,packaged_runtime=False,pixels_tested=False,physical_input_tested=False,
            cpp_compile_executed=False,cook_package_executed=False,callbacks_replayed=False,inventory_or_health_written=False,
            abilities_granted_by_fixture=False,fixture_actors_spawned=False,selectors_restored=False,actual_exit_finalizer=False)
        self.report['selected_profile']=self.profile
    def write(self):atomic_write(self.path,self.report)
    def enter(self,phase):self.phase=phase;self.phase_started=time.monotonic()
    def context(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or world.get_path_name()!=MAP+'.L_InventoryTestMap':continue
            pc=lib('GameplayStatics').call_function('GetPlayerController',world,0);pawn=pc.get_controlled_pawn() if valid(pc) else None
            if not valid(pawn):continue
            asc=ability_system(pawn);health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
            if not valid(asc) or asc.get_property('AvatarActor')!=pawn or not valid(health) or health.call_function('GetHealth')<=0:continue
            if pawn.get_property('bHidden'):continue
            if any(s.ActiveCount and valid(s.Ability) and s.Ability.get_class().get_name()=='GA_SpawnEffect_C' for s in asc.get_property('ActivatableAbilities').Items):continue
            return world,pc,pawn,asc
    def prepare(self):
        for target in screens.CLASSES.values():ue.register_declared_mixin(ue.load_class(target))
        for row in ue.get_registered_mixins():
            cls=row['target_class'];cdo=cls.get_cdo()
            if {'Python','BlueprintFallback'}<=set(row['profiles']) and 'PythonMixinProfile' in cdo.properties():
                self.classes[cls]=str(cdo.get_property('PythonMixinProfile'))
                if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
        require(any(cls.get_path_name()=='/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C' for cls in self.classes),'actual Explorer hero profile binding missing')
        self.report['selected_class_paths']=sorted(cls.get_path_name() for cls in self.classes);self.travel()
    def travel(self):
        self.release_input()
        if self.pc is not None:self.old.append((self.pc,self.pawn))
        self.previous_world=self.world
        for cls in self.classes:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.report['native_level_open_requests']+=1
        lib('GameplayStatics').call_function('OpenLevel',self.world,MAP,True,'')
        self.pc=None;self.pawn=None;self.world=None;self.enter('travel')
    def inventory(self):
        component=self.pc.get_component_by_type(ue.find_class('LyraInventoryManagerComponent'))
        return sorted([dict(definition=path(e.Instance.get_property('ItemDef')),count=int(e.StackCount)) for e in component.get_property('InventoryList').Entries],key=lambda r:(r['definition'],r['count']))
    def stack(self):
        layouts=[w for w in ue.tobject_iterator(ue.find_class('PrimaryGameLayout')) if valid(w) and w.call_function('GetOwningPlayer')==self.pc and w.call_function('IsInViewport')]
        require(len(layouts)==1,'one actual Explorer player root layout required')
        return layouts[0].get_property('GameMenu_Stack')
    def widgets(self):return [w for w in self.stack().get_property('WidgetList') if valid(w)]
    def inject(self,asset,value):
        self.input=lib('SubsystemBlueprintLibrary').call_function('GetLocalPlayerSubsystem',self.pc,ue.find_class('EnhancedInputLocalPlayerSubsystem'))
        self.action=ue.load_object(ue.find_class('InputAction'),asset);self.input.call_function('InjectInputVectorForAction',self.action,ue.FVector(*value))
    def release_input(self):
        if valid(self.input) and valid(self.action):self.input.call_function('InjectInputVectorForAction',self.action,ue.FVector())
        self.action=None
    def start_case(self,context):
        self.world,self.pc,self.pawn,self.asc=context;require(self.world!=self.previous_world,'fresh native World required for profile comparison')
        profile=self.profile;require(str(self.pawn.get_property('PythonMixinProfile'))==profile,'profile was not selected before native Explorer spawn')
        gs=lib('GameplayStatics').call_function('GetGameState',self.world);experience=gs.get_component_by_type(ue.find_class('LyraExperienceManagerComponent')).get_property('CurrentExperience')
        self.row=dict(profile=profile,world=path(self.world),pawn_class=path(self.pawn.get_class()),experience=path(experience),native_role=int(self.pawn.call_function('GetLocalRole')),
            visible=True,health=float(self.pawn.get_component_by_type(ue.find_class('LyraHealthComponent')).call_function('GetHealth')),
            initial_inventory=self.inventory(),natural_begin=copy.deepcopy(beginning.evidence(self.pawn)),menus=[],input_subsystem_used=True,
            granted_abilities=sorted(path(s.Ability.get_class()) for s in self.asc.get_property('ActivatableAbilities').Items if valid(s.Ability)))
        self.report['cases'].append(self.row);require(not self.widgets(),'actual Explorer Menu layer should start empty');self.menu_index=0;self.open_menu()
    def open_menu(self):
        self.menu_kind=('inventory','map')[self.menu_index];asset='IA_ToggleInventory' if self.menu_kind=='inventory' else 'IA_ToggleMap'
        self.menu_asset='/ShooterExplorer/Input/Actions/'+asset+'.'+asset
        self.inject(self.menu_asset,(1.,0.,0.));self.released=False;self.enter('menu-open')
    def observe_menu(self):
        if not self.released:self.release_input();self.released=True
        widgets=self.widgets()
        active=self.stack().call_function('GetActiveWidget')
        if not widgets or active not in widgets or not active.call_function('IsActivated'):return
        cls=screens.CLASSES[self.menu_kind];require(all(path(w.get_class())==cls for w in widgets),'native input opened unexpected Explorer screen')
        self.menu_widgets=widgets;self.menu_before=[copy.deepcopy(screens.evidence(w)) for w in widgets]
        self.menu_row=dict(kind=self.menu_kind,input_asset=self.menu_asset,native_widgets=len(widgets),widget_class=cls,native_layer='UI.Layer.GameMenu',native_active_widget_observed=True);self.row['menus'].append(self.menu_row)
        for w in widgets:w.call_function('DeactivateWidget')
        self.enter('menu-close')
    def close_menu(self):
        if self.widgets() or any(valid(w) and w.call_function('IsActivated') for w in self.menu_widgets):return
        self.menu_row.update(native_removed=True,callback_deltas=[{k:screens.evidence(w)[k]-before[k] for k in ('python','fallback')} for w,before in zip(self.menu_widgets,self.menu_before)])
        self.menu_index+=1
        if self.menu_index<2:self.open_menu();return
        self.move_start=vector(self.pawn.get_actor_location());self.move_frames=0;self.enter('move')
    def move(self):
        self.inject('/Game/Input/Actions/IA_Move.IA_Move',(0.,1.,0.));self.move_frames+=1
        if self.move_frames<24:return
        self.release_input();self.row['movement']=dict(input_frames=self.move_frames,start=self.move_start,end=vector(self.pawn.get_actor_location()),native_input_asset='/Game/Input/Actions/IA_Move.IA_Move')
        self.row['movement']['distance_squared']=sum((a-b)**2 for a,b in zip(self.row['movement']['start'],self.row['movement']['end']))
        self.row['inventory_preserved']=self.inventory()==self.row['initial_inventory'];self.enter('quiet')
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'Explorer Experience comparison timeout');require(time.monotonic()-self.phase_started<55.,'Explorer Experience phase timeout: '+self.phase)
            if self.phase=='warmup':
                context=self.context()
                if context is not None:self.world,self.pc,self.pawn,self.asc=context;self.prepare()
            elif self.phase=='travel':
                context=self.context()
                if context is not None and context[0]!=self.previous_world:self.start_case(context)
            elif self.phase=='menu-open':self.observe_menu()
            elif self.phase=='menu-close':self.close_menu()
            elif self.phase=='move':self.move()
            elif self.phase=='quiet' and time.monotonic()-self.phase_started>.5:
                self.report['old_profile_pawns_and_controllers_destroyed']=all(not valid(v) for pair in self.old for v in pair);self.finish()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:
            self.release_input()
            for cls,profile in self.classes.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
            for cls in self.roots:cls.remove_from_root()
            self.report['selectors_restored']=all(str(cls.get_cdo().get_property('PythonMixinProfile'))==p for cls,p in self.classes.items()) and all(not cls.is_rooted() for cls in self.roots)
            if error is None:validate(dict(self.report,status='passed',actual_exit_finalizer=True))
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_EXPERIENCE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        self.report['actual_exit_finalizer']=True
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_EXPERIENCE_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerExperienceResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
