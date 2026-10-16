"""Read-only snapshots around naturally entered equipment lifecycle handlers."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from . import weapon_instance_mixin as policy


def path(value): return value.get_path_name() if valid(value) else None


def capture(instance, equipped):
    pawn = instance.call_function("GetTypedPawn", ue.find_class("Character"))
    tags = instance.CosmeticAnimStyleTags
    layer = instance.call_function("PickBestAnimLayer", equipped, tags)
    linked = pawn.Mesh.call_function("GetLinkedAnimLayerInstanceByClass", layer) if valid(pawn) and valid(layer) else None
    montage = instance.WeaponEquipMontage if equipped else instance.WeaponUnequipMontage
    anim = pawn.Mesh.call_function("GetAnimInstance") if valid(pawn) else None
    health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent")) if valid(pawn) else None
    return dict(tags=sorted(str(tag.TagName) for tag in tags.GameplayTags), selected_layer=path(layer),
        linked_layer=path(linked.get_class()) if valid(linked) else None, montage=path(montage),
        montage_playing=bool(anim.call_function("Montage_IsPlaying", montage)) if valid(anim) and valid(montage) else False,
        dead_or_dying=bool(health.call_function("IsDeadOrDying")) if valid(health) else False)


def install(root, sink):
    def around(handler, equipped):
        def observed(instance):
            handler(instance)
            sink(instance, equipped)
        return observed
    for name, cls in (("Python", policy.LyraWeaponInstancePythonProfile), ("BlueprintFallback", policy.LyraWeaponInstanceBlueprintFallbackProfile)):
        methods = dict(K2_OnEquipped=around(cls.K2_OnEquipped, True), K2_OnUnequipped=around(cls.K2_OnUnequipped, False),
            DetermineCosmeticTags=cls.DetermineCosmeticTags)
        ue.register_mixin_profile(root, name, type("ObservedWeapon"+name, (), methods))


def restore(root):
    ue.register_mixin_profile(root, "Python", policy.LyraWeaponInstancePythonProfile)
    ue.register_mixin_profile(root, "BlueprintFallback", policy.LyraWeaponInstanceBlueprintFallbackProfile)
