"""Actual deferred native components/BeginPlay/parts/cleanup, retained BP types."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from . import cosmetics_mixin as policy
from .cosmetic_state import capture, path
from .cosmetic_contract import PLAN, MANNY, QUINN, require, validate


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase, self.index = Path(result), time.monotonic(), "ready", 0
        self.finished, self.component, self.sides = False, None, []
        self.report = dict(schema_version=1, status="running", error=None, cases=[], random_trials=[], original_player_restored=False)
        self.report.update({key: False for key in ("full_acceptance", "network_acceptance", "packaged_runtime", "animation_assets_modified",
            "part_actors_spawned_by_python", "part_arrays_written", "beginplay_handler_replayed", "rng_seed_or_result_written")})
        self.statics = ue.find_class("GameplayStatics").get_cdo()

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bHeroInputReady and snap.bHealthReady and snap.Health > 0 and not snap.bDamageImmune): continue
            self.world, self.bridge = world, bridge
            self.controller = self.statics.call_function("GetPlayerController", world, 0)
            self.pawn = self.controller.get_controlled_pawn()
            require(int(self.pawn.call_function("GetLocalRole")) == 3, "native cosmetic fixture requires authority")
            self.original = capture(self.pawn)
            if not self.original: continue
            self.begin(); return

    def begin(self):
        self.kind = "selection" if self.index < len(PLAN)*2 else "random"
        self.name = PLAN[self.index//2][0] if self.kind == "selection" else "native-random"
        self.profile = ("BlueprintFallback", "Python")[self.index % 2]
        self.cls = ue.load_class(policy.SELECTION if self.kind == "selection" else policy.RANDOM)
        self.before_parts, self.before_stats = capture(self.pawn), policy.snapshot()
        self.transform = ue.FTransform()
        self.component = self.controller.call_function("AddComponentByClass", self.cls, True, self.transform, True)
        require(valid(self.component), "native deferred cosmetic component not created")
        if self.kind == "selection":
            self.component.set_property("AvailableCharacterParts", [ue.load_class(value) for value in PLAN[self.index//2][1]])
        if self.profile == "BlueprintFallback": ue.set_mixin_profile(self.component, self.profile)
        actors, = self.statics.call_function("GetAllActorsOfClass", self.component, ue.find_class("LyraCharacter"))
        self.actor_count = len(actors)
        self.controller.call_function("FinishAddComponent", self.component, True, self.transform)
        require(str(ue.get_mixin_profile(self.component)) == self.profile, "native component default/explicit Profile differs")
        self.enter("added")

    def added(self):
        if time.monotonic()-self.phase_started < .15: return
        parts = capture(self.pawn)
        handles = {row["handle"] for row in self.before_parts}
        added = [row for row in parts if row["handle"] not in handles]
        require(len(added) == 1 and len(parts) == len(self.before_parts)+1, "native BeginPlay did not add exactly one real part")
        part = added[0]
        if getattr(self, "require_actors", True): require(part["actor"] is not None, "native child actor did not spawn")
        self.row = dict(kind=self.kind, profile=self.profile, chosen_class=part["cls"], native_part=part,
            native_actor_count=self.actor_count, pawn=self.pawn.get_path_name(), native_type_preserved=self.component.get_class() == self.cls,
            native_owner_preserved=self.component.call_function("GetOwner") == self.controller,
            native_beginplay_observed=True, native_cleanup_restored_original_ids=False, profile_roundtrip_preserved_part=False)
        ue.set_mixin_profile(self.component, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
        ue.set_mixin_profile(self.component, self.profile)
        self.row["profile_roundtrip_preserved_part"] = capture(self.pawn) == parts
        stats = policy.snapshot()
        self.row["counters"] = {key: value-self.before_stats[key] for key, value in stats.items() if type(value) is int}
        self.part_presented()

    def part_presented(self):
        self.component.call_function("K2_DestroyComponent", self.controller)
        self.component = None
        self.enter("removed")

    def removed(self):
        current = capture(self.pawn)
        if current != self.before_parts:
            require(time.monotonic()-self.phase_started < 3., "native cosmetic EndPlay did not restore original part/actor identities")
            return
        self.row["native_cleanup_restored_original_ids"] = True
        self.record_trial(self.row)
        if self.kind == "selection":
            self.sides.append(copy.deepcopy(self.row))
            if self.index % 2:
                self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1])); self.sides = []
                ue.log("UEP_COSMETIC_CASE_OBSERVED "+self.name)
        else: self.report["random_trials"].append(copy.deepcopy(self.row))
        self.index += 1
        random = self.report["random_trials"]
        enough = len(random) >= 16 and all({row["chosen_class"] for row in random if row["profile"] == profile} == {MANNY, QUINN}
            for profile in ("BlueprintFallback", "Python"))
        if enough or len(random) == 64:
            self.report["original_player_restored"] = current == self.original
            self.finish()
        else: self.begin()

    def record_trial(self, row): pass

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 180., "native cosmetic total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "added": self.added()
            else: self.removed()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if valid(self.component): self.component.call_function("K2_DestroyComponent", self.controller)
            if hasattr(self, "pawn") and hasattr(self, "original"):
                self.report["original_player_restored"] = capture(self.pawn) == self.original
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_COSMETIC_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_COSMETIC_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPCosmeticResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCosmeticResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
