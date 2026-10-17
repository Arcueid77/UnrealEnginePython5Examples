"""Native ASC activation on the real player and bot; no activation/RPC replay."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from .auto_respawn_helpers_validation import Validation as Ready, instances, specs
from .dash_selector_mixin import CLASS, evidence as selector_evidence
from .dash_rpc_input_mixin import evidence as rpc_evidence, vector, path
from .dash_rpc_input_network_validation import configuration, delta, distance, payload, task_state
from .dash_local_direction_mixin import evidence
from .dash_local_direction_contract import STANDALONE_TRIALS, require, standalone


def rotation(value): return [float(value.roll), float(value.pitch), float(value.yaw)]
def counters(ability):
    return dict(local=copy.deepcopy(evidence(ability)), selector=copy.deepcopy(selector_evidence(ability)), rpc=copy.deepcopy(rpc_evidence(ability)))


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.require_auto_active = False; self.cleaned = False
        self.report = dict(schema_version=1, status="running", error=None, cases=[],
            full_acceptance=False, network_acceptance=False, packaged_runtime=False, physical_input_tested=False,
            enhanced_input_tested=False, whole_dash_activation_migrated=False, dash_task_business_migrated=False,
            movement_parity_certified=False, activation_event_replayed=False, rpc_receiver_replayed=False,
            ability_granted_by_fixture=False, ability_direction_montage_written_by_fixture=False,
            health_written_by_fixture=False, raw_velocity_written_by_fixture=False, gameplay_state_delivered_by_files=False,
            request_entry="ASC.TryActivateAbilityByClass", movement_intent_entry="Pawn.AddMovementInput",
            fixture_control_rotation_entry="Controller.SetControlRotation", fixture_pose_entry="Actor.K2_TeleportTo")

    def context(self, pawn, controller):
        asc = ability_system(pawn)
        if not valid(asc): return None
        values = instances(asc, self.cls)
        health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if len(values) != 1 or not valid(health) or health.call_function("IsDeadOrDying") or health.call_function("GetHealth") <= 0: return None
        return dict(pawn=pawn, controller=controller, asc=asc, ability=values[0], health=health,
            profile=str(ue.get_mixin_profile(values[0])), config=configuration(values[0]), specs=specs(asc),
            location=pawn.get_actor_location(), rotation=pawn.get_actor_rotation(), control=controller.call_function("GetControlRotation"),
            initial_health=float(health.call_function("GetHealth")))

    def begin(self):
        self.cls = ue.load_class(CLASS)
        bots, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerBotController"))
        bot = next((value for value in bots if valid(value.get_controlled_pawn()) and self.context(value.get_controlled_pawn(), value)), None)
        if bot is None: return
        player, ai = self.context(self.pawn, self.controller), self.context(bot.get_controlled_pawn(), bot)
        require(player is not None and ai is not None, "native granted player/AI Dash instances required")
        self.actors = dict(player=player, ai=ai)
        bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world)
        self.report.update(native_net_mode=str(bridge.call_function("CaptureSnapshot").NetMode), actual_ability_class=CLASS,
            actual_granted_primary_instances=True, player=path(self.pawn), ai=path(ai["pawn"]), ai_controller=path(bot))
        require(self.report["native_net_mode"] == "Standalone", "direction matrix requires actual native Standalone")
        self.enter("start")

    def start(self):
        name, profile = STANDALONE_TRIALS[self.index]
        self.current = self.actors["ai" if name == "ai-navigation" else "player"]
        actor = self.current; ability, pawn = actor["ability"], actor["pawn"]
        if ability.get_property("bIsActive") or ability.call_function("GetCooldownTimeRemaining") > 0 or int(pawn.CharacterMovement.MovementMode) != 1: return
        moved = bool(pawn.call_function("K2_TeleportTo", actor["location"], actor["rotation"]))
        require(moved, "collision-checked native fixture pose reset refused")
        pitch = 20. if name == "camera-pitch" else 0.
        actor["controller"].call_function("SetControlRotation", ue.FRotator(0., pitch, actor["rotation"].yaw))
        ue.set_mixin_profile(ability, profile)
        self.before = counters(ability); self.fields_before = payload(ability)
        self.row = dict(index=self.index, name=name, profile=profile, actor=path(pawn), controller=path(actor["controller"]),
            native_role=int(pawn.call_function("GetLocalRole")), native_pose_reset=moved, control_pitch_fixture=pitch,
            native_active_observed=False, native_root_motion_task_observed=False, native_montage_task_observed=False,
            max_motion_distance=0., max_native_speed=0., cooldown_repeat_rejected=None)
        self.enter("settle")

    def input_snapshot(self):
        actor = self.current; pawn, ability = actor["pawn"], actor["ability"]
        ai_controller = ue.find_class("AIBlueprintHelperLibrary").get_cdo().call_function("GetAIController", pawn)
        ai = valid(ai_controller); point = pawn.get_actor_location(); projected = succeeded = None
        math = ue.find_class("KismetMathLibrary").get_cdo()
        if ai:
            # Independent, read-only native query. The actual BP/Python activation queries again.
            result = ue.find_class("NavigationSystemV1").get_cdo().call_function("K2_ProjectPointToNavigation",
                WorldContextObject=ability, Point=point, NavData=None, FilterClass=None, QueryExtent=ue.FVector(500., 500., 500.))
            projected, = [value for value in result if type(value) is not bool]
            succeeded, = [value for value in result if type(value) is bool]
            flat = math.call_function("Multiply_VectorVector", math.call_function("Subtract_VectorVector", projected, point), ue.FVector(1., 1., 0.))
            last = movement = math.call_function("Normal", flat, .0001)
        else:
            last = pawn.call_function("GetLastMovementInputVector")
            camera = pawn.get_property("CameraComponent").call_function("GetForwardVector")
            movement = math.call_function("Multiply_VectorVector", camera, ue.FVector(1., 1., 1.2))
        return dict(ai=ai, facing=vector(pawn.call_function("GetActorForwardVector")), last_input=vector(last), movement=vector(movement),
            raw_last_input=vector(pawn.call_function("GetLastMovementInputVector")), point=vector(point),
            projected=vector(projected) if projected is not None else None, projection_succeeded=succeeded,
            control_rotation=rotation(actor["controller"].call_function("GetControlRotation")))

    def intent(self):
        actor = self.current; pawn, ability, asc = actor["pawn"], actor["ability"], actor["asc"]
        name = self.row["name"]
        if name in ("forward", "left", "camera-pitch"):
            direction = pawn.call_function("GetActorRightVector" if name == "left" else "GetActorForwardVector")
            pawn.call_function("AddMovementInput", direction, -1. if name == "left" else 1., False)
        if self.game_time()-self.intent_started < .2: return
        self.row["input"] = self.input_snapshot(); self.motion_start = vector(pawn.get_actor_location())
        self.row["native_request_accepted"] = bool(asc.call_function("TryActivateAbilityByClass", self.cls, False))
        require(self.row["native_request_accepted"], "native standalone Dash request rejected")
        self.row["chosen"] = payload(ability)
        self.row["zero_direction"] = all(abs(value) <= .0001 for value in self.row["chosen"]["direction"])
        self.row["immediate_active"] = bool(ability.get_property("bIsActive"))
        if not self.row["zero_direction"]:
            self.row["cooldown_repeat_rejected"] = asc.call_function("TryActivateAbilityByClass", self.cls, False) is False
        self.sample(); self.enter("observe")

    def sample(self):
        actor = self.current; ability, pawn = actor["ability"], actor["pawn"]
        tasks = task_state(ability)
        self.row["native_active_observed"] |= bool(ability.get_property("bIsActive"))
        self.row["native_root_motion_task_observed"] |= tasks["root"]
        self.row["native_montage_task_observed"] |= tasks["montage"]
        self.row["max_motion_distance"] = max(self.row["max_motion_distance"], distance(vector(pawn.get_actor_location()), self.motion_start))
        self.row["max_native_speed"] = max(self.row["max_native_speed"], distance(vector(pawn.call_function("GetVelocity")), [0., 0., 0.]))

    def observe(self):
        require(time.monotonic()-self.phase_started < 16., "native standalone Dash task/end/landing timeout")
        self.sample(); actor = self.current; ability = actor["ability"]
        if ability.get_property("bIsActive") or ability.call_function("GetCooldownTimeRemaining") > 0 or int(actor["pawn"].CharacterMovement.MovementMode) != 1: return
        self.quiet_before, self.quiet_ticks = counters(ability), 0; self.enter("quiet")

    def quiet(self):
        actor = self.current; ability = actor["ability"]
        require(counters(ability) == self.quiet_before, "late local direction/selector/RPC dispatch")
        self.quiet_ticks += 1
        if self.quiet_ticks < 20: return
        self.row.update(local_direction=dict(counters=delta(evidence(ability), self.before["local"]), before=self.fields_before,
                stored=payload(ability), last=copy.deepcopy(evidence(ability)["last"]) if self.row["profile"] == "Python" else None),
            selector_counters=delta(selector_evidence(ability), self.before["selector"]), rpc_counters=delta(rpc_evidence(ability), self.before["rpc"]),
            native_ability_ended=not bool(ability.get_property("bIsActive")), native_tasks_after=task_state(ability)["count"],
            quiet_ticks=self.quiet_ticks, specs_unchanged=specs(actor["asc"]) == actor["specs"],
            native_configuration_unchanged=configuration(ability) == actor["config"], health_unchanged=float(actor["health"].call_function("GetHealth")) == actor["initial_health"])
        self.report["cases"].append(copy.deepcopy(self.row))
        ue.log("UEP_DASH_LOCAL_DIRECTION_CASE_OBSERVED "+self.row["name"]+"/"+self.row["profile"])
        self.index += 1
        if self.index == len(STANDALONE_TRIALS): self.finish()
        else: self.enter("start")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300., "native standalone direction timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "start": self.start()
            elif self.phase == "settle" and time.monotonic()-self.phase_started >= .7:
                self.intent_started = self.game_time(); self.enter("intent")
            elif self.phase == "intent": self.intent()
            elif self.phase == "observe": self.observe()
            elif self.phase == "quiet": self.quiet()
            self.report["current_phase"] = self.phase; self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def cleanup(self):
        if self.cleaned: return
        restored = []
        for actor in getattr(self, "actors", {}).values():
            ability = actor["ability"]; ue.set_mixin_profile(ability, actor["profile"])
            actor["controller"].call_function("SetControlRotation", actor["control"])
            moved = bool(actor["pawn"].call_function("K2_TeleportTo", actor["location"], actor["rotation"]))
            restored.append(dict(profile=str(ue.get_mixin_profile(ability)) == actor["profile"],
                specs=specs(actor["asc"]) == actor["specs"], configuration=configuration(ability) == actor["config"], pose_reset=moved,
                control_rotation=rotation(actor["controller"].call_function("GetControlRotation")) == rotation(actor["control"])))
        self.report["restoration"] = restored; self.cleaned = True

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_DASH_LOCAL_DIRECTION_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; standalone(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DASH_LOCAL_DIRECTION_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDashLocalDirectionResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
