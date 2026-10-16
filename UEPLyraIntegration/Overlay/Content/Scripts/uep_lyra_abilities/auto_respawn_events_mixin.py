"""Death/restart decisions; original native latent nodes and RPC do transport."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraInteractionDurationMessage, LyraVerbMessage
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_listeners_mixin import (LyraAutoRespawnListenersPythonProfile as PythonBase,
    LyraAutoRespawnListenersBlueprintFallbackProfile as BlueprintBase)

START_LONG, START_SHORT = "UEPAutoRespawnStartDeathDelay", "UEPAutoRespawnStartRestartDelay"
AFTER_LONG, AFTER_SHORT = "UEPAutoRespawnAfterDeathDelay", "UEPAutoRespawnAfterRestartDelay"
DURATION, COMPLETED = "Ability.Respawn.Duration.Message", "Ability.Respawn.Completed.Message"
ADAPTER = "/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C"
_stats = dict(death_events=0, avatar_end_events=0, duration_messages=0, long_delays_started=0,
    long_continuations=0, short_delays_started=0, short_continuations=0, native_restarts=0,
    native_completion_rpcs=0, cosmetic_completion_messages=0, fallback_death_events=0,
    fallback_avatar_end_events=0, fallback_long_continuations=0, fallback_short_continuations=0)


def snapshot(): return copy.deepcopy(_stats)
def instance_snapshot(ability): return dict(getattr(ability, "_uep_auto_event_counts", {}))


def note(ability, key):
    _stats[key] += 1
    values = instance_snapshot(ability); values[key] = values.get(key, 0)+1
    ability._uep_auto_event_counts = values


def statics(): return ue.find_class("GameplayStatics").get_cdo()


def broadcast(ability, suffix, channel, payload):
    router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
        "GetGameInstanceSubsystem", ability, ue.find_class("GameplayMessageSubsystem"))
    ue.load_class(ADAPTER).get_cdo().call_function("Broadcast"+suffix, router, GameplayTag(TagName=channel), payload)


def end_death_and_wait(ability):
    controller = ability.get_property("ControllerToReset")
    if not valid(controller): return
    asc = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("GetAbilitySystemComponent", controller.PlayerState)
    ability.call_function("EndDeathAbilities", asc)
    ability.call_function(START_SHORT); note(ability, "short_delays_started")


def restart(ability):
    game_mode = statics().call_function("GetGameMode", ability)
    if not valid(game_mode) or not game_mode.is_a(ue.find_class("LyraGameMode")): return
    game_mode.call_function("RequestPlayerRestartNextFrame", ability.get_property("ControllerToReset"), True)
    note(ability, "native_restarts")
    payload = LyraVerbMessage(Verb=GameplayTag(TagName=COMPLETED),
        Instigator=ability.call_function("GetOwningPlayerState"), Magnitude=1.)
    game_state = statics().call_function("GetGameState", ability)
    if valid(game_state) and game_state.is_a(ue.find_class("LyraGameState")):
        game_state.call_function("MulticastReliableMessageToClients", payload); note(ability, "native_completion_rpcs")
    if not ue.find_class("KismetSystemLibrary").get_cdo().call_function("IsDedicatedServer", ability):
        broadcast(ability, "Verb", COMPLETED, payload); note(ability, "cosmetic_completion_messages")


class LyraAutoRespawnEventsPythonProfile(PythonBase):
    GetOwningPlayerState = PythonBase.GetOwningPlayerState
    IsAvatarDeadOrDying = PythonBase.IsAvatarDeadOrDying
    EndDeathAbilities = PythonBase.EndDeathAbilities
    BindDeathListener = PythonBase.BindDeathListener
    ClearDeathListener = PythonBase.ClearDeathListener

    def OnDeathStarted(self, DyingActor):
        note(self, "death_events")
        self.call_function("ClearDeathListener")
        controller = self.call_function("GetControllerFromActorInfo")
        self.set_property("ControllerToReset", controller)
        if not valid(controller): return
        broadcast(self, "Duration", DURATION, LyraInteractionDurationMessage(
            Instigator=self.call_function("GetOwningPlayerState"), Duration=float(self.RespawnDelayDuration)))
        note(self, "duration_messages")
        if self.call_function("K2_HasAuthority"):
            self.set_property("ShouldFinishRestart", True)
            self.call_function(START_LONG); note(self, "long_delays_started")

    def OnAvatarEndPlay(self, Actor, EndPlayReason):
        note(self, "avatar_end_events")
        if not self.call_function("K2_HasAuthority"): return
        self.set_property("ControllerToReset", self.call_function("GetControllerFromActorInfo"))
        self.call_function("ClearDeathListener")
        self.set_property("ShouldFinishRestart", False)
        end_death_and_wait(self)

    def AfterDeathDelay(self):
        note(self, "long_continuations")
        if self.ShouldFinishRestart:
            self.set_property("ShouldFinishRestart", False)
            end_death_and_wait(self)
        return False
    AfterDeathDelay.override = AFTER_LONG

    def AfterRestartDelay(self):
        note(self, "short_continuations"); restart(self)
        return False
    AfterRestartDelay.override = AFTER_SHORT


class LyraAutoRespawnEventsBlueprintFallbackProfile(BlueprintBase):
    GetOwningPlayerState = BlueprintBase.GetOwningPlayerState
    IsAvatarDeadOrDying = BlueprintBase.IsAvatarDeadOrDying
    EndDeathAbilities = BlueprintBase.EndDeathAbilities
    BindDeathListener = BlueprintBase.BindDeathListener
    ClearDeathListener = BlueprintBase.ClearDeathListener

    def OnDeathStarted(self, DyingActor):
        note(self, "fallback_death_events"); self.call_mixin_original("OnDeathStarted", DyingActor)

    def OnAvatarEndPlay(self, Actor, EndPlayReason):
        note(self, "fallback_avatar_end_events"); self.call_mixin_original("OnAvatarEndPlay", Actor, EndPlayReason)

    def AfterDeathDelay(self):
        note(self, "fallback_long_continuations"); return True
    AfterDeathDelay.override = AFTER_LONG

    def AfterRestartDelay(self):
        note(self, "fallback_short_continuations"); return True
    AfterRestartDelay.override = AFTER_SHORT
