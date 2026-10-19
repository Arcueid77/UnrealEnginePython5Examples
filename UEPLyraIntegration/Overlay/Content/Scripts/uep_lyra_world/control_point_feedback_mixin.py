"""Volume Timeline/RPC feedback; original native clock, bindings and network flags."""
import unreal_engine as ue
from unreal_engine.enums import ETimelineDirection
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import control_point_state_mixin as state

CLASS=state.CLASS
GATES={n:'UEPControlPoint'+n for n in ('Meshes','TimelineUpdate','TimelineFinished','EnterAudio','ExitAudio','CaptureAudio','Music','ActivateVFX','CleanVFX')}
MESSAGE='UEPControlPointNativeCaptureMessage'
FRIENDLY='/Game/Audio/Sounds/SFX/Lyra_ControlPoint_CapturedByFriendly_01.Lyra_ControlPoint_CapturedByFriendly_01'
ENEMY='/Game/Audio/Sounds/SFX/Lyra_ControlPoint_CapturedByEnemy_01.Lyra_ControlPoint_CapturedByEnemy_01'


def evidence(a):
    if not hasattr(a,'_uep_control_point_feedback'):
        a._uep_control_point_feedback={p+'_'+n:0 for p in ('python','fallback') for n in GATES};a._uep_control_point_feedback.update(last_curve=None,finish_directions=[],diagnostic_fallbacks=0,capture_play_calls=0,progress_play_calls=0,progress_stop_calls=0,stingers=0,forward_finishes=0,reverse_finishes=0)
    return a._uep_control_point_feedback


def mark(a,n):evidence(a)['python_'+n]+=1
def diagnostic(a):evidence(a)['diagnostic_fallbacks']+=1;return True
def subsystem(a,name):return lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',a,ue.find_class(name))


def record_update(a,value):
    row=evidence(a);row['last_curve']=float(value)
    for key,field in (('last_owner_color','OwningTeamColor'),('last_target_color','TargetColor')):
        c=a.get_property(field);row[key]=[float(getattr(c,n)) for n in ('r','g','b','a')]


def meshes(a):
    mark(a,'Meshes');actors=list(a.get_property('StaticMeshList'))
    if any(not valid(x) for x in actors):return diagnostic(a)
    values=list(a.get_property('SM_Components'))
    for actor in actors:
        component=actor.get_property('StaticMeshComponent')
        if component not in values:values.append(component);a.set_property('SM_Components',values)
    return False


def update(a,value):
    mark(a,'TimelineUpdate');record_update(a,value)
    cube=a.get_property('Cube');counter=a.get_property('NS_CapturePointCounter');fx=a.get_property('NS_CapturePoint');audio=a.get_property('Audio_CPProgress');light=a.get_property('PointLight');extras=list(a.get_property('SM_Components'));lights=list(a.get_property('LightList'))
    if not all(valid(x) for x in (cube,counter,fx,audio,light)) or any(not valid(x) for x in extras+lights):return diagnostic(a)
    blended=lib('KismetMathLibrary').call_function('LinearColorLerp',a.get_property('OwningTeamColor'),a.get_property('TargetColor'),value);rgb=lib('KismetMathLibrary').call_function('Conv_LinearColorToVector',blended)
    cube.call_function('SetVectorParameterValueOnMaterials','Color',rgb);counter.call_function('SetVariableLinearColor','GunPad_Color',blended);counter.call_function('SetVariableFloat','RibbonProgression',value)
    for component in extras:component.call_function('SetVectorParameterValueOnMaterials','Color',rgb)
    light.call_function('SetLightColor',blended,True)
    for actor in lights:actor.get_property('LightComponent').call_function('SetLightColor',blended,True)
    fx.call_function('SetVariableLinearColor','BlendingColor',blended);fx.call_function('SetVariableLinearColor','TeamColor',a.get_property('TargetColor'));fx.call_function('SetVariableLinearColor','OwnerColor',a.get_property('OwningTeamColor'));fx.call_function('SetVariableFloat','ColorBlend',value)
    audio.call_function('SetFloatParameter','Progress',value);return False


def finish(a,direction):
    mark(a,'TimelineFinished');evidence(a)['finish_directions'].append(int(direction));timeline=a.get_property('TL_ConvertPoint')
    if int(direction)==int(ETimelineDirection.Forward):
        if not a.call_function('HasAuthority'):return False
        teams=list(a.get_property('OverlappingTeams'));scoring=a.get_property('ControlPointGameMode');counter=a.get_property('NS_CapturePointCounter')
        if not teams or not valid(scoring) or not valid(counter):return diagnostic(a)
        a.set_property('OwnerTeamID',int(teams[0]));scoring.call_function('CapturePoint',list(a.get_property('OverlappingPawns')),a)
        a.set_property('OwningTeamColor',state.one(scoring.call_function('GetTeamColor',int(a.get_property('OwnerTeamID')))));counter.call_function('SetVariableFloat','RibbonProgression',0.);counter.call_function('Deactivate');timeline.call_function('SetNewTime',0.)
        a.call_function('Capture Audio',int(a.get_property('OwnerTeamID')));a.call_function(MESSAGE);evidence(a)['forward_finishes']+=1
    else:
        a.call_function('Clean Up VFX');timeline.call_function('SetNewTime',0.);evidence(a)['reverse_finishes']+=1
    return False


