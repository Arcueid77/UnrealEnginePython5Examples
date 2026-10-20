"""Actual primary load,dynamic level/delegates,native latent task unregister."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import lobby_background_mixin as policy
from .lobby_background_contract import PROFILES,FALSE_FIELDS,require,validate
def count(actor,key):return sum(policy.evidence(actor)[p+'_'+key] for p in ('python','fallback'))
def path(v):return v.get_path_name() if v is not None else None
def xyz(v):return [float(v.x),float(v.y),float(v.z)]
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_local_playing_phase=False;self.report=dict(status='running',error=None,profiles=[]);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.index=0;self.cls=None;self.cdo_before=None;self.class_root=False;self.actors=[];self.streams=[]
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);self.class_root=not self.cls.is_rooted()
        if self.class_root:self.cls.add_to_root()
        ue.register_declared_mixin(self.cls);self.cdo_before=self.cls.get_cdo().get_property('PythonMixinProfile');self.manager=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('LoadingScreenManager'));self.ids=list(one(policy.lib('KismetSystemLibrary').call_function('GetPrimaryAssetIdList',ue.find_struct('PrimaryAssetType')(Name='LyraLobbyBackground'))));require(self.ids,'native lobby catalog must contain real backgrounds');self.start_profile()
    def reason(self):return str(self.manager.call_function('GetDebugReasonForShowingOrHidingLoadingScreen'))
    def start_profile(self):
        self.profile=PROFILES[self.index];self.cls.get_cdo().set_property('PythonMixinProfile',self.profile);self.location=ue.FVector(15000.+self.index*20000.,10000.,3000.);self.rotation=ue.FRotator(0.,17.,0.);self.actor=self.world.actor_spawn(self.cls,self.location,self.rotation);self.actors.append(self.actor);self.row=dict(profile=self.profile);self.task_seen=False;self.reason_seen=False;self.stream=None;self.enter('streaming')
    def observe(self):
        require(time.monotonic()-self.phase_started<100.,'lobby background phase timeout: '+self.phase)
        if self.phase=='streaming':
            a=self.actor;e=policy.evidence(a);task=a.get_property('LoadingScreenTask')
            if valid(task):self.task_seen=True
            self.reason_seen |= policy.REASON in self.reason()
            stream=e.get('last_instance')
            if stream is not None and self.stream is None:self.stream=stream;self.streams.append(stream)
            self.report['native_lobby_diagnostics']=dict(profile=self.profile,counters={k:v for k,v in e.items() if isinstance(v,(int,float,bool))},reason=self.reason(),stream=path(stream),task=path(task))
            if count(a,'release')<1:return
            require(count(a,'loaded')==count(a,'shown')==count(a,'release')==1 and self.stream is not None and self.stream.call_function('IsLevelLoaded') and self.stream.call_function('IsLevelVisible'),'actual native lobby level callbacks/state missing');box=a.get_property('EditorOnlyBox');require(xyz(box.call_function('GetUnscaledBoxExtent'))==xyz(a.get_property('BoxExtents')) and count(a,'construct')>=1,'native lobby construction box changed');self.row['native_construction_box_extents_preserved']=True;selected=a.get_property('BackgroundToLoad');require(any(str(v.PrimaryAssetType.Name)==str(selected.PrimaryAssetType.Name) and str(v.PrimaryAssetName)==str(selected.PrimaryAssetName) for v in self.ids),'native catalog selection not registered');self.row['native_catalog_selected_registered_primary_id']=True;require(self.task_seen and self.reason_seen and valid(task),'native loading task/reason not observed');self.row['native_loading_process_task_identity_and_reason']=True;background=e.get('loaded_background');require(valid(background) and background.is_a(ue.find_class('LyraLobbyBackground')) and count(a,'asset_ready')==1,'actual native primary lobby load missing');self.row['native_primary_async_loaded_correct_data_asset']=True;transform=self.stream.get_property('LevelTransform');rotation=a.get_actor_rotation();self.row['transform_samples']=dict(actor_location=xyz(a.get_actor_location()),stream_location=xyz(transform.translation),actor_rotation=[rotation.roll,rotation.pitch,rotation.yaw],stream_rotation=[transform.rotation.roll,transform.rotation.pitch,transform.rotation.yaw]);require(all(abs(x-y)<.1 for x,y in zip(xyz(transform.translation),xyz(a.get_actor_location()))) and all(abs(float(getattr(transform.rotation,k))-float(getattr(rotation,k)))<.01 for k in ('roll','pitch','yaw')),'native instance transform differs');self.row['native_level_instance_actor_location_rotation']=True;delay=float(e['release_game_time'])-float(e['hide_game_time']);require(delay>=.48,'native original delay completed early');self.row.update(native_actual_loaded_and_shown_weak_delegate_callbacks=True,native_half_second_delay_before_unregister=True,loaded_callbacks=1,shown_callbacks=1,release_callbacks=1,release_delay_game_seconds=delay,selected_primary_id=str(selected.PrimaryAssetType.Name)+':'+str(selected.PrimaryAssetName),native_stream=path(self.stream));self.enter('released')
        elif self.phase=='released':
            if policy.REASON in self.reason():return
            self.row['native_loading_reason_released']=True;self.stream.call_function('SetShouldBeVisible',False);self.stream.call_function('SetShouldBeLoaded',False);self.stream.call_function('SetIsRequestingUnloadAndRemoval',True);self.enter('unload')
        elif self.phase=='unload':
            if valid(self.stream) and (self.stream.call_function('IsLevelLoaded') or self.stream.call_function('IsLevelVisible')):return
            if valid(self.stream) and self.stream in list(self.world.get_property('StreamingLevels')):return
            self.row['native_owned_level_unloaded_and_removed']=True;self.streams=[];self.actor.actor_destroy();require(not valid(self.actor),'owned lobby actor did not destroy');self.actors=[];self.row['native_actor_destroyed']=True;self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.finish()
    def cleanup(self):
        for stream in self.streams:
            if valid(stream) and stream.is_a(ue.find_class('LevelStreaming')):stream.call_function('SetShouldBeVisible',False);stream.call_function('SetShouldBeLoaded',False);stream.call_function('SetIsRequestingUnloadAndRemoval',True)
        for actor in self.actors:
            if valid(actor) and actor.is_a(ue.find_class('Actor')):
                task=actor.get_property('LoadingScreenTask')
                if valid(task):task.call_function('Unregister')
                actor.actor_destroy()
        if self.cls is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.cdo_before)
        if self.class_root:self.cls.remove_from_root()
        self.report['owned_roots_cdo_profile_and_original_health_restored']=(self.cls is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.cdo_before) and (not hasattr(self,'health_before') or self.healths()==self.health_before)
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<280.,'lobby background timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_LOBBY_BACKGROUND_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_LOBBY_BACKGROUND_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPLobbyBackgroundResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
