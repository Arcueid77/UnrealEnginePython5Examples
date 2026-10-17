"""Real C++ Add/RemoveCharacterPart -> bound BP/Python receiver, no replay."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from .inventory_clear_mixin import inventory_state
from .team_cosmetics_validation import DeviceObserver, ActorState, visual
from .outline_validation import path, gc
from . import parts_changed_mixin as policy, team_cosmetics_mixin as team_policy
from .parts_changed_contract import CLASS, TEMP_CLASS, PLAN, require, validate
from .parts_changed_observation import component, parts, part_actors, query, delta, DelegateObserver


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result)
        self.fixture_actor = self.player_state = self.observer = self.delegates = None; self.owned_handles = []
        self.report.update(callback_replayed=False, component_delegate_broadcast_by_fixture=False, all_parts_removed_by_fixture=False,
            parts_properties_written=False, hardware_output_tested=False, pixels_verified=False, full_acceptance=False, whole_character_migrated=False,
            original_player_visual_camera_profile_cdo_inventory_restored=False, owned_unassigned_actor_destroyed=False)

    def begin(self):
        self.report["natural_startup_python_dispatch"] = copy.deepcopy(policy.evidence(self.pawn))
        self.inventory_before = inventory_state(self.controller); self.cdo = self.pawn.get_class().get_cdo()
        self.cdo_profile = str(ue.get_mixin_profile(self.cdo)); self.player_state = ActorState(self.pawn)
        self.fixture_actor = self.world.actor_spawn(ue.load_class(CLASS), ue.FVector(200000., 200000., 2000.))
        self.fixture_actor.call_function("SetReplicates", False); self.fixture_profile = str(ue.get_mixin_profile(self.fixture_actor))
        self.observer = DeviceObserver(); self.report["retained_character_class"] = self.pawn.get_class().get_path_name()
        self.delegates = DelegateObserver((self.pawn, self.fixture_actor))
        self.prepare()

    def prepare(self):
        name, initial, target, switch = PLAN[self.index]
        self.actor = self.pawn if target == "owner" else self.fixture_actor
        self.initial, self.switch, self.operation = initial, switch, 0
        self.original_parts = parts(self.actor); self.original_actors = [path(value) for value in part_actors(self.actor)]
        self.spawned = []
        user = self.actor.call_function("GetPlatformUserId")
        self.case = dict(name=name, initial_profile=initial, target=target, switch=switch, original_parts=copy.deepcopy(self.original_parts),
            native_authority=bool(self.actor.call_function("HasAuthority")), native_team_query=query(self.actor),
            platform_user_valid=bool(ue.find_class("InputDeviceLibrary").get_cdo().call_function("IsValidPlatformId", user)), operations=[])
        self.enter("operation")

    def operate(self):
        profile = ("Python" if self.initial == "BlueprintFallback" else "BlueprintFallback") if self.switch and self.operation else self.initial
        ue.set_mixin_profile(self.actor, profile)
        before = copy.deepcopy(policy.evidence(self.actor)); team_before = copy.deepcopy(team_policy.evidence(self.actor))
        raw_before = self.delegates.count(self.actor)
        marker = self.observer.marker()
        if self.operation == 0:
            self.handle = component(self.actor).call_function("AddCharacterPart", LyraCharacterPart(PartClass=ue.find_class("Actor"))).clone()
            self.owned_handles.append((self.actor, self.handle))
        else: component(self.actor).call_function("RemoveCharacterPart", self.handle)
        self.properties = self.observer.collect(marker)
        current = policy.evidence(self.actor); current_actors = part_actors(self.actor)
        temporary = [value for value in current_actors if value.get_class().get_path_name() == TEMP_CLASS and path(value) not in self.original_actors]
        self.spawned.extend(temporary)
        counters = delta(current, before, "last_query")
        self.row = dict(operation=("add", "remove", "remove-again")[self.operation], profile=profile, native_operation_called=True,
            native_callback_count=self.delegates.count(self.actor)-raw_before,
            native_delegate_payload_matches=all(value["component_matches"] and value["owner_matches"] for value in self.delegates.since(self.actor, raw_before)), counters=counters,
            team_counters=delta(team_policy.evidence(self.actor), team_before, "last_call"), last_query=copy.deepcopy(current["last_query"]),
            native_team_query=query(self.actor), part_entries=len(parts(self.actor)), temporary_actors=len(temporary), visual=visual(self.actor),
            native_device_properties_created=len(self.properties))
        self.enter("device")

    def observe(self):
        require(time.monotonic()-self.phase_started < 8, "native cosmetic callback device properties did not finish")
        if not self.observer.observed(self.properties) or not self.observer.markers_removed(): return
        self.row.update(native_device_properties=self.observer.rows(self.properties), native_scheduler_removed_owned_properties=True)
        self.case["operations"].append(copy.deepcopy(self.row)); self.operation += 1
        if self.operation < 3: self.enter("operation"); return
        self.case.update(original_part_entries_and_actor_identities_restored=parts(self.actor) == self.original_parts and
            [path(value) for value in part_actors(self.actor)] == self.original_actors, owned_temporary_actors_destroyed=bool(self.spawned) and all(not valid(value) for value in self.spawned))
        self.report["cases"].append(copy.deepcopy(self.case)); ue.log("UEP_CHARACTER_PARTS_CASE_PASSED "+self.case["name"]+"/"+self.initial)
        self.index += 1
        if self.index == len(PLAN): self.finish()
        else: self.prepare()

    def cleanup(self):
        errors = []
        for actor, handle in self.owned_handles:
            try:
                if valid(actor) and any(row["handle"] == int(handle.PartHandle) for row in parts(actor)):
                    component(actor).call_function("RemoveCharacterPart", handle)
            except Exception: errors.append(traceback.format_exc())
        if self.player_state is not None:
            try:
                self.player_state.restore()
                self.report["original_player_visual_camera_profile_cdo_inventory_restored"] = inventory_state(self.controller) == self.inventory_before and str(ue.get_mixin_profile(self.cdo)) == self.cdo_profile
            except Exception: errors.append(traceback.format_exc())
        if self.delegates is not None:
            try: self.delegates.close()
            except Exception: errors.append(traceback.format_exc())
            self.report["delegate_fixture_shutdown"] = self.delegates.snapshot()
        if self.observer is not None:
            self.report.update(native_observation_markers=len(self.observer.markers), native_observation_markers_removed=self.observer.markers_removed())
            try: self.observer.close()
            except Exception: errors.append(traceback.format_exc())
            self.report.update(device_roots_created=self.observer.roots_created, device_roots_released=self.observer.roots_released)
        try:
            if valid(self.fixture_actor): self.fixture_actor.call_function("K2_DestroyActor")
            self.report["owned_unassigned_actor_destroyed"] = self.fixture_actor is not None and not valid(self.fixture_actor)
        except Exception: errors.append(traceback.format_exc())
        if errors: raise RuntimeError("native parts cleanup failed: "+"\n".join(errors))

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "native parts standalone timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "operation": self.operate()
            elif self.phase == "device": self.observe()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_PARTS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_PARTS_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterPartsResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
