"""Typed BP calls on disposable native Characters; no shared pawn physics undo."""
import copy
import time
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .inventory_wait_transitions import Transition as OwnedTransition, end_owned_respawn
from .equipment_hide_observation import Trial as HideTrial
from .inventory_clear_mixin import CLASS, inventory_state
from .outline_validation import path, gc
from .team_observer_observation import proxies
from .initial_inventory_contract import require
from . import ragdoll_mixin as policy, inventory_wait_mixin as wait, initial_inventory_mixin as loadout

PROBE = "/Game/UEPValidation/BP_CharacterRagdollProbe.BP_CharacterRagdollProbe_C"
PHYSICS = "/Game/UEPValidation/PA_CharacterRagdollProbe.PA_CharacterRagdollProbe"
SCENARIOS = [(name, 0, calls, profile) for name, calls in (("stationary", 1), ("moving", 1), ("zero-strength", 1), ("repeat", 2)) for profile in ("BlueprintFallback", "Python")]


def delta(actor, before):
    after = policy.evidence(actor)
    return {key: (after[key]-before[key] if type(after[key]) is int else after[key][len(before[key]):] if key == "trace" else copy.deepcopy(after[key])) for key in after}


def physical(actor):
    mesh = actor.get_property("Mesh"); bone = actor.get_property("RagdollImpulseBone")
    require(valid(mesh) and int(mesh.call_function("GetBoneIndex", bone)) >= 0, "actual native Ragdoll mesh/bone missing")
    return dict(mesh=path(mesh), bone=str(bone), collision_profile=str(mesh.call_function("GetCollisionProfileName")),
        simulating=bool(mesh.call_function("IsSimulatingPhysics", bone)), velocity=policy.vector(mesh.call_function("GetPhysicsLinearVelocity", bone)))


class Caller:
    def __init__(self):
        self.cls = ue.load_class(PROBE); self.object = self.cls.get_cdo(); self.added = not self.cls.is_rooted(); self.released = False
        if self.added: self.cls.add_to_root()
    def call(self, actor): self.object.call_function("Run", actor)
    def close(self):
        if self.added and not self.released: self.cls.remove_from_root(); self.released = True
        return dict(created=int(self.added), released=int(self.released))


class NaturalHideTrial(HideTrial):
    def start(self):
        self.ragdoll_before = copy.deepcopy(policy.evidence(self.owner.pawn)); super().start()
    def capture_hide(self):
        super().capture_hide()
        self.row.update(natural_ragdoll_counters=delta(self.actor, self.ragdoll_before), natural_ragdoll_physical=physical(self.actor))


