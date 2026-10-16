"""Three AutoRespawn helpers only; original BP still owns listeners/restart."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C"
DEAD_QUERY = "Is Avatar Dead or Dying"
METHODS = ("GetOwningPlayerState", DEAD_QUERY, "EndDeathAbilities")
_stats = dict(player_state_queries=0, death_queries=0, death_end_calls=0, abilities_ended=0,
    fallback_player_state_queries=0, fallback_death_queries=0, fallback_death_end_calls=0)


def snapshot(): return copy.deepcopy(_stats)


def instance_snapshot(ability):
    return dict(getattr(ability, "_uep_auto_helpers_counts", {}))


def note(ability, key):
    _stats[key] += 1
    values = instance_snapshot(ability); values[key] = values.get(key, 0)+1
    ability._uep_auto_helpers_counts = values


class LyraAutoRespawnHelpersPythonProfile:
    def GetOwningPlayerState(self):
        note(self, "player_state_queries")
        asc = self.call_function("GetLyraAbilitySystemComponentFromActorInfo")
        return asc.call_function("GetOwner") if valid(asc) else None

    def IsAvatarDeadOrDying(self):
        note(self, "death_queries")
        avatar = self.call_function("GetAvatarActorFromActorInfo")
        if not valid(avatar): return {"IsDeadOrDying": False}
        health = ue.find_class("LyraHealthComponent").get_cdo().call_function("FindHealthComponent", avatar)
        return {"IsDeadOrDying": bool(health.call_function("IsDeadOrDying")) if valid(health) else False}
    IsAvatarDeadOrDying.override = DEAD_QUERY
    IsAvatarDeadOrDying.uep_named_outputs = True

    def EndDeathAbilities(self, AbilitySystem):
        note(self, "death_end_calls")
        # Match the original exact death-tag query and native primary-instance
        # resolution. Never end other tags, write specs, or synthesize a death.
        if not valid(AbilitySystem): return
        tags = GameplayTagContainer(GameplayTags=[GameplayTag(TagName="Ability.Type.StatusChange.Death")])
        handles, = AbilitySystem.call_function("FindAllAbilitiesWithTags", Tags=tags, bExactMatch=True)
        library = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
        for handle in handles:
            ability, is_instance = library.call_function("GetGameplayAbilityFromSpecHandle", AbilitySystem, handle)
            if valid(ability):
                ability.call_function("K2_EndAbility"); note(self, "abilities_ended")


class LyraAutoRespawnHelpersBlueprintFallbackProfile:
    def GetOwningPlayerState(self):
        note(self, "fallback_player_state_queries")
        return self.call_mixin_original("GetOwningPlayerState")

    def IsAvatarDeadOrDying(self):
        note(self, "fallback_death_queries")
        result, = self.call_mixin_original(DEAD_QUERY)
        return {"IsDeadOrDying": result}
    IsAvatarDeadOrDying.override = DEAD_QUERY
    IsAvatarDeadOrDying.uep_named_outputs = True

    def EndDeathAbilities(self, AbilitySystem):
        note(self, "fallback_death_end_calls")
        self.call_mixin_original("EndDeathAbilities", AbilitySystem)