def enter(a,target):
    mark(a,'EnterAudio')
    if not valid(target) or not target.call_function('IsLocallyViewed'):return False
    audio=a.get_property('Audio_CPProgress')
    if not valid(audio):return diagnostic(a)
    audio.call_function('SetBoolParameter','LocalPlayerInside',True);audio.call_function('Play',0.);evidence(a)['progress_play_calls']+=1;return False


def exit_audio(a,target):
    mark(a,'ExitAudio')
    if not valid(target) or not target.call_function('IsLocallyViewed'):return False
    audio=a.get_property('Audio_CPProgress')
    if not valid(audio):return diagnostic(a)
    if audio.call_function('IsActive'):audio.call_function('SetBoolParameter','LocalPlayerInside',False);audio.call_function('StopDelayed',.5);evidence(a)['progress_stop_calls']+=1
    return False


def capture_audio(a,owner):
    mark(a,'CaptureAudio');audio=a.get_property('Audio_CPComplete');teams=subsystem(a,'LyraTeamSubsystem')
    if not valid(audio) or not valid(teams):return diagnostic(a)
    actors=native_outputs('GameplayStatics','GetAllActorsOfClass',lib('GameplayStatics').call_function('GetAllActorsOfClass',a,ue.find_class('Pawn')))['OutActors']
    for pawn in actors:
        if not pawn.call_function('IsLocallyViewed'):continue
        result=native_outputs('LyraTeamSubsystem','FindTeamFromActor',teams.call_function('FindTeamFromActor',pawn))
        if not result['bIsPartOfTeam']:continue
        sound=FRIENDLY if int(result['TeamId'])==int(owner) else ENEMY;audio.call_function('SetSound',ue.load_object(ue.find_class('SoundBase'),sound));audio.call_function('Play',0.);evidence(a)['capture_play_calls']+=1
    return False


def music(a):
    mark(a,'Music');pawn=lib('GameplayStatics').call_function('GetPlayerPawn',a,0)
    if valid(pawn) and pawn in a.get_property('OverlappingPawns'):ue.load_class('/Game/Audio/Blueprints/GeneralAudioFunctions.GeneralAudioFunctions_C').get_cdo().call_function('FireStinger',True,a);evidence(a)['stingers']+=1
    return False


def clean(a):
    mark(a,'CleanVFX');counter=a.get_property('NS_CapturePointCounter')
    if not valid(counter):return diagnostic(a)
    counter.call_function('SetVariableFloat','RibbonProgression',0.);counter.call_function('Deactivate');return False


class LyraControlPointFeedbackPythonProfile:
    Construct=state.LyraControlPointStatePythonProfile.Construct
    Check=state.LyraControlPointStatePythonProfile.Check
    Contest=state.LyraControlPointStatePythonProfile.Contest
    Recapture=state.LyraControlPointStatePythonProfile.Recapture
    Ready=state.LyraControlPointStatePythonProfile.Ready
    Enter=state.LyraControlPointStatePythonProfile.Enter
    Exit=state.LyraControlPointStatePythonProfile.Exit
    Recompute=state.LyraControlPointStatePythonProfile.Recompute
    def Meshes(self):return meshes(self)
    Meshes.override=GATES['Meshes']
    def Update(self,Value):return update(self,Value)
    Update.override=GATES['TimelineUpdate']
    def Finished(self,Direction):return finish(self,Direction)
    Finished.override=GATES['TimelineFinished']
    def EnterAudio(self,Target):return enter(self,Target)
    EnterAudio.override=GATES['EnterAudio']
    def ExitAudio(self,Target):return exit_audio(self,Target)
    ExitAudio.override=GATES['ExitAudio']
    def CaptureAudio(self,OwnerTeamID):return capture_audio(self,OwnerTeamID)
    CaptureAudio.override=GATES['CaptureAudio']
    def Music(self):return music(self)
    Music.override=GATES['Music']
    def Activate(self):mark(self,'ActivateVFX');self.call_function('CheckTimerNS');return False
    Activate.override=GATES['ActivateVFX']
    def Clean(self):return clean(self)
    Clean.override=GATES['CleanVFX']


def fallback(name):
    def invoke(self,*args):
        evidence(self)['fallback_'+name]+=1
        if name=='TimelineUpdate':record_update(self,args[0])
        if name=='TimelineFinished':evidence(self)['finish_directions'].append(int(args[0]))
        return True
    invoke.override=GATES[name];return invoke


class LyraControlPointFeedbackBlueprintFallbackProfile:
    Construct=state.LyraControlPointStateBlueprintFallbackProfile.Construct
    Check=state.LyraControlPointStateBlueprintFallbackProfile.Check
    Contest=state.LyraControlPointStateBlueprintFallbackProfile.Contest
    Recapture=state.LyraControlPointStateBlueprintFallbackProfile.Recapture
    Ready=state.LyraControlPointStateBlueprintFallbackProfile.Ready
    Enter=state.LyraControlPointStateBlueprintFallbackProfile.Enter
    Exit=state.LyraControlPointStateBlueprintFallbackProfile.Exit
    Recompute=state.LyraControlPointStateBlueprintFallbackProfile.Recompute
    Meshes=fallback('Meshes');Update=fallback('TimelineUpdate');Finished=fallback('TimelineFinished');EnterAudio=fallback('EnterAudio');ExitAudio=fallback('ExitAudio');CaptureAudio=fallback('CaptureAudio');Music=fallback('Music');Activate=fallback('ActivateVFX');Clean=fallback('CleanVFX')
