"""AutoRespawn listener orchestration; exact native BP delegates own delivery."""
import copy
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_helpers_mixin import (LyraAutoRespawnHelpersPythonProfile,
    LyraAutoRespawnHelpersBlueprintFallbackProfile)

BIND_END, UNBIND_END = "UEPAutoRespawnBindEndPlay", "UEPAutoRespawnUnbindEndPlay"
BIND_DEATH, UNBIND_DEATH = "UEPAutoRespawnBindDeath", "UEPAutoRespawnUnbindDeath"
_stats = dict(bind_calls=0, clear_calls=0, avatar_binds=0, health_binds=0,
    avatar_unbinds=0, health_unbinds=0, fallback_bind_calls=0, fallback_clear_calls=0)


def snapshot(): return copy.deepcopy(_stats)


def instance_snapshot(ability): return dict(getattr(ability, "_uep_auto_listener_counts", {}))


def note(ability, key):
    _stats[key] += 1
    values = instance_snapshot(ability); values[key] = values.get(key, 0)+1
    ability._uep_auto_listener_counts = values


class LyraAutoRespawnListenersPythonProfile(LyraAutoRespawnHelpersPythonProfile):
    # The current native Mixin collector deliberately scans the local class
    # dictionary. Expose reused functions explicitly, preserving their override
    # name and named-output metadata without duplicating their implementation.
    GetOwningPlayerState = LyraAutoRespawnHelpersPythonProfile.GetOwningPlayerState
    IsAvatarDeadOrDying = LyraAutoRespawnHelpersPythonProfile.IsAvatarDeadOrDying
    EndDeathAbilities = LyraAutoRespawnHelpersPythonProfile.EndDeathAbilities

    def BindDeathListener(self):
        note(self, "bind_calls")
        self.call_function("ClearDeathListener")
        avatar = self.call_function("GetAvatarActorFromActorInfo")
        if not valid(avatar): return
        self.set_property("LastBoundAvatarActor", avatar)
        self.call_function(BIND_END, avatar); note(self, "avatar_binds")
        health = ue.find_class("LyraHealthComponent").get_cdo().call_function("FindHealthComponent", avatar)
        self.set_property("LastBoundHealthComponent", health)
        if valid(health):
            self.call_function(BIND_DEATH, health); note(self, "health_binds")

    def ClearDeathListener(self):
        note(self, "clear_calls")
        avatar, health = self.get_property("LastBoundAvatarActor"), self.get_property("LastBoundHealthComponent")
        if valid(avatar):
            self.call_function(UNBIND_END, avatar); note(self, "avatar_unbinds")
        if valid(health):
            self.call_function(UNBIND_DEATH, health); note(self, "health_unbinds")
        # The original intentionally retains LastBoundAvatarActor; preserve it
        # so BP/Python can clear each other's exact named native bindings.
        self.set_property("LastBoundHealthComponent", None)


class LyraAutoRespawnListenersBlueprintFallbackProfile(LyraAutoRespawnHelpersBlueprintFallbackProfile):
    GetOwningPlayerState = LyraAutoRespawnHelpersBlueprintFallbackProfile.GetOwningPlayerState
    IsAvatarDeadOrDying = LyraAutoRespawnHelpersBlueprintFallbackProfile.IsAvatarDeadOrDying
    EndDeathAbilities = LyraAutoRespawnHelpersBlueprintFallbackProfile.EndDeathAbilities

    def BindDeathListener(self):
        note(self, "fallback_bind_calls"); self.call_mixin_original("BindDeathListener")

    def ClearDeathListener(self):
        note(self, "fallback_clear_calls"); self.call_mixin_original("ClearDeathListener")
