"""Teleporter policy; native collision, teleport, movement and audio stay native."""
import copy
import unreal_engine as ue
from .effect_pad_mixin import valid

CLASS = "/ShooterCore/Blueprint/B_Teleport.B_Teleport_C"
PREFIX = "UEPDispatchTeleporter"
_stats = dict(constructions=0, begins=0, destinations=0, character_entries=0,
              grenade_entries=0, teleports=0, launches=0, rotations=0,
              pawn_audio=0, grenade_audio=0, ignored=0, errors=[])


def snapshot():
    return copy.deepcopy(_stats)


def library(name):
    return ue.find_class(name).get_cdo()


def construct(actor):
    for name, field in (("EdgeWidth", "TeleporterEdgeWidth"), ("PortalWidth", "TeleporterWidth"),
                        ("PortalHeight", "TeleporterHeight"), ("Spread", "TeleporterSpread"),
                        ("Phase", "TeleporterPhase"), ("Brightness", "TeleporterBrigtness")):
        actor.Niagara.call_function("SetVariableFloat", name, actor.get_property(field))
    actor.Niagara.call_function("SetVariableInt", "NumPlanes", actor.TeleporterNumPlanes)
    actor.Niagara.call_function("SetVariableInt", "SystemEntered", 0)
    actor.Niagara.call_function("SetVariableBool", "Inward", actor.TeleporterInwardMotion)
    if actor.ReceiverOnly:
        # Blueprint supplies its hidden DefaultToSelf owner pin. Generic calls
        # do not populate that pin: pass the owning Actor explicitly.
        actor.Box.call_function("K2_DestroyComponent", actor)
    _stats["constructions"] += 1


def destination(actor):
    targets = actor.TeleportingTarget
    # Use UE's global RNG, the same RandHelper policy as Array_Random. Do not
    # invoke that CustomThunk through generic reflected parameter transport.
    selected = library("KismetMathLibrary").call_function("RandomInteger", len(targets)) if targets else -1
    actor.set_property("TeleporterDestination", targets[selected] if selected >= 0 else None)
    _stats["destinations"] += 1


def offset_location(actor, exit_location, mesh):
    if not actor.KeepReleativeEntryUponExit:
        return exit_location
    base = actor.DefaultSceneRoot1.call_function("K2_GetComponentLocation")
    normal = actor.DefaultSceneRoot1.call_function("GetForwardVector")
    entry = mesh.call_function("K2_GetComponentLocation")
    relative = [getattr(entry, k)-getattr(base, k) for k in ("x", "y", "z")]
    direction = [getattr(normal, k) for k in ("x", "y", "z")]
    distance = sum(a*b for a, b in zip(relative, direction))
    delta = [a-distance*b for a, b in zip(relative, direction)]
    # Original macro keeps WORLD X/Y; it does not rotate into destination space.
    # FMath::Clamp also returns its minimum for negative values even when the
    # configured maximum is below that minimum. Preserve that ordering.
    z = 0.0 if delta[2] < 0.0 else min(delta[2], actor.TeleporterHeight-100.0)
    return ue.FVector(exit_location.x+delta[0], exit_location.y+delta[1], exit_location.z+z)


def sound(actor, location, pawn):
    actor.set_property("Audio Location", location)
    sound_asset = ue.load_object(ue.find_class("SoundBase"),
        "/Game/Audio/MetaSounds/sfx_Teleport_nl_meta_Preset.sfx_Teleport_nl_meta_Preset")
    statics = library("GameplayStatics")
    if pawn and actor.get_property("Overlapping Pawn").call_function("IsLocallyViewed"):
        statics.call_function("PlaySound2D", WorldContextObject=actor, Sound=sound_asset,
                              VolumeMultiplier=1.0, PitchMultiplier=1.0, bIsUISound=False)
    else:
        for position in (location, actor.DefaultSceneRoot1.call_function("K2_GetComponentLocation")):
            statics.call_function("PlaySoundAtLocation", WorldContextObject=actor, Sound=sound_asset,
                                  Location=position, VolumeMultiplier=.7, PitchMultiplier=1.0)
    _stats["pawn_audio" if pawn else "grenade_audio"] += 1


