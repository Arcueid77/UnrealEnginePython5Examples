"""Typed BP team calls; observe native materials/stencil/device scheduler only."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import ActivateDevicePropertyParams
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_devices import team_color_mixin as device_policy
from uep_lyra_devices.team_color_validation import state as device_state
from .inventory_clear_mixin import inventory_state
from .outline_validation import canon, rgba, path
from . import team_cosmetics_mixin as policy, outline_mixin as outline
from .team_cosmetics_contract import CLASS, PLAN, require, validate

PROBE = "/Game/UEPValidation/BP_CharacterTeamCallProbe.BP_CharacterTeamCallProbe_C"


def primitives(actor):
    return ue.find_class("LyraSystemStatics").get_cdo().call_function("FindComponentsByClass", actor, ue.find_class("PrimitiveComponent"), True)


def material_state(value):
    if not valid(value): return None
    if not value.is_a(ue.find_class("MaterialInstanceDynamic")): return dict(asset=path(value))
    info = lambda entry: [str(entry.ParameterInfo.Name), int(entry.ParameterInfo.Association), int(entry.ParameterInfo.Index)]
    return dict(parent=path(value.get_property("Parent")),
        scalars=sorted([info(entry)+[float(entry.ParameterValue)] for entry in value.get_property("ScalarParameterValues")]),
        vectors=sorted([info(entry)+[rgba(entry.ParameterValue)] for entry in value.get_property("VectorParameterValues")]),
        textures=sorted([info(entry)+[path(entry.ParameterValue)] for entry in value.get_property("TextureParameterValues")]))


def visual(actor):
    values = []
    for component in primitives(actor):
        materials = component.call_function("GetMaterials") if component.is_a(ue.find_class("MeshComponent")) else []
        values.append(dict(component=component.get_path_name().replace(actor.get_path_name(), "Actor", 1),
            stencil=int(component.get_property("CustomDepthStencilValue")), materials=[material_state(value) for value in materials]))
    material = actor.get_property(outline.FIELD)
    return dict(primitives=sorted(values, key=lambda row: row["component"]),
        outline=dict(scalar=float(material.call_function("K2_GetScalarParameterValue", "TeamID")),
            vector=rgba(material.call_function("K2_GetVectorParameterValue", "TeamColor"))) if valid(material) else None)


class DeviceObserver:
    def __init__(self):
        self.subsystem = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetEngineSubsystem", ue.find_class("InputDeviceSubsystem"))
        self.cls = ue.load_class(policy.DEVICE); self.owned = []; self.markers = []
        self.roots_created = self.roots_released = 0
        self.library = ue.find_class("InputDeviceLibrary").get_cdo()

    def marker(self):
        # Native monotonically acquired handles bracket a synchronous BP call.
        # Only copied handle PODs are used for read-only public API queries;
        # never write ActiveProperties, the native counter, or production handles.
        # The Engine deliberately does not create this subsystem on dedicated
        # servers. Observe that absence; never manufacture one for the test.
        if not valid(self.subsystem): return None
        user = self.library.call_function("GetPrimaryPlatformUser")
        handle = self.subsystem.call_function("ActivateDevicePropertyOfClass", ue.find_class("ColorInputDeviceProperty"), ActivateDevicePropertyParams(UserId=user))
        value = self.subsystem.call_function("GetActiveDeviceProperty", handle)
        require(valid(value), "native device observation marker unavailable")
        data = value.ColorData; data.bEnable = False; data.bResetAfterCompletion = False; value.ColorData = data
        rooted = not value.is_rooted()
        if rooted: value.add_to_root(); self.roots_created += 1
        self.owned.append((value, rooted)); self.markers.append(handle)
        return handle

    def collect(self, before):
        if not valid(self.subsystem):
            require(before is None, "absent native device subsystem has a marker")
            return []
        after = self.marker(); first, last = int(before.InternalId), int(after.InternalId)
        require(0 < last-first <= 64, "native device observation handle interval is not bounded")
        props = []
        for number in range(first+1, last):
            handle = before.clone(); handle.InternalId = number
            value = self.subsystem.call_function("GetActiveDeviceProperty", handle)
            require(self.subsystem.call_function("IsPropertyActive", handle) and valid(value) and value.get_class() == self.cls and
                value.get_outer() == self.subsystem, "native device interval contains an unexpected activation")
            rooted = not value.is_rooted()
            if rooted: value.add_to_root(); self.roots_created += 1
            self.owned.append((value, rooted))
            props.append((handle, value))
        return props

    def observed(self, props):
        return all(not self.subsystem.call_function("IsPropertyActive", handle) and
            not valid(self.subsystem.call_function("GetActiveDeviceProperty", handle)) and
            device_policy.instance_snapshot(value)["evaluations"] >= 1 for handle, value in props)

    def rows(self, props):
        return [dict(native_type=path(value.get_class()), counters=device_policy.instance_snapshot(value), color=device_state(value)) for handle, value in props]

    def markers_removed(self):
        return all(not self.subsystem.call_function("IsPropertyActive", handle) and
            not valid(self.subsystem.call_function("GetActiveDeviceProperty", handle)) for handle in self.markers)

    def close(self):
        # On failure remove only the explicitly returned fixture-marker handles.
        # Never synthesize a removal request for any production handle.
        for handle in self.markers:
            if self.subsystem.call_function("IsPropertyActive", handle): self.subsystem.call_function("RemoveDevicePropertyByHandle", handle)
        for value, rooted in self.owned:
            if rooted and value.is_rooted(): value.remove_from_root(); self.roots_released += 1


class ActorState:
    def __init__(self, actor):
        self.actor, self.profile = actor, str(ue.get_mixin_profile(actor))
        self.before = visual(actor); self.camera = actor.get_property("CameraComponent")
        self.pp = self.camera.get_property("PostProcessSettings").clone(); self.pp_before = canon(self.pp)
        self.material = actor.get_property(outline.FIELD)
        self.material_values = self.before["outline"]
        self.components = [(component, int(component.get_property("CustomDepthStencilValue")),
            list(component.call_function("GetMaterials")) if component.is_a(ue.find_class("MeshComponent")) else None) for component in primitives(actor)]

    def restore(self):
        for component, stencil, materials in self.components:
            component.call_function("SetCustomDepthStencilValue", stencil)
            if materials is not None:
                for index, material in enumerate(materials): component.call_function("SetMaterial", index, material)
        self.actor.set_property(outline.FIELD, self.material)
        if valid(self.material):
            self.material.call_function("SetScalarParameterValue", "TeamID", self.material_values["scalar"])
            self.material.call_function("SetVectorParameterValue", "TeamColor", ue.FLinearColor(*self.material_values["vector"]))
        self.camera.set_property("PostProcessSettings", self.pp); ue.set_mixin_profile(self.actor, self.profile)
        require(visual(self.actor) == self.before and canon(self.camera.get_property("PostProcessSettings")) == self.pp_before and
            str(ue.get_mixin_profile(self.actor)) == self.profile, "native team original visual/camera/Profile state not restored")
        return True


class Validation(Ready):
    def __init__(self, result):
        super().__init__(result); self.states, self.fixture_actor, self.observer, self.caller = [], None, None, None
        self.caller_root, self.caller_released = False, False
        self.report.update(hardware_output_tested=False, pixels_verified=False, whole_character_migrated=False, full_acceptance=False,
            device_mapping_written=False, callbacks_replayed=False, all_device_properties_removed=False,
            original_visual_camera_profile_cdo_inventory_restored=False)

    def begin(self):
        self.report["natural_startup_python_dispatch"] = copy.deepcopy(policy.evidence(self.pawn))
        last = self.report["natural_startup_python_dispatch"]["last_call"]
        require(last is not None, "natural team callback did not enter Python")
        self.original_team = int(last["team_id"])
        self.display = ue.load_object(ue.find_class("LyraTeamDisplayAsset"), last["display_asset"]) if last["display_asset"] else None
        self.inventory_before = inventory_state(self.controller); self.cdo = self.pawn.get_class().get_cdo()
        self.cdo_before = (str(ue.get_mixin_profile(self.cdo)), path(self.cdo.get_property(outline.FIELD)))
        self.caller = ue.load_class(PROBE); self.probe = self.caller.get_cdo(); self.caller_root = not self.caller.is_rooted()
        if self.caller_root: self.caller.add_to_root()
        self.observer = DeviceObserver()
        self.fixture_actor = self.world.actor_spawn(ue.load_class(CLASS), ue.FVector(200000., 200000., 2000.))
        self.fixture_actor.call_function("SetReplicates", False)
        for actor in (self.pawn, self.fixture_actor): self.states.append(ActorState(actor))
        self.report.update(retained_character_class=self.pawn.get_class().get_path_name(), original_team_id=self.original_team,
            original_display_asset=path(self.display), current_display_asset_valid=valid(self.display), fixture_actor_replication_disabled=True)
        self.enter("trial")

    def start_trial(self):
        name, profile, source, team, calls, target = PLAN[self.index]
        state = self.states[0 if target == "owner" else 1]; actor = state.actor
        team = self.original_team if team == "current" else team
        display = self.display if source == "current" else None
        expected_color = ue.find_class("LyraTeamStatics").get_cdo().call_function("GetTeamColorWithFallback", display, "TeamColor", ue.FLinearColor(*policy.FALLBACK))
        user = actor.call_function("GetPlatformUserId")
        user_valid = bool(ue.find_class("InputDeviceLibrary").get_cdo().call_function("IsValidPlatformId", user))
        before_props = self.observer.marker(); before = copy.deepcopy(policy.evidence(actor)); before_outline = dict(outline.evidence(actor))
        ue.set_mixin_profile(actor, profile)
        for number in range(calls): self.probe.call_function("UpdateTeam", actor, team, display)
        self.properties = self.observer.collect(before_props); after = policy.evidence(actor)
        self.row = dict(name=name, profile=profile, source=source, team_id=team, calls=calls, target=target, bp_reference_call=True,
            expected_color=rgba(expected_color), locally_controlled=bool(actor.call_function("IsLocallyControlled")),
            player_controlled=bool(actor.call_function("IsPlayerControlled")), platform_user_valid=user_valid, actual=visual(actor),
            counters={key: after[key]-before[key] for key in after if key != "last_call"},
            outline_counters={key: value-before_outline[key] for key, value in outline.evidence(actor).items()},
            native_device_properties_created=len(self.properties))
        require(valid(self.observer.subsystem) or not user_valid, "valid production platform user lacks its native device subsystem")
        self.row["original_visual_camera_profile_restored"] = state.restore()
        self.enter("device")

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 360, "native team orchestration total timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "trial" and time.monotonic()-self.phase_started >= .1: self.start_trial()
            elif self.phase == "device":
                require(time.monotonic()-self.phase_started < 8, "native device scheduler did not evaluate/remove owned properties")
                if self.observer.observed(self.properties) and self.observer.markers_removed():
                    self.row["native_device_properties"] = self.observer.rows(self.properties)
                    self.row["native_scheduler_removed_owned_properties"] = True; self.report["cases"].append(copy.deepcopy(self.row))
                    ue.log("UEP_CHARACTER_TEAM_CASE_PASSED "+self.row["name"]+"/"+self.row["profile"])
                    self.index += 1
                    if self.index == len(PLAN): self.finish()
                    else: self.enter("trial")
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def cleanup(self):
        errors = []
        for state in self.states:
            try: state.restore()
            except Exception: errors.append(traceback.format_exc())
        if self.observer is not None:
            self.report.update(native_observation_markers=len(self.observer.markers), native_observation_markers_removed=self.observer.markers_removed(),
                native_device_subsystem_available=valid(self.observer.subsystem), native_handle_queries_read_only=True, native_active_set_written=False)
            try: self.observer.close()
            except Exception: errors.append(traceback.format_exc())
            self.report.update(device_roots_created=self.observer.roots_created, device_roots_released=self.observer.roots_released)
        if self.states:
            self.report["original_visual_camera_profile_cdo_inventory_restored"] = not errors and inventory_state(self.controller) == self.inventory_before and (
                str(ue.get_mixin_profile(self.cdo)), path(self.cdo.get_property(outline.FIELD))) == self.cdo_before
        try:
            if valid(self.fixture_actor): self.fixture_actor.call_function("K2_DestroyActor")
        except Exception: errors.append(traceback.format_exc())
        self.report["owned_unpossessed_actor_destroyed"] = self.fixture_actor is not None and not valid(self.fixture_actor)
        if self.caller_root and not self.caller_released:
            try: self.caller.remove_from_root(); self.caller_released = True
            except Exception: errors.append(traceback.format_exc())
        self.report.update(caller_roots_created=int(self.caller_root), caller_roots_released=int(self.caller_released))
        if errors: raise RuntimeError("team fixture cleanup failed: "+"\n".join(errors))

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_CHARACTER_TEAM_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_CHARACTER_TEAM_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPCharacterTeamResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
