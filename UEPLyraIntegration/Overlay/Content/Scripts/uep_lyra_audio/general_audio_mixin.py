"""Static FireStinger through typed Object dispatch; original warnings preserved."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/Game/UEPMixins/BP_GeneralAudioRouter.BP_GeneralAudioRouter_C"
METHOD="UEPGeneralAudioStinger"
MUSIC="/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C"
def lib(name):return ue.find_class(name).get_cdo()
def evidence(router):
    value=getattr(router,"_uep_general_audio",None)
    if value is None:value=dict(python_calls=0,fallback_calls=0,manager_calls=0);router._uep_general_audio=value
    return value
def stinger(router,positive,world):
    state=lib("GameplayStatics").call_function("GetGameState",world)
    if not valid(state) or not state.is_a(ue.find_class("LyraGameState")):text="FireStinger: LyraGameState not valid."
    else:
        manager=state.get_component_by_type(ue.load_class(MUSIC))
        if valid(manager):manager.call_function("Fire Stinger",positive);evidence(router)["manager_calls"]+=1;return
        text="FireStinger: MusicManager not valid."
    lib("KismetSystemLibrary").call_function("PrintString",world,text,True,False,ue.FLinearColor(0.,.66,1.,1.),5.,"None")
class LyraGeneralAudioPythonProfile:
    def Fire(self,Positive,WorldContext):evidence(self)["python_calls"]+=1;stinger(self,Positive,WorldContext);return dict(UseOriginal=False)
    Fire.override=METHOD;Fire.uep_named_outputs=True
class LyraGeneralAudioBlueprintFallbackProfile:
    def Fire(self,Positive,WorldContext):evidence(self)["fallback_calls"]+=1;return dict(UseOriginal=True)
    Fire.override=METHOD;Fire.uep_named_outputs=True
