"""Retained static audio API, dispatched through an ordinary typed Object."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, TapDelayInfo
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/Game/UEPMixins/BP_WeaponAudioDispatchRouter.BP_WeaponAudioDispatchRouter_C"
METHODS={"SendWeaponFire":"UEPAudioSendFire","SetWeaponSoundParams":"UEPAudioSoundParams",
    "DebugPrintTap":"UEPAudioDebugTap","Calculate Tap Properties":"UEPAudioTapProperties"}
PRESET="/Game/Audio/Effects/SubmixEffects/TAP_EarlyReflections.TAP_EarlyReflections"
MUSIC="/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C"


def lib(name):return ue.find_class(name).get_cdo()
def evidence(router):
    value=getattr(router,"_uep_audio_dispatch",None)
    if value is None:
        value={method+"_"+profile:0 for method in METHODS for profile in ("python","fallback")};router._uep_audio_dispatch=value
    return value
def tap_preset():return ue.load_object(ue.find_class("SubmixEffectTapDelayPreset"),PRESET)


def send_fire(player,strength,world):
    statics=lib("GameplayStatics");pawn=statics.call_function("GetPlayerPawn",world,0)
    if not valid(pawn) or player!=pawn:return
    state=statics.call_function("GetGameState",world)
    if not valid(state) or not state.is_a(ue.find_class("LyraGameState")):return
    manager=state.get_component_by_type(ue.load_class(MUSIC))
    if valid(manager):manager.call_function("Receive Weapon Fire",player,strength)
    else:
        system=lib("KismetSystemLibrary")
        text=system.call_function("GetDisplayName",state)+" does not have a MusicManager."
        system.call_function("PrintString",world,text,True,False,ue.FLinearColor(1.,.376326,0.,1.),10.,"None")


def sound_params(actor,spawn):
    if not valid(actor) or not actor.is_a(ue.find_class("Pawn")):return
    local=bool(actor.call_function("IsLocallyViewed"));instigator=actor.get_property("Instigator")
    if not valid(instigator):return
    controller=instigator.call_function("GetController")
    if not valid(controller):return
    quickbar=controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
    if not valid(quickbar):return
    item=quickbar.call_function("GetActiveSlotItem");tag=GameplayTag(TagName="Lyra.ShooterGame.Weapon.MagazineAmmo")
    # Preserve the original VM's null-target diagnostics for an empty active slot.
    if not valid(item):return True
    ammo=int(item.call_function("GetStatTagStackCount",tag)) if item.call_function("HasStatTag",tag) else 0
    string=lib("KismetStringLibrary")
    seed=-1 if local else int(string.call_function("GetCharacterAsNumber",lib("KismetSystemLibrary").call_function("GetDisplayName",actor),
        int(string.call_function("Len",lib("KismetSystemLibrary").call_function("GetDisplayName",actor)))-1))
    for audio in spawn.AudioComponents:
        if not valid(audio):continue
        audio.call_function("SetIntParameter","PawnSeed",seed)
        if local:audio.call_function("SetIntParameter","MagazineAmmo",ammo)


def debug_tap(suffix,delay,gain,pan,world):
    string=lib("KismetStringLibrary")
    values=[str(string.call_function("Conv_DoubleToString",float(value))) for value in (delay,gain,pan)]
    text="EarlyReflection."+suffix+"\r\nDelay : "+values[0]+"\r\nGain : "+values[1]+"\r\nPan : "+values[2]
    lib("KismetSystemLibrary").call_function("PrintString",world,text,True,False,ue.FLinearColor(0.,.526042,.159781,1.),5.,string.call_function("Conv_StringToName",suffix))


def tap_properties(suffix,cam,hit,tap_id,trace_distance,travel,did_hit,listener):
    math=lib("KismetMathLibrary");preset=tap_preset()
    if did_hit:
        distance=float(math.call_function("Conv_DoubleToFloat",math.call_function("VSize",math.call_function("Subtract_VectorVector",listener,hit))))
        normalized=float(math.call_function("MapRangeUnclamped",float(travel)+distance,0.,10000.,0.,1.))
        delay=math.call_function("MapRangeUnclamped",normalized*normalized,0.,1.,10.,600.)
        gain=math.call_function("MapRangeClamped",normalized*math.call_function("MapRangeClamped",distance,0.,1000.,0.,1.),0.,1.,-9.,-60.)
        direction=math.call_function("Normal",math.call_function("Subtract_VectorVector",cam.call_function("GetCameraLocation"),hit),.0001)
        pan=math.call_function("Dot_VectorVector",math.call_function("GetRightVector",cam.call_function("GetCameraRotation")),direction)*180.
    else:
        previous,=preset.call_function("GetTap",tap_id);delay=previous.DelayLength;gain=-60.;pan=previous.PanInDegrees
    preset.call_function("SetTap",tap_id,TapDelayInfo(TapLineMode=1,DelayLength=delay,Gain=gain,PanInDegrees=pan))


class LyraWeaponAudioDispatchPythonProfile:
    def Send(self,Player,Strength,WorldContext):
        evidence(self)["SendWeaponFire_python"]+=1;send_fire(Player,Strength,WorldContext);return dict(UseOriginal=False)
    Send.override=METHODS["SendWeaponFire"];Send.uep_named_outputs=True
    def Params(self,Actor,GCN_Spawn_Result,WorldContext):
        evidence(self)["SetWeaponSoundParams_python"]+=1;return dict(UseOriginal=bool(sound_params(Actor,GCN_Spawn_Result)))
    Params.override=METHODS["SetWeaponSoundParams"];Params.uep_named_outputs=True
    def Debug(self,Suffix,Delay,Gain,Pan,WorldContext):
        evidence(self)["DebugPrintTap_python"]+=1;debug_tap(Suffix,Delay,Gain,Pan,WorldContext);return dict(UseOriginal=False)
    Debug.override=METHODS["DebugPrintTap"];Debug.uep_named_outputs=True
    def Tap(self,DebugSuffix,Cam,HitLocation,TapId,TraceDistance,TravelDistance,DidHit,ListenerLocation,WorldContext):
        evidence(self)["Calculate Tap Properties_python"]+=1
        if DidHit and not valid(Cam):return dict(UseOriginal=True)
        tap_properties(DebugSuffix,Cam,HitLocation,TapId,TraceDistance,TravelDistance,DidHit,ListenerLocation);return dict(UseOriginal=False)
    Tap.override=METHODS["Calculate Tap Properties"];Tap.uep_named_outputs=True


def fallback(method):
    def call(self,*args):evidence(self)[method+"_fallback"]+=1;return dict(UseOriginal=True)
    call.override=METHODS[method];call.uep_named_outputs=True;return call


class LyraWeaponAudioDispatchBlueprintFallbackProfile:
    Send=fallback("SendWeaponFire")
    Params=fallback("SetWeaponSoundParams")
    Debug=fallback("DebugPrintTap")
    Tap=fallback("Calculate Tap Properties")
