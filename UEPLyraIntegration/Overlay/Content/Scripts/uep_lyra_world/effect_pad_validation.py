"""Isolated Actor BP/Python construction and no-ASC overlap comparison.

Real GAS and physical overlap are separate gates. Deferred spawning selects
the baseline before construction; originals/reference assets are never edited.
"""

import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import HitResult

from uep_lyra_hud.weapon_observer import valid
from .effect_pad_mixin import BEGIN_EVENT, END_EVENT


ASSETS = (
    "/Game/Environments/Gameplay/BP_GameplayEffectPad.BP_GameplayEffectPad_C",
    "/Game/Environments/Gameplay/B_GameplayEffectPad_Child_Healing.B_GameplayEffectPad_Child_Healing_C",
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def actor_values(actor):
    material = actor.Pad.call_function("GetMaterial", 0)
    return {"text": str(actor.Text.Text), "world_size": float(actor.Text.WorldSize),
            "material_parent": material.Parent.get_path_name() if valid(material) and hasattr(material, "Parent") else None}


class EffectPadValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.actors = []
        self.classes = []
        self.report = {"schema_version": 1, "status": "running", "cases": [],
                       "real_gas_verified": False, "physical_overlap_tested": False,
                       "full_acceptance": False}
        self.report["construction_route"] = "explicit Parent BP construction -> virtual UEPConstructEffectPad -> single parent router"
        self.report["related_child_router_used"] = False

    def spawn(self, world, cls, profile, effect, index):
        transform = ue.FTransform()
        transform.translation = ue.FVector(10000.0 + index * 500.0, 0.0, 100.0)
        statics = ue.find_class("GameplayStatics").get_cdo()
        actor = statics.call_function("BeginDeferredActorSpawnFromClass", world, cls, transform, 1, None)
        check(valid(actor), "native deferred spawn failed")
        self.actors.append(actor)
        ue.set_mixin_profile(actor, profile)
        actor.set_property("GameplayEffectToApply", effect)
        statics.call_function("FinishSpawningActor", actor, transform)
        return actor

    def validate(self, world, controller):
        ue.unregister_all_mixins()
        for path in ASSETS:
            cls = ue.load_class(path)
            if path == ASSETS[0]:
                ue.register_declared_mixin(cls)
            self.classes.append(cls)
        for cls in self.classes:
            cdo = cls.get_cdo()
            cases = (("damage", cdo.GE_Damage), ("heal", cdo.GE_Heal),
                     ("special", ue.find_class("GameplayEffect")), ("invalid", None))
            for name, effect in cases:
                baseline = self.spawn(world, cls, "BlueprintFallback", effect, len(self.actors))
                candidate = self.spawn(world, cls, "Python", effect, len(self.actors))
                original, actual = actor_values(baseline), actor_values(candidate)
                check(original == actual, "construction differs: " + repr((name, original, actual)))
                check(candidate.get_class() == baseline.get_class() == cls, "actor class changed")
                expected_calls = 0 if effect is None else 1
                check(candidate._uep_effect_pad_constructions == expected_calls,
                      "Python construction was bypassed/replayed: " + cls.get_name())
                pawn = controller.get_controlled_pawn()
                for actor in (baseline, candidate):
                    actor.call_function(BEGIN_EVENT, actor.Volume, pawn, None, 0, False, HitResult())
                    actor.call_function(END_EVENT, actor.Volume, pawn, None, 0)
                check(candidate._uep_effect_pad_begin_intents == candidate._uep_effect_pad_end_intents == 0,
                      "actor without native ASC applied an effect")
                self.report["cases"].append({"class": cls.get_name(), "case": name, "bp": original,
                                              "python": actual, "python_construction_calls": expected_calls,
                                              "same_class": True, "no_asc_noop": True})

    def finish(self, error=None):
        for actor in self.actors:
            if valid(actor):
                actor.actor_destroy()
        ue.unregister_all_mixins()
        self.report["status"], self.report["error"] = ("failed" if error else "passed"), error
        self.report["actors_destroyed"] = len(self.actors)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_EFFECT_PAD_DIFFERENTIAL_" + self.report["status"].upper())
        ue.request_exit()

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 90, "effect-pad fixture timed out")
            for world in ue.all_worlds():
                if world.get_world_type() not in (1, 3, 5):
                    continue
                check("/Engine/Maps/Entry" in world.get_path_name(), "isolated fixture requires Entry")
                controller = ue.find_class("GameplayStatics").get_cdo().call_function("GetPlayerController", world, 0)
                if controller is None or controller.get_controlled_pawn() is None:
                    continue
                self.validate(world, controller)
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPEffectPadResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = EffectPadValidation(result)
ticker = ue.add_ticker(validation.tick)
