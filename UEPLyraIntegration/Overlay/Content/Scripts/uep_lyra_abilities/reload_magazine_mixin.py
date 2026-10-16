"""Magazine reload decisions; native montage/event tasks and ammo replication."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/Game/Weapons/GA_Weapon_ReloadMagazine.GA_Weapon_ReloadMagazine_C"
NATIVE_END, GUARD = "UEPReloadMagazineNativeEnded", "UEPReloadMagazineTearingDown"
MAGAZINE, CAPACITY, SPARE = ("Lyra.ShooterGame.Weapon."+name for name in ("MagazineAmmo", "MagazineSize", "SpareAmmo"))
NO_FIRING, RELOAD_DONE = "Ability.Weapon.NoFiring", "GameplayEvent.ReloadDone"
_active = {}
_stats = dict(activations=0, can_activate_checks=0, magazine_full_refusals=0, no_spare_refusals=0,
    tasks_created=0, scopes_created=0, scopes_closed=0, native_ends=0, reload_events=0,
    authority_reloads=0, transferred_rounds=0, client_events=0, blocks_added=0, blocks_removed=0,
    montage_completions=0, montage_interrupts=0, montage_cancels=0,
    fallback_activations=0, fallback_native_ends=0, fallback_reloads=0, errors=[])


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_abilities=list(_active.values()))


def container(tag):
    return ue.find_class("BlueprintGameplayTagLibrary").get_cdo().call_function(
        "MakeGameplayTagContainerFromTag", GameplayTag(TagName=tag))


def ammo(item):
    return tuple(int(item.call_function("GetStatTagStackCount", GameplayTag(TagName=tag))) for tag in (MAGAZINE, CAPACITY, SPARE))


def can_activate(ability):
    _stats["can_activate_checks"] += 1
    magazine, capacity, spare = ammo(ability.call_function("GetAssociatedItem"))
    failure = "MagazineFull" if magazine >= capacity else ("NoSpareAmmo" if spare <= 0 else None)
    if failure is not None: _stats["magazine_full_refusals" if failure == "MagazineFull" else "no_spare_refusals"] += 1
    return dict(ReturnValue=failure is None, RelevantTags=container("Ability.ActivateFail."+failure) if failure else GameplayTagContainer())


def reload_ammo(ability):
    # This public BP function itself has no authority branch. Its gameplay-event
    # caller owns that check; preserve public behavior and native item API calls.
    item = ability.call_function("GetAssociatedItem")
    magazine, capacity, spare = ammo(item)
    transfer = min(capacity, magazine+spare)-magazine
    item.call_function("AddStatTagStack", GameplayTag(TagName=MAGAZINE), transfer)
    item.call_function("RemoveStatTagStack", GameplayTag(TagName=SPARE), transfer)
    _stats["transferred_rounds"] += transfer


def close(ability):
    scope = ability._uep_reload_magazine_scope
    ability._uep_reload_magazine_scope = None
    _active.pop(id(ability), None)
    if scope is not None: scope.close(); _stats["scopes_closed"] += 1


def cleanup(ability):
    if not ability.DidBlockFiring: return
    ability.DidBlockFiring = False
    ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("RemoveLooseGameplayTags",
        ability.call_function("GetOwningActorFromActorInfo"), container(NO_FIRING), False)
    _stats["blocks_removed"] += 1


def request_end(ability, reason):
    _stats[reason] += 1
    ability.call_function("K2_EndAbilityLocally" if reason == "montage_completions" else "K2_EndAbility")


def reloaded(ability, payload):
    _stats["reload_events"] += 1
    if ability.call_function("K2_HasAuthority"):
        _stats["authority_reloads"] += 1
        ability.call_function("ReloadAmmoIntoMagazine", None)
        ability.call_function("K2_EndAbility")
    else: _stats["client_events"] += 1


def activate(ability):
    close(ability)
    scope = SubscriptionScope(); ability._uep_reload_magazine_scope = scope
    _active[id(ability)] = ability.get_path_name()
    _stats["activations"] += 1; _stats["scopes_created"] += 1
    try:
        ability.DidBlockFiring = ammo(ability.call_function("GetAssociatedItem"))[0] == 0
        if ability.DidBlockFiring:
            ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("AddLooseGameplayTags",
                ability.call_function("GetOwningActorFromActorInfo"), container(NO_FIRING), False)
            _stats["blocks_added"] += 1
        montage = ue.find_class("AbilityTask_PlayMontageAndWait").get_cdo().call_function("CreatePlayMontageAndWaitProxy",
            OwningAbility=ability, TaskInstanceName="None", MontageToPlay=ability.ReloadMontage,
            Rate=ability.Playrate, StartSection="None", bStopWhenAbilityEnds=False,
            AnimRootMotionTranslationScale=1., StartTimeSeconds=0., bAllowInterruptAfterBlendOut=False)
        if not valid(montage): raise RuntimeError("native reload montage task factory failed")
        _stats["tasks_created"] += 1
        for name, reason in (("OnCompleted", "montage_completions"), ("OnInterrupted", "montage_interrupts"), ("OnCancelled", "montage_cancels")):
            scope.bind_event(montage, name, lambda cause=reason: request_end(ability, cause))
        montage.call_function("ReadyForActivation")
        if not ability.get_property("bIsActive"): return
        event = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function("WaitGameplayEvent", ability,
            GameplayTag(TagName=RELOAD_DONE), None, True, True)
        if not valid(event): raise RuntimeError("native reload event task factory failed")
        _stats["tasks_created"] += 1
        scope.bind_event(event, "EventReceived", lambda payload: reloaded(ability, payload))
        event.call_function("ReadyForActivation")
    except Exception as error:
        _stats["errors"].append(str(error)); teardown(ability); raise


def teardown(ability):
    ability.set_property(GUARD, True)
    try:
        close(ability)
        if ability.get_property("bIsActive"):
            cleanup(ability); ability.call_function("K2_EndAbility")
    finally: ability.set_property(GUARD, False)


class LyraReloadMagazinePythonProfile:
    def __init__(self): self._uep_reload_magazine_scope = None

    def K2_CanActivateAbility(self, ActorInfo, Handle): return can_activate(self)
    K2_CanActivateAbility.uep_named_outputs = True

    def ReloadAmmoIntoMagazine(self, State): reload_ammo(self)

    def K2_ActivateAbility(self): activate(self)

    def NativeEnded(self, bWasCancelled):
        close(self); cleanup(self); _stats["native_ends"] += 1
        return False
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self): teardown(self)


class LyraReloadMagazineBlueprintFallbackProfile:
    def __init__(self): self._uep_reload_magazine_scope = None
    # Omit CanActivate deliberately: the router's missing-method fallback keeps
    # all native return/named-output storage, with no Python tuple remapping.

    def ReloadAmmoIntoMagazine(self, State):
        _stats["fallback_reloads"] += 1; self.call_mixin_original("ReloadAmmoIntoMagazine", State)

    def K2_ActivateAbility(self):
        _stats["fallback_activations"] += 1; self.call_mixin_original("K2_ActivateAbility")

    def NativeEnded(self, bWasCancelled):
        _stats["fallback_native_ends"] += 1
        return self.call_mixin_original(NATIVE_END, bWasCancelled)
    NativeEnded.override = NATIVE_END

    def __uep_mixin_teardown__(self): teardown(self)
