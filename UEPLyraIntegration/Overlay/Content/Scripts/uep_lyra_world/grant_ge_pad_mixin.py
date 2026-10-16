"""Grant-pad business; native GAS, Timeline/curve, collision and visuals remain."""
import copy
import unreal_engine as ue
from unreal_engine import FVector, FRotator
from .effect_pad_mixin import valid, ability_system

CLASS = "/ShooterCore/Blueprint/B_GrantAbilityPad_ApplyGE.B_GrantAbilityPad_ApplyGE_C"
PREFIX = "UEPDispatchGrantGE"
TEXT = "UEPTransferGrantGEText"
_stats = dict(constructions=0, begins=0, ends=0, actives=0, updates=0, finishes=0, ticks=0, errors=[])


def snapshot():
    return copy.deepcopy(_stats)


def color(actor):
    return ue.find_class("KismetMathLibrary").get_cdo().call_function("Conv_LinearColorToVector", actor.PadColor)


def construct(actor):
    actor.Pad.call_function("SetVectorParameterValueOnMaterials", "PadColor", color(actor))
    actor.call_function(TEXT)  # Native FText property transport, preserving text history.
    resource = ue.load_object(ue.find_class("MaterialInterface"),
        "/ShooterCore/Effects/Material/MI_WeaponSpawnerTimerIndicator.MI_WeaponSpawnerTimerIndicator")
    actor.set_property("MID_TimerIndicator", actor.TimerIndicator.call_function("CreateDynamicMaterialInstance", 0, resource, "None"))
    actor.ItemMesh.call_function("SetStaticMesh", actor.Mesh)
    actor.PointLight.call_function("SetLightColor", actor.PadColor, True)
    _stats["constructions"] += 1


def begin(actor, other):
    _stats["begins"] += 1
    asc = ability_system(other) if valid(other) else None
    if actor.bActive and valid(asc):
        asc.call_function("BP_ApplyGameplayEffectToSelf", actor.GameplayEffectToApply, 0.0)
        actor.ItemMesh.call_function("SetHiddenInGame", True, False)


def end(actor, other):
    _stats["ends"] += 1
    asc = ability_system(other) if valid(other) else None
    if valid(asc):
        asc.call_function("RemoveActiveGameplayEffectBySourceEffect", actor.GameplayEffectToApply, None, -1)
        actor.call_function("Active")


def active(actor):
    actor.Pad.call_function("SetVectorParameterValueOnMaterials", "PadColor", FVector(.109375, .109375, .109375))
    actor.PointLight.call_function("SetVisibility", False, False)
    actor.Text.call_function("K2_SetText", "Charging")
    actor.call_function("SetActorTickEnabled", False)
    actor.set_property("bActive", False)
    rate = ue.find_class("KismetMathLibrary").get_cdo().call_function("Divide_DoubleDouble", 1.0, float(actor.Duration))
    actor.TL_Charge.call_function("SetPlayRate", rate)
    actor.TL_Charge.call_function("PlayFromStart")
    _stats["actives"] += 1


def finish(actor):
    actor.set_property("bActive", True)
    actor.Pad.call_function("SetVectorParameterValueOnMaterials", "PadColor", color(actor))
    actor.call_function(TEXT)
    actor.ItemMesh.call_function("SetHiddenInGame", False, False)
    actor.call_function("SetActorTickEnabled", True)
    actor.MID_TimerIndicator.call_function("SetScalarParameterValue", "Percent", 0.0)
    actor.PointLight.call_function("SetVisibility", True, False)
    _stats["finishes"] += 1


def guarded(function, actor, *args):
    try:
        function(actor, *args)
    except Exception as error:
        _stats["errors"].append(str(error))
        raise
    return False


class LyraGrantGEPythonProfile:
    def Construction(self):
        return guarded(construct, self)
    Construction.override = PREFIX+"Construction"

    def Begin(self, OtherActor):
        return guarded(begin, self, OtherActor)
    Begin.override = PREFIX+"Begin"

    def End(self, OtherActor):
        return guarded(end, self, OtherActor)
    End.override = PREFIX+"End"

    def Active(self):
        guarded(active, self)

    def Tick(self, DeltaSeconds):
        def apply(actor):
            actor.Scene.call_function("K2_AddLocalRotation", FRotator(0.0, 0.0, float(DeltaSeconds)*50.0), False, bTeleport=False)
            _stats["ticks"] += 1
        return guarded(apply, self)
    Tick.override = PREFIX+"Tick"

    def Update(self, Value):
        def apply(actor):
            actor.MID_TimerIndicator.call_function("SetScalarParameterValue", "Percent", Value)
            _stats["updates"] += 1
        return guarded(apply, self)
    Update.override = PREFIX+"Update"

    def Finish(self):
        return guarded(finish, self)
    Finish.override = PREFIX+"Finish"


class LyraGrantGEBlueprintFallbackProfile:
    def Construction(self):
        return self.call_mixin_original(PREFIX+"Construction")
    Construction.override = PREFIX+"Construction"

    def Begin(self, OtherActor):
        return self.call_mixin_original(PREFIX+"Begin", OtherActor)
    Begin.override = PREFIX+"Begin"

    def End(self, OtherActor):
        return self.call_mixin_original(PREFIX+"End", OtherActor)
    End.override = PREFIX+"End"

    def Active(self):
        self.call_mixin_original("Active")

    def Tick(self, DeltaSeconds):
        return self.call_mixin_original(PREFIX+"Tick", DeltaSeconds)
    Tick.override = PREFIX+"Tick"

    def Update(self, Value):
        return self.call_mixin_original(PREFIX+"Update", Value)
    Update.override = PREFIX+"Update"

    def Finish(self):
        return self.call_mixin_original(PREFIX+"Finish")
    Finish.override = PREFIX+"Finish"
