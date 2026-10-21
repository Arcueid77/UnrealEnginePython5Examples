"""Parent client-only footstep lifetime and interface forwarding orchestration."""
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorScaleMethod,ESpawnActorCollisionHandlingMethod,EAttachmentRule
from uep_lyra_world.effect_pad_mixin import valid
from .hero_default_death_mixin import LyraHeroDefaultDeathPythonProfile,LyraHeroDefaultDeathBlueprintFallbackProfile,CLASS,SELECTOR
FOOTSTEP='/Game/Effects/Blueprints/B_FootStep.B_FootStep_C'

def lib(name):return ue.find_class(name).get_cdo()
def evidence(actor):
    value=getattr(actor,'_uep_hero_default_motion',None)
    if value is None:value=dict(python_calls=0,fallback_calls=0,server_noops=0,spawns=0,reuses=0,attachments=0,forwards=0);actor._uep_hero_default_motion=value
    return value

class LyraHeroDefaultMotionPythonProfile:
    UpdateCustomStencilFromTeamID=LyraHeroDefaultDeathPythonProfile.__dict__['UpdateCustomStencilFromTeamID']
    HideEquippedWeapons=LyraHeroDefaultDeathPythonProfile.__dict__['HideEquippedWeapons']
    Ragdoll=LyraHeroDefaultDeathPythonProfile.__dict__['Ragdoll']
    PythonDeathStarted=LyraHeroDefaultDeathPythonProfile.__dict__['PythonDeathStarted']
    PythonAfterDeathDelay=LyraHeroDefaultDeathPythonProfile.__dict__['PythonAfterDeathDelay']

    def AnimMotionEffect(self,Bone,MotionEffect,StaticMeshComponent,LocationOffset,RotationOffset,AnimationSequence,bHitSuccess,HitResult,Contexts,VFXScale,AudioVolume,AudioPitch):
        counts=evidence(self);counts['python_calls']+=1
        if lib('KismetSystemLibrary').call_function('IsServer',self):counts['server_noops']+=1;return
        footstep=self.get_property('FootStep')
        if not valid(footstep):
            transform=lib('KismetMathLibrary').call_function('MakeTransform',ue.FVector(),ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale;statics=lib('GameplayStatics');footstep=statics.call_function('BeginDeferredActorSpawnFromClass',self,ue.load_class(FOOTSTEP),transform,ESpawnActorCollisionHandlingMethod.Undefined,None,scale)
            # Match the source exposed-on-spawn property order before Finish.
            footstep.set_property('Skeletal Mesh Component',self.get_property('Mesh'));footstep.set_property('FootStepRightFootBone','foot_r');statics.call_function('FinishSpawningActor',footstep,transform,scale);self.set_property('FootStep',footstep);counts['spawns']+=1
            footstep.call_function('K2_AttachToComponent',self.get_property('Mesh'),'None',EAttachmentRule.KeepRelative,EAttachmentRule.KeepRelative,EAttachmentRule.KeepRelative,True);counts['attachments']+=1
        else:counts['reuses']+=1
        footstep.call_function('AnimMotionEffect',Bone,MotionEffect,StaticMeshComponent,LocationOffset,RotationOffset,AnimationSequence,bHitSuccess,HitResult,Contexts,VFXScale,AudioVolume,AudioPitch);counts['forwards']+=1

class LyraHeroDefaultMotionBlueprintFallbackProfile:
    UpdateCustomStencilFromTeamID=LyraHeroDefaultDeathBlueprintFallbackProfile.__dict__['UpdateCustomStencilFromTeamID']
    HideEquippedWeapons=LyraHeroDefaultDeathBlueprintFallbackProfile.__dict__['HideEquippedWeapons']
    Ragdoll=LyraHeroDefaultDeathBlueprintFallbackProfile.__dict__['Ragdoll']
    PythonDeathStarted=LyraHeroDefaultDeathBlueprintFallbackProfile.__dict__['PythonDeathStarted']
    PythonAfterDeathDelay=LyraHeroDefaultDeathBlueprintFallbackProfile.__dict__['PythonAfterDeathDelay']
    def AnimMotionEffect(self,Bone,MotionEffect,StaticMeshComponent,LocationOffset,RotationOffset,AnimationSequence,bHitSuccess,HitResult,Contexts,VFXScale,AudioVolume,AudioPitch):
        evidence(self)['fallback_calls']+=1;self.call_mixin_original('AnimMotionEffect',Bone,MotionEffect,StaticMeshComponent,LocationOffset,RotationOffset,AnimationSequence,bHitSuccess,HitResult,Contexts,VFXScale,AudioVolume,AudioPitch)
