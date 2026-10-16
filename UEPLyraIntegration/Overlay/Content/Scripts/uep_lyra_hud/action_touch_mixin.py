"""Action button BP policy; CommonUI, animation, UMG and input stay native."""
import copy
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .weapon_observer import valid

CLASS = "/Game/UI/Hud/W_ActionTouchButton.W_ActionTouchButton_C"
MOBILE_CLASS = "/Game/UI/Hud/W_ActionTouchButton_MobileOnly.W_ActionTouchButton_MobileOnly_C"
PROXY, RESUME = "UEPOriginalActionDurationProxy", "UEPResumeActionDuration"
_active = {}
_stats = dict(scopes_created=0, scopes_closed=0, messages=0, foreign_messages=0,
              ticks=0, clicks=0, style_updates=0, material_resets=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()))


def library(name):
    return ue.find_class(name).get_cdo()


def game_time(widget):
    return float(library("GameplayStatics").call_function("GetTimeSeconds", widget))


def has_channel(widget):
    return bool(library("BlueprintGameplayTagLibrary").call_function("IsGameplayTagValid", widget.DurationMessageTag))


def material(widget, name):
    return getattr(widget, name).call_function("GetDynamicMaterial")


def update_percent(widget, percent):
    for name in ("ItemGlow", "WeaponCard"):
        material(widget, name).call_function("SetScalarParameterValue", "Animate_Cooldown", percent)


def reset_materials(widget):
    widget.call_function("StopAnimation", widget.CooldownInactiveToActive)
    for name in ("WeaponCard", "ItemGlow"):
        material(widget, name).call_function("SetScalarParameterValue", "Animate_ActiveToInactive", 1.0)
    _stats["material_resets"] += 1


def style(widget):
    layout = library("WidgetLayoutLibrary")
    layout.call_function("SlotAsOverlaySlot", widget.MainSBWithPadding).call_function("SetPadding", widget.HitTestPadding)
    for child, flag in (("BackingBorder", "UseBacking"), ("Shadow", "UseShadow"), ("BackgroundBlur", "UseBlur"),
                        ("ItemGlow", "UseGlow"), ("DisableGlowBoostOvr", "UseGlowBoost")):
        getattr(widget, child).call_function("SetVisibility", 3 if widget.get_property(flag) else 1)
    widget.WeaponCard.call_function("SetBrush", widget.ButtonBrush)
    widget.ItemGlow.call_function("SetBrush", widget.ButtonGlowBrush)
    for child in ("ItemGlow", "ItemGlow_Boost"):
        layout.call_function("SlotAsOverlaySlot", getattr(widget, child)).call_function("SetPadding", widget.GlowOverdraw)
    radius = widget.BlurCornerRadius
    widget.BackgroundBlur.call_function("SetCornerRadius", library("KismetMathLibrary").call_function("MakeVector4", radius, radius, radius, radius))
    layout.call_function("SlotAsOverlaySlot", widget.BackgroundBlur).call_function("SetPadding", widget.BlurPadding)
    _stats["style_updates"] += 1


def received(widget, payload):
    if payload.Instigator != widget.call_function("GetOwningPlayerPawn"):
        _stats["foreign_messages"] += 1
        return
    # Attribute assignment emits editor property notifications in Editor builds
    # and can re-run UMG PreConstruct. Runtime BP writes do not do that.
    widget.set_property("Duration", float(payload.Duration))
    widget.set_property("StartTime", game_time(widget))
    widget._uep_action_message_playing = widget.call_function("IsAnimationPlaying", widget.CooldownInactiveToActive)
    if widget._uep_action_message_playing:
        widget.call_function("StopAnimation", widget.CooldownInactiveToActive)
    widget.call_function("UpdateCoolDownPercent", 0.)
    widget.call_function("PlayAnimationForward", widget.CooldownActiveToInactive, 1., False)
    widget.set_property("Charging", True)
    widget._uep_action_messages += 1
    _stats["messages"] += 1


def start(widget):
    if widget._uep_action_scope is not None or not has_channel(widget):
        return
    scope = SubscriptionScope()
    widget._uep_action_scope = scope

    def read(proxy):
        payload, success = widget.call_function("ReadActionDuration", proxy)
        if success is not True:
            raise RuntimeError("typed action-duration extraction failed")
        return payload.clone()

    try:
        scope.listen_gameplay_message(widget, str(widget.DurationMessageTag.TagName), ue.find_struct("LyraInteractionDurationMessage"),
                                      read, lambda channel, payload: received(widget, payload))
    except Exception:
        scope.close(); widget._uep_action_scope = None
        raise
    _active[id(widget)] = widget.get_path_name()
    _stats["scopes_created"] += 1


def close(widget):
    scope, widget._uep_action_scope = widget._uep_action_scope, None
    _active.pop(id(widget), None)
    if scope is not None:
        scope.close(); _stats["scopes_closed"] += 1


