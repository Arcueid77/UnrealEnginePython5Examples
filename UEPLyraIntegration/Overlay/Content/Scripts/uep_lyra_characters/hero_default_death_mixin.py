"""Parent Health ingress uses native montage/sight/Delay and virtual endpoints."""
import unreal_engine as ue
from unreal_engine.classes import Actor
from unreal_engine.structs import LatentActionInfo
from uep_lyra_world.effect_pad_mixin import valid
from .hero_default_ragdoll_mixin import LyraHeroDefaultRagdollPythonProfile,LyraHeroDefaultRagdollBlueprintFallbackProfile,CLASS,SELECTOR
from .death_started_mixin import BOUND_EVENT,evidence,trace,stamp,resume
from .latent_keys import allocate
RESUME='UEPHeroDefaultAfterDeathDelay'

class LyraHeroDefaultDeathPythonProfile:
    UpdateCustomStencilFromTeamID=LyraHeroDefaultRagdollPythonProfile.__dict__['UpdateCustomStencilFromTeamID']
    HideEquippedWeapons=LyraHeroDefaultRagdollPythonProfile.__dict__['HideEquippedWeapons']
    Ragdoll=LyraHeroDefaultRagdollPythonProfile.__dict__['Ragdoll']

    def PythonDeathStarted(self,OwningActor:Actor):
        value=evidence(self);value['python_calls']+=1
        montages=list(self.get_property('Death Montages'));math=ue.find_class('KismetMathLibrary').get_cdo();index=int(math.call_function('RandomIntegerInRange',0,len(montages)-1));montage=montages[index] if 0<=index<len(montages) else None
        self.call_function('PlayAnimMontage',montage,1.,'None');value['montage_calls']+=1;trace(self,'montage');sense=self.get_property('AIPerceptionStimuliSource')
        if valid(sense):sense.call_function('UnregisterFromSense',ue.find_class('AISense_Sight'));value['unregister_calls']+=1
        else:value['missing_sense_noops']+=1
        trace(self,'sight');duration=float(math.call_function('RandomFloatInRange',.1,.6))
        if value['uuid'] is None:value['uuid'],=allocate(self,'hero-default-death-delay',1)
        value['last_start']=dict(owning_actor=OwningActor.get_path_name() if valid(OwningActor) else None,montage=montage.get_path_name() if valid(montage) else None,montage_index=index,montage_count=len(montages),duration=duration,**stamp(self))
        info=LatentActionInfo(Linkage=0,UUID=value['uuid'],ExecutionFunction=RESUME,CallbackTarget=self);ue.find_class('KismetSystemLibrary').get_cdo().call_function('Delay',self,duration,info);value['delay_requests']+=1;value['pending']=True;trace(self,'delay')
    PythonDeathStarted.override=BOUND_EVENT

    def PythonAfterDeathDelay(self,Linkage:int):resume(self,Linkage)
    PythonAfterDeathDelay.override=RESUME

class LyraHeroDefaultDeathBlueprintFallbackProfile:
    UpdateCustomStencilFromTeamID=LyraHeroDefaultRagdollBlueprintFallbackProfile.__dict__['UpdateCustomStencilFromTeamID']
    HideEquippedWeapons=LyraHeroDefaultRagdollBlueprintFallbackProfile.__dict__['HideEquippedWeapons']
    Ragdoll=LyraHeroDefaultRagdollBlueprintFallbackProfile.__dict__['Ragdoll']
    def PythonDeathStarted(self,OwningActor:Actor):
        evidence(self)['fallback_calls']+=1;trace(self,'fallback');self.call_mixin_original(BOUND_EVENT,OwningActor)
    PythonDeathStarted.override=BOUND_EVENT
    PythonAfterDeathDelay=LyraHeroDefaultDeathPythonProfile.__dict__['PythonAfterDeathDelay']
