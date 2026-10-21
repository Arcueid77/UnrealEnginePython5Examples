"""Original actors and prompt remain untouched; observe native no-op boundaries."""
import atexit,hashlib,json,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture
from .explorer_shells_contract import FALSE_FIELDS,require,validate
ASSETS={'simple':'/ShooterExplorer/Blueprint/B_SimpleFollowPawn.B_SimpleFollowPawn_C','big':'/ShooterExplorer/Blueprint/B_SimpleFollowPawn_Big.B_SimpleFollowPawn_Big_C','prompt':'/ShooterExplorer/UserInterface/W_InteractionPrompt.W_InteractionPrompt_C'}
def path(v):return v.get_path_name() if valid(v) else None
def vector(v):return [float(v.x),float(v.y),float(v.z)]
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,actors=[],prompt_cases=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.actors=[];self.widgets=[];self.descriptors=[];self.frame_start=None
    def config(self,a):
        capsule=a.get_property('CapsuleComponent');mesh=a.get_property('Mesh');return dict(cls=path(a.get_class()),root_class=path(a.get_property('RootComponent').get_class()),mesh_asset=path(mesh.call_function('GetSkeletalMeshAsset')),mesh_relative_scale=vector(mesh.get_property('RelativeScale3D')),capsule_radius=float(capsule.call_function('GetUnscaledCapsuleRadius')),capsule_half_height=float(capsule.call_function('GetUnscaledCapsuleHalfHeight')),component_count=len(lib('LyraSystemStatics').call_function('FindComponentsByClass',a,ue.find_class('ActorComponent'),False)),location=vector(a.get_actor_location()))
    def tree(self,label):
        file=self.path.parent/(label+'.t3d');require(ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(self.prompt.get_property('WidgetTree'),str(file)),'native original prompt tree export failed');return file.read_bytes()
    def begin(self):
        self.player_before=capture(self.controller);self.health_before=self.healths();root=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerShellAudit=')));self.audit=json.loads((root/'audit.json').read_text(encoding='utf-8-sig'));self.reference_hashes=self.audit['reference_hashes'];self.classes={k:ue.load_class(v) for k,v in ASSETS.items()}
        for index,kind in enumerate(('simple','big')):
            actor=self.world.actor_spawn(self.classes[kind],ue.FVector(200000.+index*1000.,200000.,2000.));self.actors.append(actor);actor.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0);self.report['actors'].append(dict(kind=kind,exact_original_class_spawned=actor.get_class()==self.classes[kind],native_parent_routes_retained=self.audit['assets'][kind]['classification']['empty_or_forwarding_only'],before=self.config(actor),original_native_method_shapes_preserved=all(actor.find_function(name).get_class().get_name()!='PythonFunction' and ue.describe_function(actor.get_class(),name)==shape for name,shape in self.audit['assets'][kind]['signatures'].items())))
        self.prompt=lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes['prompt'],self.controller);self.prompt.add_to_root();self.widgets.append(self.prompt);self.prompt.call_function('AddToPlayerScreen',0);self.text=self.prompt.get_property('WidgetTree').get_property('RootWidget').call_function('GetContent').call_function('GetContent');self.frame_start=int(lib('KismetSystemLibrary').call_function('GetFrameCount'));self.enter('native-frames')
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'retained Explorer native frame timeout')
        if int(lib('KismetSystemLibrary').call_function('GetFrameCount'))-self.frame_start<5:return
        for actor,row in zip(self.actors,self.report['actors']):row['after']=self.config(actor);row['components_config_and_location_stable']=row['after']==row['before']
        original=self.tree('prompt-before-bind');text_before=str(self.text.call_function('GetText'));visibility_before=int(self.prompt.call_function('GetVisibility'));actor_data=self.world.actor_spawn(ue.find_class('Actor'));self.actors.append(actor_data);actor_data.add_actor_root_component(ue.find_class('SceneComponent'),'UEPPromptDataRoot');scene_before=(vector(actor_data.get_actor_location()),len(lib('LyraSystemStatics').call_function('FindComponentsByClass',actor_data,ue.find_class('ActorComponent'),False)))
        for name,data in (('actor',actor_data),('nonactor',self.statics.call_function('GetGameInstance',self.world)),('null-data',None)):
            descriptor=ue.new_object(ue.find_class('IndicatorDescriptor'));descriptor.add_to_root();self.descriptors.append(descriptor);descriptor.call_function('SetDataObject',data);self.prompt.call_function('BindIndicator',descriptor);unchanged=self.tree('prompt-after-'+name)==original and str(self.text.call_function('GetText'))==text_before and int(self.prompt.call_function('GetVisibility'))==visibility_before;scene_after=(vector(actor_data.get_actor_location()),len(lib('LyraSystemStatics').call_function('FindComponentsByClass',actor_data,ue.find_class('ActorComponent'),False)));self.report['prompt_cases'].append(dict(name=name,native_bind_call_completed=True,text_style_visibility_and_tree_unchanged=unchanged,descriptor_and_actor_state_unchanged=descriptor.call_function('GetDataObject')==data and scene_after==scene_before))
        self.report['original_assets_hashes_unchanged']=all(hashlib.sha256(Path(file).read_bytes()).hexdigest()==digest for file,digest in self.reference_hashes.items());self.finish()
    def cleanup(self):
        for w in self.widgets:
            if valid(w):w.call_function('RemoveFromParent');w.remove_from_root()
        for descriptor in self.descriptors:
            if valid(descriptor):descriptor.call_function('SetDataObject',None);descriptor.remove_from_root()
        for actor in self.actors:
            if valid(actor):actor.actor_destroy()
        self.report['owned_actors_widgets_descriptors_and_roots_closed']=all(not valid(a) for a in self.actors) and all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets) and all(not d.is_rooted() for d in self.descriptors);self.report['primary_player_inventory_and_health_unchanged']=capture(self.controller)==self.player_before and self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'retained Explorer readiness timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_SHELLS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_SHELLS_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerShellsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
