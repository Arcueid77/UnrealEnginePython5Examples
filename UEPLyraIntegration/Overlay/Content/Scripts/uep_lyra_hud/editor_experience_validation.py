"""Real catalog/layout/deferred portal initialization and natural overlap travel."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import editor_experience_list_mixin as lists,editor_experience_portal_mixin as portal
from .editor_experience_contract import FALSE_FIELDS,require,validate
def arg(n,d):return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'=')),d)
def path(x):return x.get_path_name() if x is not None else None
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def count(obj,key,is_portal=False):return sum((portal if is_portal else lists).evidence(obj)[p+'_'+key] for p in ('python','fallback'))
def xyz(v):return [float(v.x),float(v.y),float(v.z)]
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_local_playing_phase=False;self.profile=arg('UEPEditorExperienceProfile','Python');self.report=dict(status='running',error=None,profile=self.profile,native_filter_cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.cdos={};self.class_roots=[];self.owned=[];self.case_index=0;self.loaded=[];self.travel_started=False
    def begin(self):
        self.health_before=self.healths();self.original_world=self.world;self.original_controller=self.controller;self.original_pawn=self.pawn
        for key,name in (('list',lists.CLASS),('portal',portal.CLASS),('tile','/Game/UI/Menu/Experiences/W_ExperienceTile.W_ExperienceTile_C')):
            cls=ue.load_class(name);self.classes[key]=cls
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            ue.register_declared_mixin(cls);self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.loading=lists.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('LyraLoadingScreenSubsystem'));self.loading_before=self.loading.call_function('GetLoadingScreenContentWidget');self.start_case()
    def expected(self,loaded,show_all,additional):
        values=list(additional)
        for exp in loaded:
            if valid(exp) and exp.is_a(ue.find_class('LyraUserFacingExperienceDefinition')):
                if bool(exp.get_property('bShowInFrontEnd')) and bool(exp.get_property('bIsDefaultExperience')):values.insert(0,exp)
                elif show_all:values.append(exp)
        return values
    def start_case(self):
        self.show_all=self.case_index==1;self.additional=[] if not self.show_all else [self.loaded[-1],self.loaded[0],self.loaded[0]];location=ue.FVector(18000.+self.case_index*18000.,14000.,4000.);rotation=ue.FRotator(0.,0.,23.);scale=ue.FVector(1.25,.8,1.1);self.transform=lists.lib('KismetMathLibrary').call_function('MakeTransform',location,rotation,scale);self.list_actor=lists.lib('GameplayStatics').call_function('BeginDeferredActorSpawnFromClass',self.world,self.classes['list'],self.transform,1,None,0);self.list_actor.set_property('ShowAllExperiences',self.show_all);self.list_actor.set_property('AdditionalExperiencesToShow',self.additional);self.list_actor.set_property('PortalSpacing',1300.);lists.lib('GameplayStatics').call_function('FinishSpawningActor',self.list_actor,self.transform,0);self.owned.append(self.list_actor);self.enter('catalog')
    def observe(self):
        require(time.monotonic()-self.phase_started<(130. if self.phase=='arrival' else 40.),'editor experience phase timeout: '+self.phase)
        if self.phase=='catalog':
            self.report['native_editor_diagnostics']=dict(case=self.case_index,list_counts={k:v for k,v in lists.evidence(self.list_actor).items() if isinstance(v,int)},portal_count=len(self.list_actor.get_property('ExperiencePortals')))
            if count(self.list_actor,'loaded')<1:return
            loaded=lists.evidence(self.list_actor).get('loaded_inputs',[]);require(loaded,'native real primary definitions missing');self.loaded=loaded;self.expected_values=self.expected(loaded,self.show_all,self.additional);values=list(self.list_actor.get_property('UserFacingExperienceList'));self.portals=list(self.list_actor.get_property('ExperiencePortals'));require(values==self.expected_values and len(self.portals)==len(values),'native default-map filter/order differs');self.report['native_catalog_async_loaded_real_definitions']=True;self.frames=0;self.enter('widgets')
        elif self.phase=='widgets':
            self.frames+=1
            if self.frames<20:return
            root_transform=self.list_actor.get_property('DefaultSceneRoot').call_function('K2_GetComponentToWorld');actor_rotation=self.list_actor.get_actor_rotation()
            for index,(p,exp) in enumerate(zip(self.portals,self.expected_values)):
                require(valid(p) and p.get_property('UserFacingExperienceToLoad')==exp and portal.evidence(p).get('begin_experience')==exp,'definition not exposed before native portal BeginPlay');offset=(index-len(self.expected_values)*.5+.5)*1300.;expected=lists.lib('KismetMathLibrary').call_function('TransformLocation',root_transform,ue.FVector(offset,0.,0.));actual=p.get_actor_location();require(all(abs(a-b)<.1 for a,b in zip(xyz(expected),xyz(actual))) and all(abs(float(getattr(p.get_actor_rotation(),k))-float(getattr(actor_rotation,k)))<.01 for k in ('roll','pitch','yaw')),'native centered portal transform differs');widget=p.get_property('Widget');tile=widget.call_function('GetWidget');require(valid(tile) and tile.get_property('MyUserFacingExperience')==exp and int(widget.get_property('TickMode'))==0 and count(p,'widget',True)>=1,'original portal widget/delay/tick disable missing');require(portal.evidence(p).get('native_default_flag')==bool(exp.get_property('bIsDefaultExperience')) and count(p,'color',True)>=1,'native default color branch differs')
            self.report.update(native_spawn_definition_exposed_before_beginplay=True,native_centered_actor_transform_layout=True,native_original_widget_definition_delay_tick_disabled=True,native_original_default_color_branch=True);self.report['native_filter_cases'].append(self.show_all)
            if not self.show_all:self.destroy_case();self.case_index+=1;self.start_case()
            else:self.old_portals=list(self.portals);self.before_loaded=count(self.list_actor,'loaded');self.list_actor.call_function('ReceiveBeginPlay');self.enter('repeat')
        elif self.phase=='repeat':
            if count(self.list_actor,'loaded')<=self.before_loaded:return
            current=list(self.list_actor.get_property('ExperiencePortals'));require(current[:len(self.old_portals)]==self.old_portals and len(current)==len(self.old_portals)*2 and list(self.list_actor.get_property('UserFacingExperienceList'))==self.expected_values,'original portal cache does not accumulate');self.portals=current;self.report.update(native_repeated_begin_accumulates_old_portal_cache=True,native_false_true_filter_additional_order_and_duplicates=True);self.target=next(p for p in self.portals if p.get_property('UserFacingExperienceToLoad').get_property('bShowInFrontEnd') and p.get_property('UserFacingExperienceToLoad').get_property('bIsDefaultExperience'));
            for p in self.portals:
                if p!=self.target:p.call_function('SetActorEnableCollision',False)
            self.report['owned_duplicate_portal_collisions_disabled_before_positive_overlap']=True;before=count(self.target,'load',True);self.target.call_function('ReceiveActorBeginOverlap',self.list_actor);dummy=self.world.actor_spawn(ue.find_class('DefaultPawn'),ue.FVector(70000.,70000.,8000.));self.target.call_function('ReceiveActorBeginOverlap',dummy);dummy.actor_destroy();require(count(self.target,'load',True)==before,'nonpawn/uncontrolled inputs loaded experience');self.report['native_nonpawn_and_uncontrolled_inputs_do_not_load']=True;require(self.healths()==self.health_before,'original health changed before travel');self.report['initial_gameplay_health_unchanged_before_travel']=True;self.requests_before={path(r) for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest'))};self.target_evidence=portal.evidence(self.target);self.target_experience=self.target.get_property('UserFacingExperienceToLoad');destination=self.target.get_property('CollisionCapsule').call_function('K2_GetComponentLocation');self.pawn.call_function('K2_SetActorLocation',NewLocation=destination,bSweep=False,bTeleport=True);self.travel_started=True;self.enter('request')
        elif self.phase=='request':
            tally=lambda key:sum(self.target_evidence[p+'_'+key] for p in ('python','fallback'))
            if tally('pushed')<1:return
            requests=[r for r in ue.tobject_iterator(ue.find_class('CommonSession_HostSessionRequest')) if path(r) not in self.requests_before];require(len(requests)==1 and tally('load')==1 and tally('overlap')>=3 and tally('pushed')==1,'actual local overlap/spinner/request count differs');self.request=requests[0];exp=self.target_experience;require(self.target_evidence.get('pushed_experience')==exp and int(self.request.get_property('OnlineMode'))==0,'current experience/offline payload differs');self.report.update(native_real_local_pawn_overlap_requests_load=True,native_spinner_afterpush_current_definition_offline_payload=True,request_mode=0,pushed_handler_calls=1,native_request_map=str(self.request.get_property('MapID').PrimaryAssetName),native_request_experience=dict(self.request.get_property('ExtraArgs'))['Experience']);self.enter('arrival')
        elif self.phase=='arrival':
            for world in ue.all_worlds():
                if world.get_world_type() not in (1,3) or world==self.original_world:continue
                controller=lists.lib('GameplayStatics').call_function('GetPlayerController',world,0)
                if not valid(controller):continue
                bridge=lists.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
                if not valid(bridge):continue
                snap=bridge.call_function('CaptureSnapshot')
                if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0):continue
                level=lists.lib('GameplayStatics').call_function('GetCurrentLevelName',world,True);mode=lists.lib('GameplayStatics').call_function('GetGameMode',world);experience=lists.lib('GameplayStatics').call_function('ParseOption',mode.get_property('OptionsString'),'Experience');require(level==self.report['native_request_map'].rsplit('/',1)[-1] and experience==self.report['native_request_experience'],'actual offline destination differs');self.world=world;self.controller=controller;self.report.update(native_destination_map_experience_and_player_ready=True,native_destination_level=level,native_destination_experience=experience,native_world_controller_replacement_expected=True);self.finish();return
    def destroy_case(self):
        for p in list(self.list_actor.get_property('ExperiencePortals')):
            if valid(p):p.actor_destroy()
        self.list_actor.actor_destroy();self.owned=[]
    def cleanup(self):
        if not self.travel_started and hasattr(self,'list_actor') and valid(self.list_actor):self.destroy_case()
        if hasattr(self,'loading'):self.loading.call_function('SetLoadingScreenContentWidget',self.loading_before)
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for cls in self.class_roots:cls.remove_from_root()
        self.report['owned_roots_profiles_fixture_actors_and_loading_class_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.cdos.items()) and (not hasattr(self,'loading') or self.loading.call_function('GetLoadingScreenContentWidget')==self.loading_before)
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<280.,'editor experience timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EDITOR_EXPERIENCE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EDITOR_EXPERIENCE_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPEditorExperienceResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
