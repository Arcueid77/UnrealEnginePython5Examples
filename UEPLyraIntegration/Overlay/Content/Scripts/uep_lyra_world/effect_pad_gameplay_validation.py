"""Opt-in physical overlap / native GAS differential on a real Lyra Pawn.

Test-owned pads and native Pawn teleports isolate collision from manual input.
Never call the overlap handlers, write attributes, or modify official assets.
The native bridge supplies an explicit nonlethal baseline through native GAS.
"""

from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue

from uep_runtime.subscriptions import SubscriptionScope
from uep_lyra_hud import state as hud_state, weapon_observer
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network_bots import isolate_bots
from uep_lyra_network_io import atomic_write
from .effect_pad_mixin import ability_system
from uep_lyra_hud.weapon_observer import valid


PAD = "/Game/Environments/Gameplay/BP_GameplayEffectPad.BP_GameplayEffectPad_C"
CHILD = "/Game/Environments/Gameplay/B_GameplayEffectPad_Child_Healing.B_GameplayEffectPad_Child_Healing_C"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def effect_count(asc, effect):
    return int(asc.call_function("GetGameplayEffectCount", effect, None, False))


class EffectPadGameplayValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.elapsed = 0.0
        self.state = "ready"
        self.deadline = 0.0
        self.index = 0
        self.actors = []
        self.events = []
        self.scope = SubscriptionScope()
        self.pawn = self.movement = self.cls = None
        self.original_location = None
        self.original_mode = None
        self.finished = False
        self.report = {"schema_version": 1, "status": "running", "cases": [],
                       "real_gas_verified": False, "physical_overlap_tested": False,
                       "network_acceptance": False, "full_acceptance": False,
                       "overlap_handlers_called_by_probe": False,
                       "attributes_written_by_probe": False, "manual_input_tested": False}

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
            if not (snapshot.bExperienceLoaded and snapshot.bHealthReady and snapshot.bAbilitySystemReady
                    and not snapshot.bDamageImmune and snapshot.Health > 0):
                continue
            check(str(snapshot.NetMode) == "Standalone", "single-process authority lane required")
            controller = statics.call_function("GetPlayerController", world, 0)
            pawn = controller.get_controlled_pawn()
            if not valid(pawn):
                continue
            self.world, self.bridge, self.pawn = world, bridge, pawn
            self.asc = ability_system(pawn)
            self.health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            self.movement = pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
            check(valid(self.asc) and valid(self.health) and valid(self.movement), "real Pawn GAS/movement unavailable")
            self.original_location = pawn.get_actor_location()
            self.original_mode = int(self.movement.MovementMode)
            self.movement.call_function("StopMovementImmediately")
            self.movement.call_function("DisableMovement")
            self.cls = ue.load_class(PAD)
            ue.register_declared_mixin(self.cls)
            cdo = self.cls.get_cdo()
            self.plan = [(cls, name, profile, effect) for cls in (self.cls, ue.load_class(CHILD)) for name, effect in
                         (("damage", cdo.GE_Damage), ("heal", cdo.GE_Heal))
                         for profile in ("BlueprintFallback", "Python")]
            self.report["pawn"] = pawn.get_path_name()
            self.report["asc"] = self.asc.get_path_name()
            self.report["net_mode"] = str(snapshot.NetMode)
            return True
        return False

    def health_value(self):
        return float(self.health.call_function("GetHealth"))

    def relocate(self, location):
        # SetActorLocation uses native UpdateOverlaps even without a sweep.
        check(self.pawn.set_actor_location(location), "native Pawn teleport rejected")

    def begin_case(self):
        cls, name, profile, effect = self.plan[self.index]
        check(effect_count(self.asc, effect) == 0, "baseline already owns pad effect")
        delta = 75.0 - self.health_value()
        command = self.bridge.call_function("ApplyAuthorityHealthDelta", "pad." + str(self.index), delta, False)
        check(command.bApplied and abs(float(command.HealthAfter) - 75.0) < 0.05,
              "native nonlethal baseline rejected")
        effect_cdo = effect.get_cdo()
        period = float(effect_cdo.Period.Value)
        duration = int(effect_cdo.DurationPolicy)
        check(duration != 0, "authored pad effect is instant; active-removal lane must be redesigned")
        self.dwell = max(period * 1.1, 0.2)
        # Far enough from the retained map's own world-interaction actors.
        self.center = ue.FVector(self.original_location.x + 4000.0 + self.index * 800.0,
                                 self.original_location.y, self.original_location.z + 300.0)
        transform = ue.FTransform()
        transform.translation = self.center
        statics = ue.find_class("GameplayStatics").get_cdo()
        self.pad = statics.call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform, 1, None)
        check(valid(self.pad), "deferred pad spawn failed")
        self.actors.append(self.pad)
        ue.set_mixin_profile(self.pad, profile)
        self.pad.set_property("GameplayEffectToApply", effect)
        statics.call_function("FinishSpawningActor", self.pad, transform)
        check(self.pad.get_class() == cls, "physical test changed BP class")
        self.effect, self.profile = effect, profile
        self.current = {"case": name, "profile": profile, "class": cls.get_name(),
                        "effect": effect.get_path_name(), "period": period, "duration_policy": duration,
                        "rounds": [], "health_before": self.health_value()}
        self.event_start = len(self.events)
        self.scope.bind_event(self.pad.Volume, "OnComponentBeginOverlap", self.on_begin)
        self.scope.bind_event(self.pad.Volume, "OnComponentEndOverlap", self.on_end)
        self.round_start = self.health_value()
        self.enter()

    def on_begin(self, component, actor, *unused):
        if actor == self.pawn:
            self.events.append({"type": "begin", "index": self.index, "health": self.health_value()})

    def on_end(self, component, actor, *unused):
        if actor == self.pawn:
            self.events.append({"type": "end", "index": self.index, "health": self.health_value()})

    def enter(self):
        self.relocate(self.pad.Volume.call_function("K2_GetComponentLocation"))
        self.state, self.deadline = "inside", self.elapsed + self.dwell

    def advance(self):
        if self.state == "ready":
            if self.ready():
                self.begin_case()
            return
        if self.state == "inside":
            check(self.health_value() > 0, "pad unexpectedly killed the test Pawn")
            if self.elapsed < self.deadline:
                return
            count = effect_count(self.asc, self.effect)
            check(count >= 1, "physical begin did not apply native active effect")
            self.inside_health = self.health_value()
            self.inside_count = count
            self.relocate(ue.FVector(self.center.x + 500.0, self.center.y, self.center.z))
            self.state, self.deadline = "outside", self.elapsed + self.dwell
            return
        if self.state == "outside":
            if self.elapsed < self.deadline:
                return
            check(effect_count(self.asc, self.effect) == 0, "physical end did not remove all source effects")
            check(abs(self.health_value() - self.inside_health) < 0.05, "effect kept executing after physical end")
            self.current["rounds"].append({"before": self.round_start, "inside": self.inside_health,
                                           "after": self.health_value(), "inside_count": self.inside_count,
                                           "after_count": 0})
            if len(self.current["rounds"]) == 1:
                self.round_start = self.health_value()
                self.enter()
                return
            seen = self.events[self.event_start:]
            check([event["type"] for event in seen] == ["begin", "end", "begin", "end"],
                  "collision callbacks replayed or missing: " + repr(seen))
            self.current["physical_events"] = seen
            if self.profile == "Python":
                check(self.pad._uep_effect_pad_constructions == 1, "Python constructor bypassed")
                check(self.pad._uep_effect_pad_begin_intents == self.pad._uep_effect_pad_end_intents == 2,
                      "Python overlap method bypassed or replayed")
                self.current["python_begin_intents"] = 2
                self.current["python_end_intents"] = 2
                baseline = self.report["cases"][-1]
                for bp, py in zip(baseline["rounds"], self.current["rounds"]):
                    check(abs((bp["inside"] - bp["before"]) - (py["inside"] - py["before"])) < 0.05,
                          "native Health delta differs between BP/Python: " + repr((bp, py)))
                    check(bp["inside_count"] == py["inside_count"], "native active count differs")
            self.scope.close()
            self.scope = SubscriptionScope()
            self.pad.actor_destroy()
            self.report["cases"].append(self.current)
            self.index += 1
            if self.index == len(self.plan):
                self.report.update(real_gas_verified=True, physical_overlap_tested=True, original_bp_compared=True)
                self.finish()
            else:
                self.begin_case()

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.scope.close()
            for actor in self.actors:
                if valid(actor):
                    actor.actor_destroy()
            if valid(self.pawn) and self.original_location is not None:
                self.relocate(self.original_location)
                self.movement.call_function("SetMovementMode", self.original_mode, 0)
            if self.cls is not None:
                check(ue.unregister_mixin(self.cls), "pad router restore failed")
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "passed", error=error,
                           actors_destroyed=len(self.actors), delegates_closed=self.scope.closed,
                           elapsed_seconds=time.monotonic() - self.started,
                           hud=hud_state.snapshot(), weapon_observer=weapon_observer.snapshot(),
                           gameplay_slice={"enabled": False}, shutdown=None)
        if not error:
            defer_until_shutdown(self.report, self.path)
        atomic_write(self.path, self.report)
        (ue.log_error if error else ue.log)("UEP_EFFECT_PAD_GAMEPLAY_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def tick(self, delta):
        try:
            self.elapsed += delta
            check(time.monotonic() - self.started < 180, "physical pad fixture timed out: " + self.state)
            self.advance()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPEffectPadGameplayResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = EffectPadGameplayValidation(result)
ticker = ue.add_ticker(validation.tick)