class Trial(OwnedTransition):
    def __init__(self, world, caller, scenario): super().__init__(world, None, scenario); self.caller = caller
    def start(self):
        self.actor = self.owner.pawn; end_owned_respawn(self.actor)
        self.before_inventory = inventory_state(self.owner.controller); self.pawn_hidden = bool(self.actor.get_property("bHidden"))
        self.original_strength = float(self.actor.get_property("RagdollImpulseStrength"))
        self.actor.set_property("RagdollImpulseStrength", 0. if self.scenario[0] == "zero-strength" else self.original_strength)
        ue.set_mixin_profile(self.actor, self.scenario[3])
        if self.scenario[0] != "stationary":
            self.actor.set_actor_location(ue.FVector(200000., 200000., 5000.))
            self.actor.call_function("LaunchCharacter", ue.FVector(150., 50., 100.), True, True); self.enter("native-launch")
        else: self.invoke()
    def invoke(self):
        name, _, calls, profile = self.scenario; mesh = self.actor.get_property("Mesh"); bone = self.actor.get_property("RagdollImpulseBone")
        velocity = self.actor.get_property("CharacterMovement").call_function("GetLastUpdateVelocity")
        prepared = name != "stationary"
        if prepared:
            # Explicit public-API fixture state, not project/physics property writes.
            # A pre-simulated body makes the native bVelChange delta observable
            # without confounding the initial kinematic -> simulated transfer.
            asset = ue.load_object(ue.find_class("PhysicsAsset"), PHYSICS)
            require(len(asset.get_property("SkeletalBodySetups")) == 1 and not asset.get_property("ConstraintSetup"), "quantitative single-body control differs")
            mesh.call_function("SetPhysicsAsset", asset, True)
            require(mesh.get_property("PhysicsAssetOverride") == asset, "owned mesh did not select the quantitative physics control")
            mesh.call_function("SetAllBodiesBelowSimulatePhysics", bone, True, True)
            mesh.call_function("SetEnableGravity", False); mesh.call_function("SetLinearDamping", 0.); mesh.call_function("SetAngularDamping", 0.)
            mesh.call_function("SetPhysicsLinearVelocity", ue.FVector(3., 4., 5.), False, bone)
            self.actor.get_property("CharacterMovement").call_function("StopMovementImmediately")
            velocity = self.actor.get_property("CharacterMovement").call_function("GetLastUpdateVelocity")
        before_physical = physical(self.actor); before = copy.deepcopy(policy.evidence(self.actor))
        for _ in range(calls): self.caller.call(self.actor)
        self.row = dict(name=name, profile=profile, calls=calls, actual_character_class=path(self.actor.get_class()),
            bp_reference_call=True, native_launch_producer=prepared, known_physics_velocity_prepared_via_native_api=prepared,
            single_body_constraint_free_native_control=prepared, fixture_gravity_and_damping_disabled_via_native_api=prepared,
            physics_properties_written_directly=False, native_before=before_physical, native_after=physical(self.actor),
            input_velocity=policy.vector(velocity), strength=float(self.actor.get_property("RagdollImpulseStrength")),
            counters=delta(self.actor, before), native_pawn_hidden_unchanged=bool(self.actor.get_property("bHidden")) == self.pawn_hidden,
            inventory_unchanged=inventory_state(self.owner.controller) == self.before_inventory, actor_was_not_rooted=not self.actor.is_rooted())
        self.ragdoll_ref = policy.evidence(self.actor); self.ragdoll_snapshot = copy.deepcopy(self.ragdoll_ref)
        self.called_frame = int(ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetFrameCount"))
        self.enter("observe-ragdoll")
    def step(self):
        if self.phase == "owner-ready":
            require(time.monotonic()-self.started < 20., "Ragdoll native owned bot readiness timeout")
            if self.owner.ready(): self.start()
            return False
        if self.phase == "native-launch":
            require(time.monotonic()-self.phase_started < 2., "native LaunchCharacter did not produce nonzero last-update velocity")
            velocity = policy.vector(self.actor.get_property("CharacterMovement").call_function("GetLastUpdateVelocity"))
            if velocity[0] > 100.: self.invoke()
            return False
        if self.phase == "observe-ragdoll":
            frame = int(ue.find_class("KismetSystemLibrary").get_cdo().call_function("GetFrameCount"))
            if frame >= self.called_frame+2 and "native_after_physics_step" not in self.row:
                self.row.update(native_after_physics_step=physical(self.actor), native_physics_frames_elapsed=frame-self.called_frame)
            if time.monotonic()-self.phase_started >= .1 and "native_after_physics_step" in self.row:
                self.actor.set_property("RagdollImpulseStrength", self.original_strength)
                self.row["owned_strength_restored_before_destroy"] = float(self.actor.get_property("RagdollImpulseStrength")) == self.original_strength
                self.wait_ref, self.loadout_ref = wait.evidence(self.actor), loadout.evidence(self.actor)
                self.quiet_snapshot = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref))
                self.close(); gc(); self.enter("cleanup-gc")
            return False
        done = super().step()
        if done: self.row["ragdoll_quiet_after_destroy"] = self.ragdoll_ref == self.ragdoll_snapshot
        return done


class LocalTrial:
    """Fresh, nonreplicated local Actor, including on a real network client."""
    def __init__(self, world, caller, profile):
        self.actor = None; self.closed = False; self.created = time.monotonic(); self.world = world; self.original = set(proxies())
        self.owned = []
        try:
            self.actor = world.actor_spawn(ue.load_class(CLASS), ue.FVector(200000., 200000., 5000.)); self.actor.call_function("SetReplicates", False)
            self.owned = [value for key, value in proxies().items() if key not in self.original]
            before = copy.deepcopy(policy.evidence(self.actor)); ue.set_mixin_profile(self.actor, profile)
            caller.call(self.actor)
            self.row = dict(profile=profile, actual_character_class=path(self.actor.get_class()), bp_reference_call=True,
                test_owned_nonreplicated_local_actor=True, native_role=int(self.actor.call_function("GetLocalRole")),
                actor_was_not_rooted=not self.actor.is_rooted(), native_after=physical(self.actor), counters=delta(self.actor, before))
            self.ragdoll_ref = policy.evidence(self.actor); self.ragdoll_snapshot = copy.deepcopy(self.ragdoll_ref)
            self.wait_ref, self.loadout_ref = wait.evidence(self.actor), loadout.evidence(self.actor)
        except Exception: self.close(); raise
    def close(self):
        if self.closed: return
        if valid(self.actor): self.actor.actor_destroy()
        for value in self.owned:
            if valid(value): value.call_function("Cancel")
        self.closed = True
    def step(self):
        if not self.closed:
            if time.monotonic()-self.created < .1: return False
            self.quiet = (copy.deepcopy(self.wait_ref), copy.deepcopy(self.loadout_ref)); self.close(); gc(); self.closed_at = time.monotonic(); return False
        if time.monotonic()-self.closed_at < .2: return False
        if any(valid(value) for value in self.owned) and time.monotonic()-self.closed_at < 2.: gc(); return False
        self.row.update(owned_actor_destroyed=not valid(self.actor), owned_team_proxies_created=len(self.owned),
            owned_team_proxies_collected=all(not valid(value) for value in self.owned), original_active_proxies_preserved=set(proxies()) == self.original,
            ragdoll_quiet_after_destroy=self.ragdoll_ref == self.ragdoll_snapshot,
            latent_script_quiet_after_destroy=(self.wait_ref, self.loadout_ref) == self.quiet)
        return True
