"""Ability-owned reset/UI lifetime; native listener and latent nodes do transport."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, UIExtensionHandle
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_events_mixin import (LyraAutoRespawnEventsPythonProfile as PythonBase,
    LyraAutoRespawnEventsBlueprintFallbackProfile as BlueprintBase, end_death_and_wait, AFTER_LONG, AFTER_SHORT)

PROXY, ENDED = "UEPAutoRespawnResetProxy", "UEPAutoRespawnRuntimeEnded"
START_RESET, SUBSCRIBED = "UEPAutoRespawnStartResetListener", "UEPAutoRespawnResetSubscribedGate"
RESET, END = "UEPAutoRespawnResetMessageGate", "UEPAutoRespawnEndGate"
WIDGET = "/ShooterCore/Game/Respawn/W_RespawnTimer.W_RespawnTimer_C"
_stats = dict(added=0, removed=0, activated=0, avatar_set=0, native_reset_starts=0,
    reset_messages=0, foreign_resets=0, resets_handled=0, ui_registered=0,
    ui_unregistered=0, native_reset_cancelled=0, end_cleanups=0,
    cancelled_long_continuations=0, cancelled_short_continuations=0,
    fallback_added=0, fallback_removed=0, fallback_activated=0,
    fallback_avatar_set=0, fallback_subscribed=0, fallback_reset_messages=0, fallback_end_cleanups=0)


def snapshot(): return copy.deepcopy(_stats)
def instance_snapshot(ability): return dict(getattr(ability, "_uep_auto_activation_counts", {}))


def note(ability, key):
    _stats[key] += 1
    values = instance_snapshot(ability); values[key] = values.get(key, 0)+1
    ability._uep_auto_activation_counts = values


def cancel_reset(ability):
    try: proxy = ability.get_property(PROXY)
    except Exception as error:
        if str(error) != "uobject is in invalid state" or not valid(ability): raise
        proxy = None
    # Drop the reflected claim before Cancel can invalidate the native action.
    ability.set_property(PROXY, None)
    ability.set_property("IsListeningForReset", False)
    if valid(proxy):
        proxy.call_function("Cancel"); note(ability, "native_reset_cancelled")


def unregister_ui(ability):
    ue.find_class("UIExtensionHandleFunctions").get_cdo().call_function("Unregister", ability.Extension)
    ability.set_property("Extension", UIExtensionHandle())
    note(ability, "ui_unregistered")


def cleanup(ability):
    # The ability, not its selected Profile, owns this lifetime. Explicit
    # native End/removal stops the reset producer and disarms latent business;
    # switching Profiles deliberately does neither.
    ability.set_property(ENDED, True)
    ability.set_property("ShouldFinishRestart", False)
    cancel_reset(ability); unregister_ui(ability)


def initialize(ability):
    ability.set_property(ENDED, False)
    if not ability.IsListeningForReset:
        ability.call_function(START_RESET)
        ability.set_property("IsListeningForReset", True)
        note(ability, "native_reset_starts")
    dead, = ability.call_function("Is Avatar Dead or Dying")
    if dead: ability.call_function("OnDeathStarted", ability.call_function("GetAvatarActorFromActorInfo"))
    else: ability.call_function("BindDeathListener")


class LyraAutoRespawnActivationPythonProfile(PythonBase):
    GetOwningPlayerState = PythonBase.GetOwningPlayerState
    IsAvatarDeadOrDying = PythonBase.IsAvatarDeadOrDying
    EndDeathAbilities = PythonBase.EndDeathAbilities
    BindDeathListener = PythonBase.BindDeathListener
    ClearDeathListener = PythonBase.ClearDeathListener
    OnDeathStarted = PythonBase.OnDeathStarted
    OnAvatarEndPlay = PythonBase.OnAvatarEndPlay

    def K2_OnAbilityAdded(self):
        note(self, "added"); self.set_property(ENDED, False)
        native = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem", self, ue.find_class("UIExtensionSubsystem"))
        if valid(native):
            handle = native.call_function("K2_RegisterExtensionAsWidgetForContext", GameplayTag(TagName="HUD.Slot.Reticle"),
                ue.load_class(WIDGET), self.call_function("GetOwningPlayerState"), -1)
            self.set_property("Extension", handle); note(self, "ui_registered")

    def K2_OnAbilityRemoved(self):
        note(self, "removed"); cleanup(self); self.call_function("ClearDeathListener")

    def K2_ActivateAbility(self): note(self, "activated"); initialize(self)
    def K2_OnPawnAvatarSet(self): note(self, "avatar_set"); initialize(self)

    def ResetSubscribed(self): return False
    ResetSubscribed.override = SUBSCRIBED

    def ResetMessage(self, OwnerPlayerState):
        note(self, "reset_messages")
        if OwnerPlayerState != self.call_function("GetOwningActorFromActorInfo"):
            note(self, "foreign_resets"); return False
        if self.get_property(ENDED) or not self.call_function("K2_HasAuthority"): return False
        self.set_property("ControllerToReset", self.call_function("GetControllerFromActorInfo"))
        self.call_function("ClearDeathListener")
        self.set_property("ShouldFinishRestart", False)
        end_death_and_wait(self); note(self, "resets_handled")
        return False
    ResetMessage.override = RESET

    def EndGate(self):
        note(self, "end_cleanups"); cleanup(self); self.call_function("ClearDeathListener")
        # False enters only the retained native-parent forwarding path.
        return False
    EndGate.override = END

    def AfterDeathDelay(self):
        if self.get_property(ENDED):
            note(self, "cancelled_long_continuations"); return False
        return PythonBase.AfterDeathDelay(self)
    AfterDeathDelay.override = AFTER_LONG

    def AfterRestartDelay(self):
        if self.get_property(ENDED):
            note(self, "cancelled_short_continuations"); return False
        return PythonBase.AfterRestartDelay(self)
    AfterRestartDelay.override = AFTER_SHORT


class LyraAutoRespawnActivationBlueprintFallbackProfile(BlueprintBase):
    GetOwningPlayerState = BlueprintBase.GetOwningPlayerState
    IsAvatarDeadOrDying = BlueprintBase.IsAvatarDeadOrDying
    EndDeathAbilities = BlueprintBase.EndDeathAbilities
    BindDeathListener = BlueprintBase.BindDeathListener
    ClearDeathListener = BlueprintBase.ClearDeathListener
    OnDeathStarted = BlueprintBase.OnDeathStarted
    OnAvatarEndPlay = BlueprintBase.OnAvatarEndPlay

    def K2_OnAbilityAdded(self):
        note(self, "fallback_added"); self.set_property(ENDED, False)
        self.call_mixin_original("K2_OnAbilityAdded")

    def K2_OnAbilityRemoved(self):
        note(self, "fallback_removed"); cleanup(self); self.call_mixin_original("K2_OnAbilityRemoved")

    def K2_ActivateAbility(self):
        note(self, "fallback_activated"); self.set_property(ENDED, False)
        self.call_mixin_original("K2_ActivateAbility")

    def K2_OnPawnAvatarSet(self):
        note(self, "fallback_avatar_set"); self.set_property(ENDED, False)
        self.call_mixin_original("K2_OnPawnAvatarSet")

    def ResetSubscribed(self): note(self, "fallback_subscribed"); return True
    ResetSubscribed.override = SUBSCRIBED

    def ResetMessage(self, OwnerPlayerState):
        note(self, "fallback_reset_messages")
        return not bool(self.get_property(ENDED))
    ResetMessage.override = RESET

    def EndGate(self):
        note(self, "fallback_end_cleanups"); cleanup(self)
        return True
    EndGate.override = END

    def AfterDeathDelay(self):
        if self.get_property(ENDED):
            note(self, "cancelled_long_continuations"); return False
        return BlueprintBase.AfterDeathDelay(self)
    AfterDeathDelay.override = AFTER_LONG

    def AfterRestartDelay(self):
        if self.get_property(ENDED):
            note(self, "cancelled_short_continuations"); return False
        return BlueprintBase.AfterRestartDelay(self)
    AfterRestartDelay.override = AFTER_SHORT
