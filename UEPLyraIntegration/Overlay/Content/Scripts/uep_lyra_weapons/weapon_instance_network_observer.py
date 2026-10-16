"""Read-only production equipment events during existing real network fixtures."""
import copy
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.inventory_pad_network_state import services
from uep_lyra_world.effect_pad_mixin import valid
from . import weapon_instance_mixin as policy, weapon_instance_observation as observation

CLASSES = dict(rifle="/ShooterCore/Weapons/Rifle/B_WeaponInstance_Rifle.B_WeaponInstance_Rifle_C",
    shotgun="/ShooterCore/Weapons/Shotgun/B_WeaponInstance_Shotgun.B_WeaponInstance_Shotgun_C",
    netshooter="/ShooterCore/Weapons/NetShooter_PROTO/B_WeaponInstance_NetShooter.B_WeaponInstance_NetShooter_C")


def native_style_tags(pawn):
    component = pawn.get_component_by_type(ue.find_class("LyraPawnComponent_CharacterParts"))
    if not valid(component): raise RuntimeError("equipment integration requires native character parts component")
    tags = component.call_function("GetCombinedTags", GameplayTag(TagName="Cosmetic.AnimationStyle"))
    return sorted(str(tag.TagName) for tag in tags.GameplayTags)


class Observer:
    def __init__(self, peer):
        self.peer, self.events, self.initials, self.errors, self.closed = peer, [], {}, [], False
        self.root = ue.load_class(policy.CLASS)
        self.profile = "BlueprintFallback" if "-UEPEquipmentProfile=BlueprintFallback" in sys.argv else "Python"
        self.cdo, self.original_profile = None, None
        if self.profile == "BlueprintFallback":
            weapon = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPReloadWeapon="))
            self.cdo = ue.load_class(CLASSES[weapon]).get_cdo()
            self.original_profile = str(self.cdo.get_property("PythonMixinProfile"))
            self.cdo.set_property("PythonMixinProfile", self.profile)
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        observation.install(self.root, self.received)

    def received(self, instance, equipped):
        try:
            pawn = instance.call_function("GetPawn")
            controller = pawn.call_function("GetController") if valid(pawn) else None
            if not valid(controller) or not controller.is_a(ue.find_class("LyraPlayerController")) or not valid(controller.PlayerState): return
            if self.peer != "server" and not controller.call_function("IsLocalPlayerController"): return
            self.events.append(dict(player_id=int(controller.PlayerState.PlayerId), native_role=int(pawn.call_function("GetLocalRole")),
                native_class=instance.get_class().get_path_name(), instance=instance.get_path_name(), equipped=equipped,
                profile=str(ue.get_mixin_profile(instance)), state=observation.capture(instance, equipped),
                native_cosmetic_tags=native_style_tags(pawn),
                counters=policy.instance_snapshot(instance), game_time=float(self.statics.call_function("GetTimeSeconds", pawn))))
        except Exception: self.errors.append(traceback.format_exc())

    def note_initial(self, controller):
        player_id = str(int(controller.PlayerState.PlayerId))
        if player_id in self.initials: return
        pawn = controller.get_controlled_pawn(); _, quickbar = services(controller)
        item = quickbar.call_function("GetActiveSlotItem")
        manager = pawn.get_component_by_type(ue.find_class("LyraEquipmentManagerComponent"))
        matches = [value for value in manager.call_function("GetEquipmentInstancesOfType", ue.find_class("LyraWeaponInstance"))
            if valid(value) and value.call_function("GetInstigator") == item]
        if len(matches) != 1: raise RuntimeError("native integration requires actual equipped item/instance")
        instance = matches[0]
        self.initials[player_id] = dict(native_class=instance.get_class().get_path_name(), native_role=int(pawn.call_function("GetLocalRole")),
            source_item_matches=True, profile=str(ue.get_mixin_profile(instance)), counters=policy.instance_snapshot(instance),
            native_cosmetic_tags=native_style_tags(pawn),
            state=observation.capture(instance, True))

    def ready_to_close(self):
        return bool(self.initials) and all(any(str(row["player_id"]) == player_id and row["native_class"] == initial["native_class"] and not row["equipped"]
            for row in self.events) for player_id, initial in self.initials.items())

    def close(self):
        if self.cdo is not None:
            self.cdo.set_property("PythonMixinProfile", self.original_profile)
            if str(self.cdo.get_property("PythonMixinProfile")) != self.original_profile: raise RuntimeError("equipment CDO selector restore failed")
        if not self.closed: observation.restore(self.root); self.closed = True
        return dict(read_only=True, peer=self.peer, events=copy.deepcopy(self.events), initials=copy.deepcopy(self.initials),
            errors=list(self.errors), restored=self.closed, scripted_replication=False, animation_state_written=False,
            profile=self.profile, fixture_cdo_profile_selector_written=self.cdo is not None, cdo_profile_selector_restored=True)
