"""Original placed Chair -> native target scan/TriggerInteraction/GAS -> UI pair.

The probe schedules native API intent, fixture position/movement/aim and two
test-owned UI panels. It never broadcasts a duration or replays a handler.
"""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_hud import ability_progress_mixin as progress
from .effect_pad_mixin import ability_system, valid

CHAIR = "/ShooterExplorer/Items/B_InteractableChair.B_InteractableChair_C"
SIT = "/ShooterExplorer/Interact/GA_Interaction_Sit.GA_Interaction_Sit_C"
PEERS = ("A", "B0")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def vector(value):
    return [float(getattr(value, key)) for key in ("x", "y", "z")]


def model(widget):
    material = widget.ProgressBorder.call_function("GetDynamicMaterial")
    return dict(duration=float(widget.Duration), start=float(widget.StartTime),
        visibility=int(widget.call_function("GetVisibility")), text=str(widget.ProgressText.call_function("GetText")),
        percent=float(material.call_function("K2_GetScalarParameterValue", "Percent")))


def same_models(left, right):
    return all(abs(left[key]-right[key]) < .00001 if key in ("start", "duration", "percent") else
               left[key] == right[key] for key in left)


class Producer:
    def __init__(self, path):
        self.path, self.root, self.started = Path(path), Path(path).parent, time.monotonic()
        self.peer = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPInteractionPeer="))
        self.report = dict(schema_version=1, status="running", error=None, peer=self.peer, cases=[], runtime_acceptance=False,
            native_interaction_producer_tested=False, original_world_restored=False,
            synthetic_duration_broadcast=False, python_handler_replayed=False, activation_handler_replayed=False,
            full_acceptance=False, packaged_runtime=False, hardware_input_tested=False,
            enhanced_input_pipeline_tested=False, replicated_duration_message_tested=False,
            test_owned_ui_pair=True, production_widget_reachability_tested=False,
            fixture_native_position_movement_and_aim=True)
        self.ready, self.finished, self.index, self.widgets, self.saved = False, False, -1, [], {}
        self.phase_started = self.started
        self.baseline_count = 0
        atexit.register(self.finalize)

    def write(self):
        atomic_write(self.path, self.report)

    def instances(self, asc, name):
        result = []
        for spec in asc.get_property("ActivatableAbilities").Items:
            if valid(spec.Ability) and spec.Ability.get_class().get_path_name() == name:
                result.extend(value for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value))
        return result

    def setup(self):
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3, 5) or "L_InteractionTestMap" not in world.get_name():
                continue
            chairs, = self.statics.call_function("GetAllActorsOfClass", world, ue.load_class(CHAIR))
            if not chairs:
                continue
            self.world, self.chair = world, chairs[0]
            if self.peer == "server":
                identities = {peer: read_json(self.root/(peer+"-ready.json")) for peer in PEERS}
                if not all(isinstance(row, dict) and "player_id" in row for row in identities.values()):
                    continue
                require(len({row["player_id"] for row in identities.values()}) == 2, "interaction peer IDs are not distinct")
                controllers, = self.statics.call_function("GetAllActorsOfClass", world, ue.find_class("LyraPlayerController"))
                owners = {}
                for controller in controllers:
                    if not valid(controller.PlayerState):
                        continue
                    player_id = int(controller.PlayerState.PlayerId)
                    for peer in PEERS:
                        if player_id == identities[peer]["player_id"]:
                            owners[peer] = controller
                if set(owners) != set(PEERS) or not all(valid(value.get_controlled_pawn()) and
                        valid(ability_system(value.get_controlled_pawn())) for value in owners.values()):
                    continue
                self.owners = owners
                for peer, controller in owners.items():
                    pawn = controller.get_controlled_pawn(); movement = pawn.CharacterMovement
                    self.saved[peer] = dict(pawn=pawn, location=pawn.get_actor_location(),
                        movement=movement, mode=int(movement.MovementMode), custom=int(movement.CustomMovementMode))
                self.report["original_chair_class"] = self.chair.get_class().get_path_name()
                self.ready = True
                return
            controller = self.statics.call_function("GetPlayerController", world, 0)
            pawn = controller.get_controlled_pawn() if valid(controller) else None
            asc = ability_system(pawn) if valid(pawn) else None
            if not valid(asc):
                continue
            interactors = self.instances(asc, "/ShooterExplorer/Input/Abilities/GA_Interact.GA_Interact_C")
            if not interactors:
                continue
            self.controller, self.pawn, self.asc, self.interactors = controller, pawn, asc, interactors
            self.original_aim = controller.call_function("GetControlRotation")
            cls = ue.load_class(progress.CLASS)
            self.baseline_count = progress.snapshot()["active_count"]
            self.candidate, self.baseline = controller.create_widget(cls), controller.create_widget(cls)
            self.widgets = [self.candidate, self.baseline]
            ue.set_mixin_profile(self.baseline, "BlueprintFallback")
            for index, widget in enumerate(self.widgets):
                widget.add_to_root(); widget.AddToViewport(500+index)
            self.baseline.call_function("SetRenderOpacity", 0.)
            require(ue.get_mixin_profile(self.candidate) == "Python", "interaction candidate did not retain default Python profile")
            self.report.update(original_interactor_instances=len(interactors), player_id=int(controller.PlayerState.PlayerId),
                pawn=pawn.get_path_name(), candidate=self.candidate.get_path_name(), baseline=self.baseline.get_path_name())
            atomic_write(self.root/(self.peer+"-ready.json"), {"ready": True, "player_id": self.report["player_id"]})
            self.ready = True
            return

    def server(self):
        if self.index == 2:
            if all((self.root/(peer+"-exited.json")).is_file() for peer in PEERS):
                self.report["server_waited_for_client_process_exit"] = True
                self.finish()
            return
        if self.index == -1:
            if not all((self.root/(peer+"-ready.json")).is_file() for peer in PEERS):
                return
            self.index = 0
            self.prepare()
            return
        target = PEERS[self.index]
        ack = read_json(self.root/(target+"-case.json"))
        if not isinstance(ack, dict) or ack.get("case_index") != self.index:
            return
        require(ack.get("passed") is True, "original interaction owner case failed")
        self.report["cases"].append(ack)
        if self.index == 0:
            self.index = 1; self.prepare()
            return
        self.restore()
        self.report.update(original_world_restored=True, native_interaction_producer_tested=True)
        atomic_write(self.root/"release.json", {"ready": True})
        self.index = 2
        self.phase_started = time.monotonic()

    def prepare(self):
        target = PEERS[self.index]
        origin = self.chair.get_actor_location()
        for peer, saved in self.saved.items():
            saved["movement"].call_function("SetMovementMode", 0, 0)
            saved["pawn"].set_actor_location(ue.FVector(origin.x-150., origin.y+(-90. if peer == target else 350.), origin.z+95.))
        atomic_write(self.root/"phase.json", dict(case_index=self.index, target=target, chair=self.chair.get_path_name()))
        self.phase_started = time.monotonic()

    def client(self):
        packet = read_json(self.root/"phase.json")
        if isinstance(packet, dict):
            if packet["case_index"] != self.index:
                self.index, self.phase_started, self.requested, self.observed = packet["case_index"], time.monotonic(), False, None
                self.before_messages = self.candidate._uep_progress_messages
            if packet["target"] == self.peer:
                self.chair = ue.find_object(packet["chair"])
                require(valid(self.chair) and self.chair.get_class().get_path_name() == CHAIR,
                        "client did not resolve exact original level Chair")
                # The generic positional API includes out-param slots. With
                # only the first input, Origin/BoxExtent are allocated natively
                # and the final optional include-children input stays false.
                origin, extent = self.chair.call_function("GetActorBounds", True)
                camera = self.controller.PlayerCameraManager.call_function("GetCameraLocation")
                rotation = ue.find_class("KismetMathLibrary").get_cdo().call_function("FindLookAtRotation", camera, origin)
                self.controller.call_function("SetControlRotation", rotation)
                if not self.requested and time.monotonic()-self.phase_started > .75:
                    selected = [ability for ability in self.interactors if any(valid(option.InteractionAbilityToGrant) and
                        option.InteractionAbilityToGrant.get_path_name() == SIT for option in ability.get_property("CurrentOptions"))]
                    if selected:
                        self.requested = True
                        self.selected = selected[0].get_path_name()
                        self.selected_option_count = len(selected[0].get_property("CurrentOptions"))
                        self.before_ticks = self.candidate._uep_progress_ticks
                        selected[0].call_function("TriggerInteraction")
                if self.requested:
                    delivered = self.candidate._uep_progress_messages-self.before_messages
                    if delivered:
                        require(delivered == 1, "single native interactor delivered duplicate duration")
                        actual, original = model(self.candidate), model(self.baseline)
                        require(same_models(actual, original), "native interaction duration BP/Python presentation differs")
                        require(abs(actual["duration"]-.5) < .00001, "original Sit duration changed")
                        if self.observed is None:
                            self.observed = dict(python=actual, blueprint=original,
                                native_sit_instances=len(self.instances(self.asc, SIT)))
                        if actual["visibility"] == 1 and self.candidate._uep_progress_ticks > self.before_ticks+2:
                            ack = dict(case_index=self.index, target=self.peer, passed=True, native_api="TriggerInteraction",
                                original_interactor=self.selected, original_interactor_count=len(self.interactors),
                                original_native_options=self.selected_option_count, original_sit_class=SIT,
                                native_duration_deliveries=delivered, automatic_ticks=self.candidate._uep_progress_ticks-self.before_ticks,
                                first_observed=self.observed, final_python=actual, final_blueprint=original,
                                same_class=self.candidate.get_class() == self.baseline.get_class())
                            if not (self.root/(self.peer+"-case.json")).is_file():
                                self.report["cases"].append(ack)
                                self.report["native_interaction_producer_tested"] = True
                                atomic_write(self.root/(self.peer+"-case.json"), ack)
            elif self.candidate._uep_progress_messages != self.before_messages:
                raise RuntimeError("another process interaction delivered owner duration locally")
        if (self.root/"release.json").is_file():
            self.controller.call_function("SetControlRotation", self.original_aim)
            self.report["original_world_restored"] = True
            self.finish()

    def restore(self):
        for saved in self.saved.values():
            saved["pawn"].set_actor_location(saved["location"])
            saved["movement"].call_function("SetMovementMode", saved["mode"], saved["custom"])
            require(vector(saved["pawn"].get_actor_location()) == vector(saved["location"]), "interaction fixture position restore failed")

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            if error and self.peer == "server": self.restore()
            for widget in self.widgets:
                widget.RemoveFromParent(); widget.remove_from_root()
            self.widgets = []
            self.candidate = self.baseline = None
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write()
        (ue.log_error if error else ue.log)("UEP_INTERACTION_PRODUCER_READY" if not error else error)
        ue.request_exit()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 230., "interaction producer total timeout")
            require(time.monotonic()-self.phase_started < 100., "interaction native target/message phase timeout")
            if not self.ready: self.setup()
            elif self.peer == "server": self.server()
            else: self.client()
            if not self.finished:
                atomic_write(self.root/(self.peer+"-status.json"), dict(ready=self.ready, case_index=self.index,
                    requested=getattr(self, "requested", False),
                    options=[len(value.get_property("CurrentOptions")) for value in getattr(self, "interactors", []) if valid(value)],
                    pawn_location=vector(self.pawn.get_actor_location()) if self.peer != "server" and self.ready and valid(self.pawn) else None,
                    messages=self.candidate._uep_progress_messages if self.widgets else None))
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc()); return False

    def finalize(self):
        self.report["shutdown"] = progress.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                require(len(self.report["cases"]) == (2 if self.peer == "server" else 1), "native interaction cases incomplete")
                require(self.report["original_world_restored"] and self.report["native_interaction_producer_tested"], "native interaction proof incomplete")
                require(self.report["shutdown"]["active_count"] == 0 and not self.report["shutdown"]["errors"], "interaction progress listener leaked")
                self.report["status"] = "passed"
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_INTERACTION_PRODUCER_"+self.report["status"].upper())


prefix = "-UEPInteractionInspectionResult="
producer = Producer(next(value[len(prefix):] for value in sys.argv if value.startswith(prefix)))
ticker = ue.add_ticker(producer.tick)
