"""Python ownership of the first weapon HUD batch; inventory remains native."""

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, SlateBrush


MAGAZINE_AMMO = "Lyra.ShooterGame.Weapon.MagazineAmmo"
SPARE_AMMO = "Lyra.ShooterGame.Weapon.SpareAmmo"
MAGAZINE_SIZE = "Lyra.ShooterGame.Weapon.MagazineSize"
LOW_AMMO_THRESHOLDS = {
    "W_AmmoCounter_Pistol_C": 2,
    "W_AmmoCounter_Rifle_C": 4,
    "W_AmmoCounter_Shotgun_C": 1,
}
RELOAD_EVENT = (
    "BndEvt__W_WeaponAmmoAndName_TouchButton_K2Node_ComponentBoundEvent_0_"
    "OnButtonClickedEvent__DelegateSignature"
)
BRUSH_FIELDS = (
    "TintColor", "DrawAs", "Tiling", "Mirroring", "ImageSize", "Margin",
    "OutlineSettings",
)


def _valid(value):
    try:
        return value is not None and value.is_valid()
    except Exception:
        return False


def _note(instance, method):
    counts = instance._uep_weapon_hud_calls
    counts[method] = counts.get(method, 0) + 1


def _stat(item, tag):
    return int(item.call_function("GetStatTagStackCount", GameplayTag(TagName=tag))) if _valid(item) else 0


def _set_scalar(image, parameter, value):
    material = image.call_function("GetDynamicMaterial")
    if not _valid(material):
        raise RuntimeError("ammo image has no dynamic material")
    material.call_function("SetScalarParameterValue", parameter, float(value))


def _text(value, grouping):
    # Keep UE FText/culture behavior rather than formatting display text in Python.
    return ue.find_class("KismetTextLibrary").get_cdo().call_function(
        "Conv_IntToText", int(value), False, grouping, 1, 324
    )


def _resume_observation(instance, kind):
    # A live Profile switch does not replay Construct. Its first Tick resumes
    # ownership once; ordinary frames keep all native reads in the observer.
    if not instance._uep_weapon_disposed and instance._uep_weapon_subscription is None:
        from . import weapon_observer
        weapon_observer.subscribe(instance, kind)
        weapon_observer.refresh(instance)


class LyraAmmoCounterPythonProfile:
    def __init__(self):
        self._uep_weapon_hud_calls = {}
        self._uep_weapon_subscription = None
        self._uep_weapon_disposed = False

    def Construct(self):
        self._uep_weapon_disposed = False
        from . import weapon_observer
        weapon_observer.subscribe(self, "counter")

    def Destruct(self):
        self._uep_weapon_disposed = True
        from . import weapon_observer
        weapon_observer.unsubscribe(self)

    def __uep_mixin_teardown__(self):
        self._uep_weapon_disposed = True
        from . import weapon_observer
        weapon_observer.unsubscribe(self)

    def OnWeaponInitialized(self):
        self._uep_weapon_disposed = False
        maximum = _stat(self.InventoryInstance, MAGAZINE_SIZE)
        for image in (self.AmmoCounter_Bar, self.AmmoCounter_Glow):
            _set_scalar(image, "Rounds_Max", maximum)
        from . import weapon_observer
        weapon_observer.subscribe(self, "counter")
        weapon_observer.refresh(self)
        _note(self, "OnWeaponInitialized")

    def Tick(self, MyGeometry, InDeltaTime):
        # Suppress the original per-widget BP polling. One observer owns reads.
        _resume_observation(self, "counter")
        _note(self, "Tick")

    def SetWeaponSpecificImages(self, AmmoCounterImage, WeaponSpecificImage):
        # Preserve the authored counter brush. The actual BP wires the
        # WeaponSpecificImage UObject itself to ResourceObject (not its
        # Brush.ResourceObject), despite the unusual UImage parameter type.
        original = AmmoCounterImage.Brush
        brush = SlateBrush()
        for name in BRUSH_FIELDS:
            setattr(brush, name, getattr(original, name))
        brush.ResourceObject = WeaponSpecificImage
        AmmoCounterImage.call_function("SetBrush", brush)
        _note(self, "SetWeaponSpecificImages")


class LyraWeaponAmmoPythonProfile:
    def __init__(self):
        self._uep_weapon_hud_calls = {}
        self._uep_weapon_subscription = None
        self._uep_weapon_disposed = False

    def Construct(self):
        self._uep_weapon_disposed = False
        from . import weapon_observer
        weapon_observer.subscribe(self, "panel")
        weapon_observer.refresh(self)

    def Destruct(self):
        self._uep_weapon_disposed = True
        from . import weapon_observer
        weapon_observer.unsubscribe(self)

    def __uep_mixin_teardown__(self):
        self._uep_weapon_disposed = True
        from . import weapon_observer
        weapon_observer.unsubscribe(self)

    def Tick(self, MyGeometry, InDeltaTime):
        _resume_observation(self, "panel")
        _note(self, "Tick")

    def ReloadClicked(self):
        subsystem = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
            "GetLocalPlayerSubsystem", self, ue.find_class("EnhancedInputLocalPlayerSubsystem")
        )
        if _valid(subsystem):
            action = ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/IA_Weapon_Reload.IA_Weapon_Reload")
            subsystem.call_function("InjectInputVectorForAction", action, ue.FVector(1.0, 0.0, 0.0))
        _note(self, "ReloadClicked")

    ReloadClicked.override = RELOAD_EVENT


def render_counter(instance, value):
    current = value["magazine"]
    threshold = LOW_AMMO_THRESHOLDS[instance.get_class().get_name()]
    for image in (instance.AmmoCounter_Bar, instance.AmmoCounter_Glow):
        _set_scalar(image, "Rounds_Max", value["maximum"])
        _set_scalar(image, "Rounds_Current", current)
        _set_scalar(image, "IsLowAmmo", float(current <= threshold))
    _note(instance, "AmmoChanged")


def render_panel(instance, value):
    instance.QuickBar = value["quickbar"]
    item = value["item"]
    if item != instance.InventoryItem:
        instance.InventoryItem = item
        if _valid(item):
            fragment = item.call_function("FindFragmentByClass", ue.find_class("InventoryFragment_QuickBarIcon"))
            texture = fragment.AmmoBrush.ResourceObject if _valid(fragment) else None
            if _valid(texture) and texture.is_a(ue.find_class("Texture")):
                material = instance.AmmoIcon.call_function("GetDynamicMaterial")
                if _valid(material):
                    material.call_function("SetTextureParameterValue", "TextureMask", texture)
            # Original WeaponNameWidget.SetText is disconnected: retain it.
    instance.VerticalBoxForHiding.call_function("SetVisibility", 0 if _valid(item) else 2)
    if _valid(item):
        instance.AmmoLeftInMagazineWidget.call_function("SetText", _text(value["magazine"], False))
        instance.TotalCountWidget.call_function("SetText", _text(value["spare"], True))
    _note(instance, "AmmoChanged")


class LyraWeaponHUDBlueprintFallbackProfile:
    """Explicit baseline profile; other omitted methods use router fallback."""

    def Tick(self, MyGeometry, InDeltaTime):
        return self.call_mixin_original("Tick", MyGeometry, InDeltaTime)
