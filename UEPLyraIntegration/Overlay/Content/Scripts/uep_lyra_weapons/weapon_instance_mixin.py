"""Equipment BP decisions, preserving original native animation factory calls."""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid

CLASS = "/ShooterCore/Weapons/B_WeaponInstance_Base.B_WeaponInstance_Base_C"
HERO = "/ShooterCore/Game/B_Hero_ShooterMannequin.B_Hero_ShooterMannequin_C"
_counts = {}
_proxy_paths = {}
_stats = dict(equips=0, unequips=0, tag_queries=0, layer_picks=0, layers_linked=0, montage_calls=0,
    dead_unequips_skipped=0, fallback_equips=0, fallback_unequips=0, fallback_tag_queries=0, errors=[])


def snapshot(): return dict(copy.deepcopy(_stats), active_count=0, script_subscriptions_created=0)


def instance_snapshot(instance):
    return dict({key: 0 for key, value in _stats.items() if type(value) is int}, **_counts.get(instance.get_path_name(), {}))


def proxy_path(instance): return _proxy_paths.get(instance.get_path_name())


def note(instance, key):
    _stats[key] += 1
    path = instance.get_path_name(); values = _counts.setdefault(path, {})
    values[key] = values.get(key, 0)+1
    while len(_counts) > 256: _counts.pop(next(iter(_counts)))


def determine_tags(instance):
    note(instance, "tag_queries")
    pawn = instance.call_function("GetPawn")
    component = pawn.get_component_by_type(ue.find_class("LyraPawnComponent_CharacterParts")) if valid(pawn) else None
    if valid(component):
        instance.CosmeticAnimStyleTags = component.call_function("GetCombinedTags", GameplayTag(TagName="Cosmetic.AnimationStyle"))
    # The original invalid-component branch leaves its cached tags unchanged.


def play_pair(instance, equipped, montage):
    character = instance.call_function("GetTypedPawn", ue.find_class("Character"))
    if not valid(character): return
    layer = instance.call_function("PickBestAnimLayer", equipped, instance.CosmeticAnimStyleTags)
    note(instance, "layer_picks")
    if ue.find_class("KismetSystemLibrary").get_cdo().call_function("IsValidClass", layer):
        character.Mesh.call_function("LinkAnimClassLayers", layer); note(instance, "layers_linked")
    # All original macro callback outputs are disconnected. No Python listener
    # or retained proxy is introduced; native UAnimInstance owns the playback.
    proxy = ue.find_class("PlayMontageCallbackProxy").get_cdo().call_function("CreateProxyObjectForPlayMontage",
        character.Mesh, montage, 1., 0., "None", True)
    if valid(proxy) and hasattr(proxy, "get_path_name"):
        _proxy_paths[instance.get_path_name()] = proxy.get_path_name()
        while len(_proxy_paths) > 256: _proxy_paths.pop(next(iter(_proxy_paths)))
    note(instance, "montage_calls")


class LyraWeaponInstancePythonProfile:
    def K2_OnEquipped(self):
        note(self, "equips")
        try:
            self.call_function("DetermineCosmeticTags")
            play_pair(self, True, self.WeaponEquipMontage)
        except Exception as error: _stats["errors"].append(str(error)); raise

    def DetermineCosmeticTags(self): determine_tags(self)

    def K2_OnUnequipped(self):
        note(self, "unequips")
        try:
            hero = self.call_function("GetTypedPawn", ue.load_class(HERO))
            health = hero.HealthComponent if valid(hero) else None
            if valid(health) and health.call_function("IsDeadOrDying"):
                note(self, "dead_unequips_skipped"); return
            play_pair(self, False, self.WeaponUnequipMontage)
        except Exception as error: _stats["errors"].append(str(error)); raise


class LyraWeaponInstanceBlueprintFallbackProfile:
    def K2_OnEquipped(self):
        note(self, "fallback_equips"); self.call_mixin_original("K2_OnEquipped")

    def DetermineCosmeticTags(self):
        note(self, "fallback_tag_queries"); self.call_mixin_original("DetermineCosmeticTags")

    def K2_OnUnequipped(self):
        note(self, "fallback_unequips"); self.call_mixin_original("K2_OnUnequipped")
