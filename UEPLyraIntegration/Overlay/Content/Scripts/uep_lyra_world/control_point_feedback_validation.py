"""Incremental feedback differential on the already accepted physical scenarios."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ETimelineDirection
from uep_lyra_weapons.hero_burst_cue_validation import color,dead
from .control_point_state_validation import Validation as Physical
from .control_point_state_mixin import evidence as state_evidence
from .control_point_helpers_validation import Validation as Helpers
from .control_point_state_contract import PROFILES,require
from .control_point_feedback_contract import close,validate
from . import control_point_feedback_mixin as policy


def count(a,n):return sum(policy.evidence(a)[p+'_'+n] for p in ('python','fallback'))
def params(audio):return {str(p.ParamName):p for p in audio.get_property('InstanceParameters')}


class Validation(Physical):
    value=Helpers.value
    def __init__(self,result):
        super().__init__(result);self.report['timeline_update_finish_rpc_vfx_audio_business_migrated']=True;self.report['audio_energy_measured']=False;self.local_saved=False
    def start_case(self):
        self.profile=PROFILES[self.index];self.x=250000.+self.index*10000.;transform=ue.FTransform();transform.translation=ue.FVector(self.x,250000.,3000.)
        self.extra_components=[];self.extra_lights=[];extras=[];reference=self.world.actor_spawn(ue.find_class('PointLight'),ue.FVector(self.x+4000.,250000.,3000.));self.actors.append(reference);self.reference_light=reference.get_property('LightComponent')
        for i in (0,1):
            mesh=self.world.actor_spawn(ue.find_class('StaticMeshActor'),ue.FVector(self.x+3000.,250000.+i*500.,3000.));self.actors.append(mesh);extras.append(mesh);mesh.call_function('SetActorEnableCollision',False);component=mesh.get_property('StaticMeshComponent')
            component.call_function('SetMobility',2);require(component.call_function('SetStaticMesh',ue.load_object(ue.find_class('StaticMesh'),'/Engine/BasicShapes/Cube.Cube')),'owned movable mesh setup failed');component.call_function('SetMaterial',0,ue.load_object(ue.find_class('MaterialInterface'),'/Game/Characters/Heroes/Mannequin/Materials/Instances/Manny/MI_Manny_01.MI_Manny_01'));self.extra_components.append(component)
            light=self.world.actor_spawn(ue.find_class('PointLight'),ue.FVector(self.x+3000.,250000.+i*500.,3000.));self.actors.append(light);self.extra_lights.append(light)
        self.actor=self.statics.call_function('BeginDeferredActorSpawnFromClass',self.world,self.cls,transform,1,None);self.actors.append(self.actor);self.volumes.append(self.actor);ue.set_mixin_profile(self.actor,self.profile)
        self.actor.set_property('AreaScale',policy.lib('KismetMathLibrary').call_function('MakeVector',20.,20.,4.));self.actor.set_property('TimeRequiredForCapture',1.);self.actor.set_property('StaticMeshList',extras+[extras[0]]);self.actor.set_property('SM_Components',[self.extra_components[0]]);self.actor.set_property('LightList',self.extra_lights);self.statics.call_function('FinishSpawningActor',self.actor,transform)
        self.units=[self.unit(i) for i in (0,1)];self.row=dict(profile=self.profile,ready_entries=0,native_rate=None,stages=[],samples=0,all_native_feedback_matches=True,sampled_intermediate_curve=False,
            mesh_list_unique_and_existing_preserved=list(self.actor.get_property('SM_Components'))==self.extra_components,light_native_srgb_reference=True);self.last_sample=-1;self.audio_done=False;self.report['pending_case']=self.row;self.enter('volume-ready')
    def sample(self):
        e=policy.evidence(self.actor);n=count(self.actor,'TimelineUpdate')
        if not n or n==self.last_sample:return
        self.last_sample=n;v=e['last_curve'];owner=e['last_owner_color'];target=e['last_target_color'];expected=[x+(y-x)*v for x,y in zip(owner,target)];a=self.actor;counter=a.get_property('NS_CapturePointCounter');fx=a.get_property('NS_CapturePoint');audio=a.get_property('Audio_CPProgress')
        native_blend=policy.lib('KismetMathLibrary').call_function('LinearColorLerp',ue.FLinearColor(*owner),ue.FLinearColor(*target),v);self.reference_light.call_function('SetLightColor',native_blend,True);light_expected=color(self.reference_light.call_function('GetLightColor'))
        observed=dict(blend=color(self.value(fx,'BlendingColor','GetVariableColor')),owner=color(self.value(fx,'OwnerColor','GetVariableColor')),target=color(self.value(fx,'TeamColor','GetVariableColor')),counter_color=color(self.value(counter,'GunPad_Color','GetVariableColor')),
            color_blend=float(self.value(fx,'ColorBlend','GetVariableFloat')),progress=float(params(audio)['Progress'].FloatParam),light=color(a.get_property('PointLight').call_function('GetLightColor')),
            extra_lights=[color(x.get_property('LightComponent').call_function('GetLightColor')) for x in self.extra_lights],materials=[color(x.call_function('GetMaterial',0).call_function('K2_GetVectorParameterValue','Color'))[:3] for x in [a.get_property('Cube')]+self.extra_components])
        matches=all(close(observed[k],expected) for k in ('blend','counter_color')) and close(observed['light'],light_expected) and all(close(x,light_expected) for x in observed['extra_lights']) and all(close(x,expected[:3]) for x in observed['materials']) and close(observed['owner'],owner) and close(observed['target'],target) and close(observed['color_blend'],v) and close(observed['progress'],v)
        self.row['last_native_sample']=dict(curve=v,expected=expected,light_native_expected=light_expected,observed=observed);self.row['samples']+=1;self.row['all_native_feedback_matches'] &= matches;self.row['sampled_intermediate_curve'] |= .05<v<.95
        require(matches,'actual native feedback differs from retained curve inputs: '+str(self.row['last_native_sample']))
    def audio_start(self):
        a=self.actor;audio=a.get_property('Audio_CPProgress');a.call_function('Enter Audio ',self.pawn);values=params(audio)
        self.row['audio']=dict(locally_viewed=bool(self.pawn.call_function('IsLocallyViewed')),entered=bool(values['LocalPlayerInside'].BoolParam) and bool(audio.call_function('IsActive')))
        a.call_function('Exit Audio',self.pawn);self.row['audio']['exit_parameter_false']=not bool(params(audio)['LocalPlayerInside'].BoolParam)
        before=bool(params(audio)['LocalPlayerInside'].BoolParam)
        for pawn in (None,self.units[0]['pawn']):a.call_function('Enter Audio ',pawn);a.call_function('Exit Audio',pawn)
        self.row['audio']['remote_and_invalid_noop']=not self.units[0]['pawn'].call_function('IsLocallyViewed') and bool(params(audio)['LocalPlayerInside'].BoolParam)==before
        team=policy.native_outputs('LyraTeamSubsystem','FindTeamFromActor',policy.subsystem(a,'LyraTeamSubsystem').call_function('FindTeamFromActor',self.pawn));require(team['bIsPartOfTeam'],'actual local Pawn team required')
        complete=a.get_property('Audio_CPComplete');a.call_function('Capture Audio',int(team['TeamId']));self.row['audio']['friendly_sound']=complete.get_property('Sound').get_path_name()==policy.FRIENDLY
        a.call_function('Capture Audio',int(team['TeamId'])+99);self.row['audio']['enemy_sound']=complete.get_property('Sound').get_path_name()==policy.ENEMY;self.row['audio']['capture_playing']=bool(complete.call_function('IsPlaying'))
        self.local_location=self.pawn.get_actor_location();self.local_rotation=self.pawn.get_actor_rotation();self.local_movement=self.pawn.get_property('CharacterMovement');self.local_tick=bool(self.local_movement.call_function('IsComponentTickEnabled'));self.local_saved=True
        self.local_movement.call_function('SetComponentTickEnabled',False);self.pawn.call_function('K2_SetActorLocation',NewLocation=ue.FVector(self.x,250000.,3050.),bSweep=False,bTeleport=True);self.enter('local-music')
    def restore_local(self):
        if not self.local_saved:return
        self.pawn.call_function('K2_SetActorLocation',NewLocation=self.local_location,bSweep=False,bTeleport=True);self.pawn.call_function('K2_SetActorRotation',self.local_rotation,True);self.local_movement.call_function('SetComponentTickEnabled',self.local_tick);require(bool(self.local_movement.call_function('IsComponentTickEnabled'))==self.local_tick,'local movement tick restoration failed')
        location=self.pawn.get_actor_location();rotation=self.pawn.get_actor_rotation();before_location=[float(getattr(self.local_location,k)) for k in ('x','y','z')];after_location=[float(getattr(location,k)) for k in ('x','y','z')];before_rotation=[float(getattr(self.local_rotation,k)) for k in ('pitch','yaw','roll')];after_rotation=[float(getattr(rotation,k)) for k in ('pitch','yaw','roll')]
        self.row['local_transform_native_values']=dict(before_location=before_location,after_location=after_location,before_rotation=before_rotation,after_rotation=after_rotation);self.row['local_transform_restored']=close(before_location,after_location) and close(before_rotation,after_rotation);self.local_saved=False
    def observe(self):
        require(time.monotonic()-self.phase_started<10.,'native feedback phase timeout: '+self.phase)
        self.sample()
        if self.phase=='local-music':
            if self.pawn not in self.actor.get_property('OverlappingPawns'):return
            self.actor.call_function('Music On CP Finished');self.row['music_local_overlap']=True;self.restore_local();self.actor.call_function('Exit Audio',self.pawn);self.enter('audio-delay');return
        if self.phase=='audio-delay':
            if time.monotonic()-self.phase_started<.7:return
            self.row['audio']['stopped_after_delay']=not self.actor.get_property('Audio_CPProgress').call_function('IsActive');self.audio_done=True;self.enter('final-empty');return
        if self.phase=='mixed' and len(self.actor.get_property('OverlappingTeams'))==2 and count(self.actor,'TimelineFinished')<1:return
        if self.phase=='final-empty' and not self.actor.get_property('OverlappingPawns') and time.monotonic()-self.phase_started>.1:
            if not self.audio_done:self.audio_start();return
            e=policy.evidence(self.actor);self.row.update(entries={n:count(self.actor,n) for n in policy.GATES},diagnostic_fallbacks=e['diagnostic_fallbacks'],native_forward_finishes=e['finish_directions'].count(int(ETimelineDirection.Forward)),native_reverse_finishes=e['finish_directions'].count(int(ETimelineDirection.Backward)))
        super().observe()
    def cleanup(self):
        self.restore_local();super().cleanup();self.report['production_profiles_restored']=any(r['target_class']==self.cls and all(len(r['profiles'][p]['functions'])==17 for p in PROFILES) for r in ue.get_registered_mixins());self.report['local_movement_tick_restored']=not self.local_saved
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_CONTROL_POINT_FEEDBACK_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CONTROL_POINT_FEEDBACK_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPControlPointFeedbackResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
