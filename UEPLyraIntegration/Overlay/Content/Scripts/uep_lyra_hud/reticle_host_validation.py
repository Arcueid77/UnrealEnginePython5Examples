"""Production host native Tick, profile lifetime and original-BP comparisons.

Pickup and death use native entries/events, not physical input or lethal-damage
proof. The hidden baseline is test-owned; the candidate is the actual HUD host.
"""

import atexit
import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayEventData

from . import reticle_host_mixin as hosts
from . import weapon_reticle_mixin as reticles
from .weapon_observer import valid
from uep_lyra_network_bots import isolate_bots


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def widgets(world, cls):
    result, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", world, [], cls, False)
    return result


def shape(host):
    children = list(host.SpawnedWidgets)
    return {"class": host.get_class().get_name(), "owner": host.call_function("GetOwningPlayer").get_path_name(),
            "children": [{"class": widget.get_class().get_name(), "weapon": widget.WeaponInstance.get_path_name(),
                          "item": widget.InventoryInstance.get_path_name(),
                          "horizontal": int(widget.Slot.HorizontalAlignment), "vertical": int(widget.Slot.VerticalAlignment)}
                         for widget in children],
            "overlay_children": int(host.WidgetStack.call_function("GetChildrenCount")),
            "visibility": int(host.VisWrapper.call_function("GetVisibility"))}


class ReticleHostValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.state = "ready"
        self.baseline = self.dummy_weapon = None
        self.frame = 0
        self.report = {"schema_version": 1, "status": "running", "cases": [], "full_acceptance": False,
                       "network_acceptance": False, "production_host": True, "physical_pickup_tested": False,
                       "lethal_damage_tested": False, "native_death_event_injected": False,
                       "inventory_weapon_health_properties_written": False}
        atexit.register(self.finalize)

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def phase(self, name):
        self.state, self.phase_started, self.frame = name, time.monotonic(), 0

    def ready(self):
        statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5):
                continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge):
                continue
            isolate_bots(statics, world, ue.find_class("LyraPlayerBotController"))
            snapshot = bridge.call_function("CaptureSnapshot")
            if not (snapshot.bExperienceLoaded and snapshot.bHealthReady and not snapshot.bDamageImmune):
                continue
            controller = statics.call_function("GetPlayerController", world, 0)
            cls = ue.load_class(hosts.HOST_CLASS)
            candidates = [widget for widget in widgets(world, cls) if widget.call_function("GetOwningPlayer") == controller]
            if len(candidates) != 1 or not candidates[0].SpawnedWidgets:
                continue
            self.world, self.controller, self.host, self.bridge = world, controller, candidates[0], bridge
            check(str(ue.get_mixin_profile(self.host)) == "Python", "production host did not select Python by its declaration")
            check(self.host._uep_reticle_host_changes > 0 and self.host._uep_reticle_host_ticks > 0,
                  "production native Tick/weapon event did not reach Python")
            self.baseline = controller.create_widget(cls)
            self.baseline.add_to_root()
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            self.baseline.AddToViewport(300)
            self.baseline.call_function("SetRenderOpacity", 0.0)
            self.phase("initial")
            return

    def record(self, name, nonempty=True):
        actual, original = shape(self.host), shape(self.baseline)
        check(actual == original, "host BP/Python state differs: " + name + " " + repr((original, actual)))
        check(actual["overlay_children"] == len(actual["children"]), "native overlay contains stale children")
        check(bool(actual["children"]) == nonempty, "reticle presence differs: " + name)
        if nonempty:
            check(all(child["horizontal"] == child["vertical"] == 0 for child in actual["children"]), "authored fill alignment differs")
        self.report["cases"].append({"name": name, "profile": str(ue.get_mixin_profile(self.host)), "same_class": True,
                                     "automatic_ticks": self.host._uep_reticle_host_ticks, "python": actual, "blueprint": original})

    def pickup(self, kind):
        self.previous_weapon = self.host.CurrentInstance.get_path_name()
        actors, = ue.find_class("GameplayStatics").get_cdo().call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraWeaponSpawner"))
        spawner = next((actor for actor in actors if actor.bIsWeaponAvailable and valid(actor.WeaponDefinition)
                        and kind in actor.WeaponDefinition.InventoryItemDefinition.get_name()), None)
        check(spawner is not None, "no native " + kind + " pickup")
        spawner.call_function("AttemptPickUpWeapon", self.controller.get_controlled_pawn())
        quickbar = self.controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"))
        slots = quickbar.call_function("GetSlots")
        index = None
        for candidate, item in enumerate(slots):
            if not valid(item):
                continue
            fragment = item.call_function("FindFragmentByClass", ue.find_class("InventoryFragment_ReticleConfig"))
            if valid(fragment) and any(kind in cls.get_name() for cls in fragment.ReticleWidgets):
                index = candidate
                break
        check(index is not None, "native pickup did not grant " + kind)
        quickbar.call_function("SetActiveSlotIndex", index)
        self.phase(kind.lower())

    def cleanup(self):
        if valid(self.baseline):
            self.baseline.RemoveFromParent()
            self.baseline.remove_from_root()
            self.baseline = None
        if valid(self.dummy_weapon):
            self.dummy_weapon.remove_from_root()
            self.dummy_weapon = None

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic() - self.started, host_before_exit=hosts.snapshot())
        self.write()
        (ue.log_error if error else ue.log)("UEP_RETICLE_HOST_DIFFERENTIAL_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        # Only copied Python metadata after native teardown; no UObject calls.
        self.report["host_shutdown"] = hosts.snapshot()
        self.report["reticle_shutdown"] = reticles.snapshot()
        for key in ("host_shutdown", "reticle_shutdown"):
            final = self.report[key]
            if final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"]:
                self.report.update(status="failed", error="owned scopes remained: " + key)
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)(
            "UEP_RETICLE_HOST_SHUTDOWN_" + self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 240, "reticle host total timeout")
            if self.state == "ready":
                self.ready()
                return True
            self.frame += 1
            check(time.monotonic() - self.phase_started < 30, "reticle host phase timeout: " + self.state)
            if self.frame < 30:
                return True
            if self.state == "initial":
                if not self.baseline.SpawnedWidgets:
                    return True
                self.record("production-native-initial")
                self.retained_children = [widget.get_path_name() for widget in self.host.SpawnedWidgets]
                ue.set_mixin_profile(self.host, "BlueprintFallback")
                self.phase("fallback")
            elif self.state == "fallback":
                self.record("live-blueprint-profile")
                check(self.retained_children == [widget.get_path_name() for widget in self.host.SpawnedWidgets], "fallback cleared live reticles")
                ue.set_mixin_profile(self.host, "Python")
                self.phase("python_again")
            elif self.state == "python_again":
                self.record("live-python-profile-resumed")
                check(self.retained_children == [widget.get_path_name() for widget in self.host.SpawnedWidgets], "profile replayed weapon creation")
                check(self.host._uep_reticle_host_changes == 0, "same native weapon emitted a synthetic change during profile switch")
                self.weapon = self.host.CurrentInstance
                for host in (self.host, self.baseline):
                    host.call_function("OnWeaponChanged", self.weapon, None)
                self.phase("null_weapon")
            elif self.state == "null_weapon":
                self.record("null-weapon-clears", False)
                self.dummy_weapon = ue.new_object(ue.find_class("LyraWeaponInstance"))
                self.dummy_weapon.add_to_root()
                for host in (self.host, self.baseline):
                    host.call_function("OnWeaponChanged", None, self.dummy_weapon)
                self.phase("missing_instigator")
            elif self.state == "missing_instigator":
                self.record("test-owned-native-weapon-without-instigator", False)
                for host in (self.host, self.baseline):
                    host.call_function("OnWeaponChanged", None, self.weapon)
                self.phase("restored")
            elif self.state == "restored":
                self.record("real-native-weapon-restored")
                self.pickup("Rifle")
            elif self.state in ("rifle", "shotgun"):
                if self.host.CurrentInstance.get_path_name() == self.previous_weapon or not self.host.SpawnedWidgets:
                    return True
                kind = "Rifle" if self.state == "rifle" else "Shotgun"
                self.record("native-pickup-equip-" + kind)
                check(any(kind in widget.get_class().get_name() for widget in self.host.SpawnedWidgets), "native weapon selected wrong reticle")
                if kind == "Rifle":
                    self.pickup("Shotgun")
                else:
                    self.report["image"] = str(self.path.parent / "reticle-host.png")
                    ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                        'Shot SHOWUI -nosuffix filename="' + self.report["image"] + '"', self.controller)
                    self.phase("capture")
            elif self.state == "capture":
                if not Path(self.report["image"]).is_file():
                    return True
                self.health = self.host.CurrentHealthComponent
                self.deaths_before = hosts.snapshot()["death_callbacks"]
                pawn = self.controller.get_controlled_pawn()
                tag = GameplayTag(TagName="GameplayEvent.Death")
                payload = GameplayEventData(EventTag=tag, Instigator=pawn, Target=pawn)
                ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor", pawn, tag, payload)
                self.report["native_death_event_injected"] = True
                self.phase("death")
            elif self.state == "death":
                if not valid(self.health) or not self.health.call_function("IsDeadOrDying"):
                    return True
                check(int(self.host.VisWrapper.call_function("GetVisibility")) == 1, "production reticle wrapper did not collapse on native death")
                check(int(self.baseline.VisWrapper.call_function("GetVisibility")) == 1, "original BP did not collapse on native death")
                check(hosts.snapshot()["death_callbacks"] == self.deaths_before + 1, "duplicate/missing Python death callback")
                check(self.host._uep_reticle_host_scope is None, "death reattached the closed Python listener")
                self.report["native_death_visibility_and_exact_once_callback"] = True
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPReticleHostResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = ReticleHostValidation(result)
ticker = ue.add_ticker(validation.tick)
