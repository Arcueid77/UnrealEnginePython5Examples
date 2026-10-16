"""Read original prototype world/ASC state without driving an interaction."""
import atexit
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from .effect_pad_mixin import ability_system, valid
from uep_lyra_network_io import atomic_write, read_json


class Inspection:
    def __init__(self, result):
        self.path, self.started, self.finished = Path(result), time.monotonic(), False
        self.peer = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPInteractionPeer=")), None)
        self.captured = False
        self.report = dict(schema_version=1, status="running", error=None, runtime_acceptance=False,
            native_interaction_producer_tested=False, gameplay_state_written=False, native_input_injected=False,
            ability_activated_by_probe=False, blueprints_compiled_or_saved=False)
        atexit.register(self.finalize)

    def write(self):
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def tick(self, delta):
        if self.finished:
            return False
        try:
            if time.monotonic()-self.started > 160.:
                raise RuntimeError("original interaction map readiness timeout")
            if self.captured:
                if self.peer == "server" and all((self.path.parent/(peer+"-ready.json")).is_file() for peer in ("A", "B0")):
                    atomic_write(self.path.parent/"release.json", {"ready": True})
                if (self.path.parent/"release.json").is_file():
                    self.finish()
                    return False
                return True
            statics = ue.find_class("GameplayStatics").get_cdo()
            for world in ue.all_worlds():
                if world.get_world_type() not in (1, 3, 5) or "L_InteractionTestMap" not in world.get_name():
                    continue
                controller = statics.call_function("GetPlayerController", world, 0)
                pawn = controller.get_controlled_pawn() if valid(controller) else None
                asc = ability_system(pawn) if valid(pawn) else None
                if not valid(asc):
                    continue
                abilities = []
                for spec in asc.get_property("ActivatableAbilities").Items:
                    if valid(spec.Ability):
                        instances = list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances)
                        abilities.append(dict(ability=spec.Ability.get_class().get_path_name(),
                            input_tags=[str(tag.TagName) for tag in spec.DynamicAbilityTags.GameplayTags],
                            instances=[dict(path=item.get_path_name(), active=bool(item.get_property("bIsActive")))
                                       for item in instances if valid(item)],
                            option_counts=[len(item.get_property("CurrentOptions")) for item in instances if valid(item) and
                                           spec.Ability.get_class().get_name() == "GA_Interact_C"]))
                if not any(row["ability"].endswith("/GA_Interact.GA_Interact_C") for row in abilities):
                    continue
                actors = []
                for kind in ("Chair", "Rock"):
                    cls = ue.load_class("/ShooterExplorer/Items/B_Interactable"+kind+".B_Interactable"+kind+"_C")
                    found, = statics.call_function("GetAllActorsOfClass", world, cls)
                    for actor in found:
                        location = actor.get_actor_location()
                        actors.append(dict(kind=kind, path=actor.get_path_name(), original_class=cls.get_path_name(),
                            actual_class=actor.get_class().get_path_name(),
                            replicates=bool(actor.bReplicates), local_role=int(actor.call_function("GetLocalRole")),
                            location=[float(getattr(location, key)) for key in ("x", "y", "z")]))
                if not actors:
                    continue
                self.report.update(status="captured", peer=self.peer, world=world.get_path_name(),
                    pawn=pawn.get_path_name(), pawn_class=pawn.get_class().get_path_name(),
                    asc=asc.get_path_name(), abilities=abilities, interactables=actors,
                    elapsed_seconds=time.monotonic()-self.started)
                self.captured = True
                self.write()
                ue.log("UEP_INTERACTION_WORLD_INSPECTION_READY")
                if self.peer is not None:
                    atomic_write(self.path.parent/(self.peer+"-ready.json"), {"ready": True})
                    return True
                self.finish()
                return False
            return True
        except Exception:
            self.report.update(status="failed", error=traceback.format_exc())
            self.finished = True
            self.write()
            ue.log_error(self.report["error"])
            ue.request_exit()
            return False

    def finish(self):
        self.finished = True
        self.report["status"] = "awaiting_shutdown"
        self.write()
        ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)(
            "UEP_INTERACTION_WORLD_INSPECTION_"+self.report["status"].upper())


prefix = "-UEPInteractionInspectionResult="
inspection = Inspection(next(value[len(prefix):] for value in sys.argv if value.startswith(prefix)))
ticker = ue.add_ticker(inspection.tick)