def close_original(widget):
    proxy = widget.get_property(PROXY)
    widget.set_property(PROXY, None)
    if valid(proxy):
        proxy.call_function("Cancel")


class LyraActionTouchPythonProfile:
    def __init__(self):
        self._uep_action_scope = None
        self._uep_action_ticks = self._uep_action_messages = self._uep_action_clicks = 0

    def OnInitialized(self):
        if has_channel(self):
            self.call_function("ListenForDuration")

    def ListenForDuration(self):
        start(self)

    def Resume(self):
        start(self)
    Resume.override = RESUME

    def PreConstruct(self, IsDesignTime):
        self.call_function("SetButtonStyle")
        self.call_function("ResetMaterials")

    def Construct(self):
        start(self)  # Reused native widgets rearm after their owned teardown.
        self.call_function("UpdateCoolDownPercent", 1.)
        if self.HasCooldown:
            self.call_function("PlayAnimationForward", self.CooldownInactiveToActive, 1., False)
        else:
            self.call_function("ResetMaterials")

    def SetButtonStyle(self):
        style(self)

    def ResetMaterials(self):
        reset_materials(self)

    def UpdateCoolDownPercent(self, Percent):
        update_percent(self, Percent)

    def Tick(self, MyGeometry, InDeltaTime):
        if self.Charging:
            percent = library("KismetMathLibrary").call_function("Divide_DoubleDouble", game_time(self)-self.StartTime, self.Duration)
            self.call_function("UpdateCoolDownPercent", percent)
            if percent >= 1.:
                self.set_property("Charging", False)
                self.call_function("PlayAnimationForward", self.CooldownInactiveToActive, 1., False)
                self.call_function("UpdateCoolDownPercent", 1.)
        self._uep_action_ticks += 1
        _stats["ticks"] += 1

    def BP_OnClicked(self):
        subsystem = library("SubsystemBlueprintLibrary").call_function("GetLocalPlayerSubsystem", self,
            ue.find_class("EnhancedInputLocalPlayerSubsystem"))
        # Match the original authored input vector and native input subsystem.
        subsystem.call_function("InjectInputVectorForAction", self.AssociatedAction, ue.FVector(1., 0., 0.))
        if not (self.HasCooldown or self.get_property("IsToggleButton")):
            if self.call_function("IsAnimationPlayingForward", self.OnClickedTouchInput):
                self.call_function("StopAnimation", self.OnClickedTouchInput)
            self.call_function("PlayAnimationForward", self.OnClickedTouchInput, 1., False)
        self._uep_action_clicks += 1
        _stats["clicks"] += 1

    def BP_OnDisabled(self):
        self.set_property("isDisabled", True)
        for name in ("WeaponCard", "ItemGlow"):
            material(self, name).call_function("SetScalarParameterValue", "Animate_FromEmpty", 0.)
        self.call_function("ResetMaterials")

    def BP_OnEnabled(self):
        self.set_property("isDisabled", False)
        for name in ("WeaponCard", "ItemGlow"):
            material(self, name).call_function("SetScalarParameterValue", "Animate_FromEmpty", 1.)

    def BP_OnSelected(self):
        if not self.get_property("isDisabled"):
            self.call_function("PlayAnimationForward", self.CooldownInactiveToActive, 1., False)

    def BP_OnDeselected(self):
        if not self.get_property("isDisabled"):
            self.call_function("PlayAnimationReverse", self.CooldownInactiveToActive, 1., False)

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)


class LyraActionTouchBlueprintFallbackProfile:
    def OnInitialized(self):
        self.call_mixin_original("OnInitialized")
    def ListenForDuration(self):
        close_original(self); self.call_mixin_original("ListenForDuration")
    def Resume(self):
        proxy = self.get_property(PROXY)
        if has_channel(self) and not (valid(proxy) and proxy.call_function("IsActive")):
            self.call_function("ListenForDuration")
    Resume.override = RESUME
    def PreConstruct(self, IsDesignTime):
        self.call_mixin_original("PreConstruct", IsDesignTime)
    def Construct(self):
        self.call_mixin_original("Construct"); self.call_function(RESUME)
    def SetButtonStyle(self):
        self.call_mixin_original("SetButtonStyle")
    def ResetMaterials(self):
        self.call_mixin_original("ResetMaterials")
    def UpdateCoolDownPercent(self, Percent):
        self.call_mixin_original("UpdateCoolDownPercent", Percent)
    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)
    def BP_OnClicked(self):
        self.call_mixin_original("BP_OnClicked")
    def BP_OnDisabled(self):
        self.call_mixin_original("BP_OnDisabled")
    def BP_OnEnabled(self):
        self.call_mixin_original("BP_OnEnabled")
    def BP_OnSelected(self):
        self.call_mixin_original("BP_OnSelected")
    def BP_OnDeselected(self):
        self.call_mixin_original("BP_OnDeselected")
    def Destruct(self):
        close_original(self)
    def __uep_mixin_teardown__(self):
        close_original(self)