def begin(actor, other):
    _stats["begins"] += 1
    if not valid(other):
        _stats["ignored"] += 1
        return
    character = other.is_a(ue.find_class("Character"))
    grenade = not character and other.is_a(ue.load_class("/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"))
    if not (character or grenade):
        _stats["ignored"] += 1
        return
    if character:
        actor.set_property("Overlapping Pawn", other)
    actor.call_function("Set Teleporter Destination")
    target = actor.TeleporterDestination
    if not valid(target):
        # Original invalid configuration logs Accessed None. Fail closed without
        # claiming invalid-config parity or falling through into original BP.
        raise RuntimeError("teleporter requires a valid destination")
    exit_component = target.get_property("Exit Direction")
    exit_location = exit_component.call_function("K2_GetComponentLocation")
    forward = exit_component.call_function("GetForwardVector")
    location = offset_location(actor, exit_location, other.Mesh)
    if not character:
        _stats["grenade_entries"] += 1
        actor.call_function("Teleport Audio for Grenade", exit_location)
        # B_Grenade's own business remains a separately tracked migration batch.
        other.call_function("Teleport Grenade", location, forward)
        return
    _stats["character_entries"] += 1
    target.set_property("ReceivingPawn", other)
    parameters = library("AbilitySystemBlueprintLibrary").call_function("MakeGameplayCueParameters",
        Instigator=other, EffectCauser=actor, GameplayEffectLevel=1, AbilityLevel=1)
    library("GameplayCueFunctionLibrary").call_function("ExecuteGameplayCueOnActor", other, actor.GameplayCueTag, parameters)
    actor.call_function("Teleport Audio for Pawn", location)
    rotation = library("KismetMathLibrary").call_function("Conv_VectorToRotator", forward)
    if actor.call_function("HasAuthority"):
        if other.call_function("K2_TeleportTo", location, rotation):
            _stats["teleports"] += 1
            if actor.LaunchOnTeleport:
                other.call_function("LaunchCharacter", ue.FVector(*(getattr(forward, k)*actor.LaunchMultiplier
                    for k in ("x", "y", "z"))), True, True)
                _stats["launches"] += 1
    controller = other.call_function("GetController")
    if valid(controller) and actor.bForceDirection:
        controller.call_function("SetControlRotation", rotation)
        _stats["rotations"] += 1


def guarded(function, *args):
    try:
        return function(*args)
    except Exception as error:
        _stats["errors"].append(str(error))
        raise


class LyraTeleporterPythonProfile:
    def Construction(self):
        guarded(construct, self)
        return False
    Construction.override = PREFIX+"Construction"

    def Begin(self, OtherActor):
        guarded(begin, self, OtherActor)
        return False
    Begin.override = PREFIX+"Begin"

    def Destination(self):
        guarded(destination, self)
        return False
    Destination.override = PREFIX+"Destination"

    def PawnAudio(self, AudioLocation):
        guarded(sound, self, AudioLocation, True)
        return False
    PawnAudio.override = PREFIX+"PawnAudio"

    def GrenadeAudio(self, AudioLocation):
        guarded(sound, self, AudioLocation, False)
        return False
    GrenadeAudio.override = PREFIX+"GrenadeAudio"


class LyraTeleporterBlueprintFallbackProfile:
    def Construction(self):
        return self.call_mixin_original(PREFIX+"Construction")
    Construction.override = PREFIX+"Construction"

    def Begin(self, OtherActor):
        return self.call_mixin_original(PREFIX+"Begin", OtherActor)
    Begin.override = PREFIX+"Begin"

    def Destination(self):
        return self.call_mixin_original(PREFIX+"Destination")
    Destination.override = PREFIX+"Destination"

    def PawnAudio(self, AudioLocation):
        return self.call_mixin_original(PREFIX+"PawnAudio", AudioLocation)
    PawnAudio.override = PREFIX+"PawnAudio"

    def GrenadeAudio(self, AudioLocation):
        return self.call_mixin_original(PREFIX+"GrenadeAudio", AudioLocation)
    GrenadeAudio.override = PREFIX+"GrenadeAudio"
