"""Music startup decisions/callback transforms; retained native async nodes own lifetime."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from . import music_manager_mixin as controls

START="UEPMusicStartListeners"
ELIMINATION="UEPMusicEliminationMessageGate"
DAMAGE="UEPMusicDamageMessageGate"
GAME_INSTANCE="/Game/B_LyraGameInstance.B_LyraGameInstance_C"
SOUND="/Game/Audio/MetaSounds/mx_System.mx_System"
METHODS=(*controls.METHODS,"ReceiveBeginPlay",ELIMINATION,DAMAGE)


def evidence(component):
    value=getattr(component,"_uep_music_lifecycle",None)
    if value is None:value=dict(begin_python=0,begin_fallback=0,reused=0,created=0,listener_starts=0,elimination_python=0,damage_python=0,elimination_fallback=0,damage_fallback=0);component._uep_music_lifecycle=value
    return value
def begin(component):
    stats=evidence(component);stats["begin_python"]+=1
    game=controls.lib("GameplayStatics").call_function("GetGameInstance",component)
    if not valid(game) or not game.is_a(ue.load_class(GAME_INSTANCE)):return
    sound=game.get_property("MusicSystem")
    if not valid(sound):
        sound=controls.lib("GameplayStatics").call_function("CreateSound2D",WorldContextObject=component,Sound=ue.load_object(ue.find_class("SoundBase"),SOUND),
            VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,bPersistAcrossLevelTransition=True,bAutoDestroy=False)
        game.set_property("MusicSystem",sound);stats["created"]+=1
    else:stats["reused"]+=1
    component.set_property("Music System",game.get_property("MusicSystem"));component.call_function(START);stats["listener_starts"]+=1
def elimination(component,payload):
    evidence(component)["elimination_python"]+=1;target=payload.Target
    if valid(target) and target.is_a(ue.find_class("PlayerState")):component.call_function("Receive Player Death",target.call_function("GetPawn"))
    return False
def damage(component,payload):
    evidence(component)["damage_python"]+=1;target=payload.Target
    if controls.locally_viewed(target):component.call_function("Receive Weapon Fire",target,1.)
    return False


class LyraMusicLifecyclePythonProfile:
    SetIsMenu=controls.LyraMusicManagerPythonProfile.SetIsMenu
    Death=controls.LyraMusicManagerPythonProfile.Death
    Fire=controls.LyraMusicManagerPythonProfile.Fire
    Stinger=controls.LyraMusicManagerPythonProfile.Stinger
    ReceiveTick=controls.LyraMusicManagerPythonProfile.ReceiveTick
    def ReceiveBeginPlay(self):begin(self)
    def EliminationMessage(self,Payload):return elimination(self,Payload)
    EliminationMessage.override=ELIMINATION
    def DamageMessage(self,Payload):return damage(self,Payload)
    DamageMessage.override=DAMAGE


class LyraMusicLifecycleBlueprintFallbackProfile:
    SetIsMenu=controls.LyraMusicManagerBlueprintFallbackProfile.SetIsMenu
    Death=controls.LyraMusicManagerBlueprintFallbackProfile.Death
    Fire=controls.LyraMusicManagerBlueprintFallbackProfile.Fire
    Stinger=controls.LyraMusicManagerBlueprintFallbackProfile.Stinger
    ReceiveTick=controls.LyraMusicManagerBlueprintFallbackProfile.ReceiveTick
    def ReceiveBeginPlay(self):evidence(self)["begin_fallback"]+=1;return self.call_mixin_original("ReceiveBeginPlay")
    def EliminationMessage(self,Payload):evidence(self)["elimination_fallback"]+=1;return True
    EliminationMessage.override=ELIMINATION
    def DamageMessage(self,Payload):evidence(self)["damage_fallback"]+=1;return True
    DamageMessage.override=DAMAGE
