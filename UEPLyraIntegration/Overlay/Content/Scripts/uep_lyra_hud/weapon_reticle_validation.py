"""Real Lyra reticle geometry and typed-message BP/Python differential.

The three retained layouts read the same real equipped weapon. ADS/elimination
messages are native-router test inputs here, not proof of a real ADS/kill action.
"""

import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraVerbMessage, Vector2D

from . import weapon_observer
from . import weapon_reticle_mixin as reticles
from .message_payload_validation_fields import ON, CONTROLLER
from uep_lyra_network_bots import isolate_bots
from uep_lyra_weapon_input import aim_above_players
from .ammo_mixin import MAGAZINE_AMMO, _stat


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def shape(widget):
    return {"radius": float(widget.CrossHairs.get_property("Radius")),
            "width": float(widget.SBOuterReticle.get_property("WidthOverride")),
            "height": float(widget.SBOuterReticle.get_property("HeightOverride"))}


class WeaponReticleValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.elapsed = 0.0
        self.state = "ready"
        self.deadline = 0.0
        self.widgets = []
        self.pairs = []
        self.ads_frames = 0
        self.ads_action = None
        self.original_rotation = None
        self.helper = self.other = None
        self.report = {"schema_version": 1, "status": "running", "cases": [], "message_cases": [],
                       "network_acceptance": False, "full_acceptance": False,
                       "real_ads_input_tested": False, "real_elimination_gameplay_tested": False,
                       "inventory_or_weapon_spread_written": False}

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not weapon_observer.valid(bridge):
                continue
            isolate_bots(statics, world, ue.find_class("LyraPlayerBotController"))
            snapshot = bridge.call_function("CaptureSnapshot")
            if not (snapshot.bExperienceLoaded and snapshot.bAbilitySystemReady and snapshot.bHealthReady
                    and not snapshot.bDamageImmune and snapshot.Health > 0):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            matches = [ue.find_object(path) for path in weapon_observer.snapshot()["active_widgets"]]
            matches = [widget for widget in matches if weapon_observer.valid(widget)
                       and widget.get_class().get_name() in ("W_AmmoCounter_Pistol_C", "W_AmmoCounter_Rifle_C", "W_AmmoCounter_Shotgun_C")
                       and widget.call_function("GetOwningPlayer") == controller]
            if len(matches) != 1 or not weapon_observer.valid(matches[0].WeaponInstance):
                continue
            self.world, self.controller = world, controller
            self.weapon = matches[0].WeaponInstance
            self.pawn = controller.get_controlled_pawn()
            self.instigator = controller.PlayerState
            self.report["native_weapon"] = self.weapon.get_path_name()
            self.report["native_source_counter"] = matches[0].get_path_name()
            self.router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
                "GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
            cls = ue.load_class("/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C")
            self.helper = ue.new_object(cls)
            self.helper.add_to_root()
            self.ui = ue.load_object(ue.find_class("UserDefinedStruct"), "/ShooterCore/Input/Abilities/Struct_UIMessaging.Struct_UIMessaging")
            self.other = world.actor_spawn(ue.find_class("Actor"))
            for column, kind in enumerate(("Pistol", "Rifle", "Shotgun")):
                cls = ue.load_class("/ShooterCore/Weapons/" + kind + "/W_Reticle_" + kind + ".W_Reticle_" + kind + "_C")
                ue.register_declared_mixin(cls)
                pair = []
                for row, profile in enumerate(("BlueprintFallback", "Python")):
                    widget = controller.create_widget(cls)
                    self.widgets.append(widget)
                    ue.set_mixin_profile(widget, profile)
                    check(weapon_observer.valid(widget.PythonMessageAdapterClass), "serialized decoder class default was lost")
                    widget.call_function("InitializeFromWeapon", self.weapon)
                    widget.AddToViewport(200)
                    widget.SetPositionInViewport(Vector2D(X=150 + column * 340, Y=200 + row * 230), False)
                    widget.SetDesiredSizeInViewport(Vector2D(X=180, Y=180))
                    pair.append(widget)
                self.pairs.append((kind, pair[0], pair[1]))
            self.state, self.deadline = "geometry", self.elapsed + 0.5
            return

    def compare(self):
        for kind, baseline, candidate in self.pairs:
            bp, py = shape(baseline), shape(candidate)
            radius = float(candidate.call_function("ComputeMaxScreenspaceSpreadRadius"))
            expected = dict(zip(("radius", "width", "height"), reticles.geometry(kind, radius)))
            check(all(abs(bp[key] - py[key]) < 0.01 and abs(py[key] - expected[key]) < 0.05 for key in expected),
                  "reticle geometry differs: " + repr((kind, bp, py, expected)))
            check(candidate._uep_reticle_ticks > 0, "native automatic Python reticle Tick missing")
            self.report["cases"].append({"kind": kind, "class": candidate.get_class().get_name(),
                                          "bp": bp, "python": py, "native": expected,
                                          "automatic_python_ticks": candidate._uep_reticle_ticks,
                                          "same_class": baseline.get_class() == candidate.get_class()})

    def broadcast_ui(self, enabled, owner):
        payload = self.ui()
        setattr(payload, ON, enabled)
        setattr(payload, CONTROLLER, owner)
        self.helper.call_function("BroadcastUI", self.router, GameplayTag(TagName="Gameplay.Message.ADS"), payload)

    def messages(self):
        self.broadcast_ui(True, self.controller)
        for kind, baseline, candidate in self.pairs:
            check(candidate._uep_reticle_ads is True, "owner ADS message did not reach Python")
            check(not baseline.call_function("IsAnimationPlaying", baseline.AimDownSights)
                  and not candidate.call_function("IsAnimationPlaying", candidate.AimDownSights),
                  "migration executed the authored disconnected ADS animation")
        # A different native Controller identity must not overwrite local ADS.
        foreign = self.world.actor_spawn(ue.find_class("PlayerController"))
        try:
            self.broadcast_ui(False, foreign)
            check(all(candidate._uep_reticle_ads for _, _, candidate in self.pairs), "foreign ADS changed local state")
        finally:
            foreign.actor_destroy()
        verb = LyraVerbMessage(Verb=GameplayTag(TagName="Lyra.Elimination.Message"), Instigator=self.instigator, Target=self.other)
        self.helper.call_function("BroadcastVerb", self.router, GameplayTag(TagName="Lyra.Elimination.Message"), verb)
        self.state, self.deadline = "elimination", self.elapsed + 0.05

    def check_elimination(self):
        self.report["animation_diagnostics"] = []
        for kind, baseline, candidate in self.pairs:
            check(candidate._uep_reticle_eliminations == 1, "typed elimination did not reach Python")
            bp_playing = bool(baseline.call_function("IsAnimationPlayingForward", baseline.Elimination))
            py_playing = bool(candidate.call_function("IsAnimationPlayingForward", candidate.Elimination))
            self.report["animation_diagnostics"].append({"kind": kind, "bp_playing": bp_playing,
                                                        "python_playing": py_playing,
                                                        "bp_profile": ue.get_mixin_profile(baseline),
                                                        "playerstate_controller_matches": self.instigator.call_function("GetLyraPlayerController") == self.controller,
                                                        "bp_async_properties": [name for name in baseline.properties() if "async" in name.lower()]})
            check(bp_playing and py_playing, "BP/Python animation trigger differs: " + repr(self.report["animation_diagnostics"][-1]))
            bp_time = float(baseline.call_function("GetAnimationCurrentTime", baseline.Elimination))
            py_time = float(candidate.call_function("GetAnimationCurrentTime", candidate.Elimination))
            check(abs(bp_time - py_time) < 0.05, "BP/Python animation clocks differ")
            self.report["message_cases"].append({"kind": kind, "local_ads_received": True,
                                                  "foreign_ads_ignored": True, "ads_animation_noop_preserved": True,
                                                  "elimination_triggered": True, "bp_time": bp_time, "python_time": py_time})
        # Repeat while animation is running: preserve restart at zero behavior.
        verb = LyraVerbMessage(Verb=GameplayTag(TagName="Lyra.Elimination.Message"), Instigator=self.instigator, Target=self.other)
        self.helper.call_function("BroadcastVerb", self.router, GameplayTag(TagName="Lyra.Elimination.Message"), verb)
        check(all(candidate._uep_reticle_eliminations == 2 for _, _, candidate in self.pairs), "repeated elimination did not restart")
        suicide = LyraVerbMessage(Verb=GameplayTag(TagName="Lyra.Elimination.Message"), Instigator=self.instigator, Target=self.instigator)
        self.helper.call_function("BroadcastVerb", self.router, GameplayTag(TagName="Lyra.Elimination.Message"), suicide)
        check(all(candidate._uep_reticle_eliminations == 2 for _, _, candidate in self.pairs), "suicide incorrectly triggered elimination")
        self.report["repeated_elimination_and_suicide_filter"] = True
        self.report["image"] = str(self.path.parent / "production-reticle-pairs.png")
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
            'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
        self.state, self.deadline = "capture", self.elapsed + 0.5

    def prepare_shotgun(self):
        pads, = ue.find_class("GameplayStatics").get_cdo().call_function(
            "GetAllActorsOfClass", self.world, ue.find_class("LyraWeaponSpawner"))
        pad = next((value for value in pads if value.bIsWeaponAvailable and value.WeaponDefinition is not None
                    and "Shotgun" in value.WeaponDefinition.InventoryItemDefinition.get_name()), None)
        check(pad is not None, "no native shotgun pickup in the current map")
        pad.call_function("AttemptPickUpWeapon", self.pawn)
        self.quickbar = self.controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
        slots = self.quickbar.call_function("GetSlots")
        index = next((i for i, item in enumerate(slots) if item is not None and "Shotgun" in item.ItemDef.get_name()), None)
        check(index is not None, "native shotgun pickup did not grant inventory")
        self.quickbar.call_function("SetActiveSlotIndex", index)
        self.shotgun_item = slots[index]
        self.shotgun_ammo = int(_stat(self.shotgun_item, MAGAZINE_AMMO))
        check(self.shotgun_ammo > 0, "native shotgun has no starting ammo")
        self.original_rotation = self.controller.call_function("GetControlRotation")
        aim_above_players(self.controller)
        self.report["shotgun_setup"] = {"entry": "AttemptPickUpWeapon", "pad": pad.get_path_name(),
                                        "physical_pickup_tested": False, "inventory_written": False}
        self.state, self.deadline = "shotgun_ready", self.elapsed + 0.5

    def shotgun_ready(self):
        candidates = [ue.find_object(path) for path in weapon_observer.snapshot()["active_widgets"]]
        candidates = [widget for widget in candidates if weapon_observer.valid(widget)
                      and widget.get_class().get_name() == "W_AmmoCounter_Shotgun_C"
                      and widget.call_function("GetOwningPlayer") == self.controller
                      and widget.InventoryInstance == self.shotgun_item]
        if len(candidates) != 1 or not weapon_observer.valid(candidates[0].WeaponInstance):
            return
        self.weapon = candidates[0].WeaponInstance
        for widget in self.widgets:
            widget.call_function("InitializeFromWeapon", self.weapon)
        self.fire_actions = [ue.load_object(ue.find_class("InputAction"), "/Game/Input/Actions/" + name + "." + name)
                             for name in ("IA_Weapon_Fire", "IA_Weapon_Fire_Auto")]
        self.fire_frames = 0
        self.state = "shotgun_fire"

    def finish(self, error=None):
        try:
            if self.ads_action is not None and weapon_observer.valid(self.controller):
                self.controller.inject_enhanced_input_for_action(self.ads_action, False)
            if self.original_rotation is not None and weapon_observer.valid(self.controller):
                self.controller.call_function("SetControlRotation", self.original_rotation)
            for widget in self.widgets:
                if weapon_observer.valid(widget):
                    if ue.get_mixin_profile(widget) == "BlueprintFallback":
                        # The original graph has both proxies wired to one
                        # Cancel input. Dispose both *test-owned* baseline tasks.
                        for name in [value for value in widget.properties() if "async" in value.lower()]:
                            proxy = widget.get_property(name)
                            if weapon_observer.valid(proxy):
                                proxy.call_function("Cancel")
                    widget.RemoveFromParent()
            if weapon_observer.valid(self.other):
                self.other.actor_destroy()
            if weapon_observer.valid(self.helper):
                self.helper.remove_from_root()
            self.report["reticle_observers_before_exit"] = reticles.snapshot()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "passed", error=error,
                           elapsed_seconds=time.monotonic() - self.started)
        # Final callback state is captured without UObject calls at interpreter
        # exit, after native World/widget destruction and Mixin teardown.
        if not error:
            import atexit
            def finalize():
                final = reticles.snapshot()
                self.report["reticle_shutdown"] = final
                if final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"]:
                    self.report["status"], self.report["error"] = "failed", "reticle scopes survived shutdown"
                self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
                (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WEAPON_RETICLE_SHUTDOWN_" + self.report["status"].upper())
            atexit.register(finalize)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_WEAPON_RETICLE_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def tick(self, delta):
        try:
            self.elapsed += delta
            check(time.monotonic() - self.started < 180, "weapon reticle fixture timed out: " + self.state)
            if self.state == "ready":
                self.ready()
            elif self.elapsed >= self.deadline:
                if self.state == "geometry":
                    self.compare()
                    self.messages()
                elif self.state == "elimination":
                    self.check_elimination()
                elif self.state == "capture":
                    check(Path(self.report["image"]).is_file(), "reticle screenshot missing")
                    self.broadcast_ui(False, self.controller)
                    self.ads_start = reticles.snapshot()["ads_messages"]
                    self.ads_action = ue.load_object(ue.find_class("InputAction"), "/ShooterCore/Input/Actions/IA_ADS.IA_ADS")
                    self.ads_frames = 0
                    self.state = "ads_pressed"
                elif self.state == "shotgun_ready":
                    self.shotgun_ready()
                elif self.state == "shotgun_settle":
                    self.compare()
                    self.report["real_equipped_shotgun_tested"] = True
                    self.report["native_shotgun_weapon"] = self.weapon.get_path_name()
                    self.report["native_shotgun_ammo_before"] = self.shotgun_ammo
                    self.report["native_shotgun_ammo_after"] = int(_stat(self.shotgun_item, MAGAZINE_AMMO))
                    self.finish()
                    return False
            if self.state == "ads_pressed":
                self.controller.inject_enhanced_input_for_action(self.ads_action, True)
                self.ads_frames += 1
                if self.ads_frames >= 30:
                    check(all(candidate._uep_reticle_ads for _, _, candidate in self.pairs), "native ADS input did not deliver owner message")
                    check(reticles.snapshot()["ads_messages"] > self.ads_start, "native ADS ability produced no typed message")
                    self.report["native_ads_pressed_messages"] = reticles.snapshot()["ads_messages"] - self.ads_start
                    self.ads_frames = 0
                    self.state = "ads_released"
            elif self.state == "ads_released":
                self.controller.inject_enhanced_input_for_action(self.ads_action, False)
                self.ads_frames += 1
                if self.ads_frames >= 30:
                    check(not any(candidate._uep_reticle_ads for _, _, candidate in self.pairs), "native ADS release left reticle state active")
                    check(reticles.snapshot()["ads_messages"] > self.ads_start + self.report["native_ads_pressed_messages"],
                          "native ADS ability produced no release message")
                    self.report["real_ads_input_tested"] = True
                    self.report["native_ads_input_action"] = self.ads_action.get_path_name()
                    self.report["native_ads_pressed_frames"] = self.report["native_ads_released_frames"] = 30
                    self.prepare_shotgun()
            elif self.state == "shotgun_fire":
                pressed = self.fire_frames % 15 < 3
                for action in self.fire_actions:
                    self.controller.inject_enhanced_input_for_action(action, pressed)
                self.fire_frames += 1
                if self.fire_frames >= 60:
                    check(int(_stat(self.shotgun_item, MAGAZINE_AMMO)) < self.shotgun_ammo, "native shotgun firing did not consume ammo")
                    self.state, self.deadline = "shotgun_settle", self.elapsed + 0.5
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPWeaponReticleResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = WeaponReticleValidation(result)
ticker = ue.add_ticker(validation.tick)
