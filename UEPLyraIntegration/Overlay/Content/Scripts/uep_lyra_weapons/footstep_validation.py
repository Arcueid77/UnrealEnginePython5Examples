"""Real native motion calls, Niagara stores and the unchanged latent continuation."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer
from unreal_engine.enums import EAttachLocation, ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from uep_lyra_abilities.melee_trace_mixin import break_hit, native_outputs
from .weapon_fire_fx_validation import dead, vec, parameter
from . import footstep_mixin as policy
from .footstep_contract import PROFILES, PATHS, CASES, require, validate

SYSTEM = "/Game/Effects/Particles/Footsteps/NS_Footsteps.NS_Footsteps"


class Validation(Ready):
    healths = Health.healths
    def __init__(self, result):
        super().__init__(result); self.require_auto_active = False
        self.actors = []; self.materials = []; self.original_classes = {}; self.cleanup_events = []; self.target = None
        self.report = dict(schema_version=1, status="running", error=None, cases=[], timer_cases=[],
            full_acceptance=False, network_acceptance=False, packaged_runtime=False, pixels_tested=False,
            audio_playback_tested=False, timer_properties_written=False, latent_callback_replayed=False,
            health_properties_written=False, natural_animation_dispatch_tested=False)
    def begin(self):
        bridge = policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld", self.world)
        self.report["native_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"] == "Standalone", "native standalone required")
        self.health_before = self.healths(); self.mesh = self.pawn.get_property("Mesh")
        self.cls = ue.load_class(policy.CLASS); ue.register_declared_mixin(self.cls)
        self.probe = ue.load_class("/Game/UEPValidation/BP_FootstepCaller.BP_FootstepCaller_C").get_cdo(); self.probe.add_to_root()
        self.system = ue.load_object(ue.find_class("NiagaraSystem"), SYSTEM)
        self.location = self.pawn.get_actor_location()
        self.warm = self.world.actor_spawn(ue.find_class("Actor"), self.location); self.actors.append(self.warm)
        self.root = self.warm.add_actor_root_component(ue.find_class("SceneComponent"), "UEPFootstepWarm")
        self.warm_component = policy.lib("NiagaraFunctionLibrary").call_function("SpawnSystemAttached", SystemTemplate=self.system,
            AttachToComponent=self.root, AttachPointName="None", Location=ue.FVector(), Rotation=ue.FRotator(),
            LocationType=EAttachLocation.KeepRelativeOffset, bAutoDestroy=False, bAutoActivate=True,
            PoolingMethod=getattr(ENCPoolMethod, "None"), bPreCullCheck=True)
        require(valid(self.warm_component), "native footprint prewarm failed")
        self.material_map = {0:None}
        for surface in (1, 2, 3, 4, 63):
            material = ue.new_object(ue.find_class("PhysicalMaterial")); material.set_property("SurfaceType", surface)
            material.add_to_root(); self.materials.append(material); self.material_map[surface] = material
        binding, = [r for r in ue.get_registered_mixins() if r["target_class"] == self.cls]
        self.original_classes = {name:row["python_class"] for name,row in binding["profiles"].items()}; owner = self
        for name, base in self.original_classes.items():
            def around(handler, profile):
                def invoke(actor):
                    if actor == owner.target: owner.cleanup_events.append(dict(profile=profile, time=owner.game_time()))
                    return handler(actor)
                invoke.override = policy.AFTER; return invoke
            ue.register_mixin_profile(self.cls, name, type("ObservedFootstepDelay"+name, (), dict(AnimMotionEffect=base.AnimMotionEffect, AfterDelay=around(base.AfterDelay, name))))
        self.warm_ticks = 0; self.enter("warm")
    def spawn(self, profile, enabled=True):
        actor = self.world.actor_spawn(self.cls, self.location); self.actors.append(actor)
        actor.set_property("Skeletal Mesh Component", self.mesh); actor.set_property("Foot Print System", self.system)
        actor.set_property("FootStepRightFootBone", "foot_r"); actor.set_property("Enable FootPlantEffect", enabled)
        ue.set_mixin_profile(actor, profile); return actor
    def hit(self, surface, normal):
        return self.statics.call_function("MakeHitResult", bBlockingHit=True, bInitialOverlap=False, Time=.5, Distance=17.,
            Location=ue.FVector(121.25, -42.5, 17.), ImpactPoint=ue.FVector(-600., 800., -900.),
            Normal=ue.FVector(*normal), ImpactNormal=ue.FVector(0., -1., 0.), PhysMat=self.material_map[surface],
            HitActor=self.pawn, HitComponent=self.mesh, HitBoneName="foot_l", BoneName="foot_r",
            HitItem=2, ElementIndex=1, FaceIndex=3, TraceStart=ue.FVector(1., 2., 3.), TraceEnd=ue.FVector(4., 5., 6.))
    def args(self, name="cold"):
        surface = {"reuse":1, "right-case":2, "surface-three":3, "unsupported-four":4, "unsupported-sixty-three":63}.get(name, 0)
        normal = {"zero-normal":(0., 0., 0.), "parallel-normal":(1., 0., 0.), "tilted-normal":(.3, -.4, .5), "nonunit-normal":(0., 0., 7.)}.get(name, (0., 0., 1.))
        bone = "FOOT_R" if name == "right-case" else "None" if name == "empty-bone" else "foot_l" if name == "reuse" else "foot_r"
        # Deliberately different from the stored mesh; unused ABI inputs are non-default.
        component = None if name == "ignored-inputs" else self.root
        return (bone, GameplayTag(), component, ue.FVector(91., -82., 73.), ue.FRotator(7., 8., 9.), None,
            name != "miss", self.hit(surface, normal), GameplayTagContainer(), ue.FVector(2., 3., 4.), .37, 2.7), surface
    def invoke(self, actor, path="direct", name="cold"):
        args, surface = self.args(name)
        if path == "direct": actor.call_function("AnimMotionEffect", *args)
        else: self.probe.call_function("CallMotion", actor, *args)
        return surface
    def state(self, actor):
        get = actor.get_property; q = get("FootStepOrientation")
        t = native_outputs("KismetMathLibrary", "BreakTransform", policy.lib("KismetMathLibrary").call_function("BreakTransform", get("FootStepSocketTransform")))
        rotation = t["Rotation"]; hit = break_hit(get("Hit Result"))
        return dict(trigger=bool(get("FootPrintTrigger")), side=bool(get("FootStepSide")), surface=int(get("FootStepSurfaceType")),
            surface_niagara=int(get("FootStepSurfaceTypeNiagara")), socket=str(get("CurrentSocket")), location=vec(get("FootStepHitLocation")),
            normal=vec(get("FootStepHitNormal")), orientation=[float(q.x), float(q.y), float(q.z), float(q.w)],
            transform=dict(location=vec(t["Location"]), rotation=[float(rotation.roll), float(rotation.pitch), float(rotation.yaw)], scale=vec(t["Scale"])),
            hit=dict(location=vec(hit["Location"]), impact=vec(hit["ImpactPoint"]), normal=vec(hit["Normal"]), impact_normal=vec(hit["ImpactNormal"]),
                surface=int(self.statics.call_function("GetSurfaceType", get("Hit Result")))))
    def parameters(self, component):
        if not valid(component): return None
        return dict(trigger=bool(parameter(component, "User.Trigger", "<i")[0]), location=parameter(component, "User.StepLocation", "<3f"),
            orientation=parameter(component, "User.Orientation", "<4f"), surface=parameter(component, "User.SurfaceType", "<i")[0], side=bool(parameter(component, "User.StepSide", "<i")[0]))
    def visual_trials(self):
        for profile in PROFILES:
            for path in PATHS:
                actor = self.spawn(profile); self.target = actor
                for name in CASES:
                    actor.set_property("Enable FootPlantEffect", name not in ("disabled", "cached-disabled"))
                    if name == "empty-bone": actor.set_property("FootStepRightFootBone", "None")
                    else: actor.set_property("FootStepRightFootBone", "foot_r")
                    if name == "replace-inactive":
                        inactive = actor.add_actor_component(ue.find_class("NiagaraComponent"), "UEPInactiveFootprint")
                        require(not inactive.call_function("IsActive"), "empty cache fixture unexpectedly active")
                        actor.set_property("NS_FootPrint", inactive); actor.set_property("FootPrintTrigger", True)
                    old = actor.get_property("NS_FootPrint"); before = self.state(actor)
                    # Empty inactive fixtures have no parameter overrides.
                    before_parameters = self.parameters(old) if valid(old) and name != "replace-inactive" else None
                    count = dict(policy.evidence(actor)); surface = self.invoke(actor, path, name); after = policy.evidence(actor)
                    component = actor.get_property("NS_FootPrint"); rotation = component.get_property("RelativeRotation")
                    self.report["cases"].append(dict(name=name, path=path, profile=profile, input_surface=surface,
                        before_state=before, state=self.state(actor), before_parameters=before_parameters, parameters=self.parameters(component),
                        component_valid=valid(component), same_cached=component == old, stored_mesh_unchanged=actor.get_property("Skeletal Mesh Component") == self.mesh,
                        attached_to_root=component.call_function("GetAttachParent") == actor.get_property("DefaultSceneRoot"),
                        relative_location=vec(component.get_property("RelativeLocation")), relative_rotation=[float(rotation.roll), float(rotation.pitch), float(rotation.yaw)],
                        actual_selected_motion_dispatch=after["python_calls" if profile == "Python" else "fallback_calls"]-count["python_calls" if profile == "Python" else "fallback_calls"] == 1))
                actor.call_function("K2_DestroyActor")
        self.index = 0; self.start_timer()
    def start_timer(self):
        self.profile = PROFILES[self.index]; self.target = self.spawn(self.profile, False); self.cleanup_events = []
        self.timer_start = self.game_time(); self.invoke(self.target); self.retriggered = False; self.survived = False; self.enter("timer")
    def timer(self):
        elapsed = self.game_time()-self.timer_start
        if not self.retriggered and elapsed >= 1.:
            require(not dead(self.target), "footstep died before delay"); self.invoke(self.target); self.retriggered = True
        if 3.1 <= elapsed < 3.4: require(not dead(self.target), "native delay did not reset"); self.survived = True
        if not dead(self.target): require(elapsed < 5.5, "native retriggered cleanup failed"); return
        self.timer_row = dict(profile=self.profile, native_retrigger_observed=self.retriggered, survived_original_deadline=self.survived, destroyed_after_retrigger=True, destroy_elapsed=elapsed)
        self.target = self.spawn(self.profile, False); self.cleanup_events = []
        self.hold_component = self.target.add_actor_component(ue.find_class("NiagaraComponent"), "UEPValidInactiveFootprint")
        require(not self.hold_component.call_function("IsActive"), "hold fixture unexpectedly active")
        self.target.set_property("NS_FootPrint", self.hold_component); self.hold_start = self.game_time()
        self.invoke(self.target); self.hold_removed = False; self.enter("hold")
    def hold(self):
        elapsed = self.game_time()-self.hold_start
        if not self.hold_removed and self.cleanup_events:
            require(not dead(self.target) and valid(self.hold_component) and not self.hold_component.call_function("IsActive"), "valid inactive footprint did not retain actor")
            self.timer_row.update(valid_inactive_kept_actor_alive=True, native_repeat_cleanup_observed=True)
            self.hold_component.call_function("K2_DestroyComponent", self.target); self.hold_removed = True
        if not dead(self.target): require(elapsed < 7.5, "native repeated cleanup failed"); return
        self.timer_row["destroyed_after_component_removal"] = True; self.report["timer_cases"].append(self.timer_row); self.index += 1
        if self.index == len(PROFILES): self.finish()
        else: self.start_timer()
    def cleanup(self):
        self.target = None
        for actor in self.actors:
            if not dead(actor): actor.call_function("K2_DestroyActor")
        for material in self.materials: material.remove_from_root()
        self.report["materials_unrooted"] = all(not m.is_rooted() for m in self.materials)
        if hasattr(self, "probe"): self.probe.remove_from_root(); self.report["diagnostic_probe_unrooted"] = not self.probe.is_rooted()
        if self.original_classes:
            for name, base in self.original_classes.items(): ue.register_mixin_profile(self.cls, name, base)
            binding, = [r for r in ue.get_registered_mixins() if r["target_class"] == self.cls]
            self.report["production_classes_restored"] = all(binding["profiles"][name]["python_class"] is base for name,base in self.original_classes.items())
        self.report["all_test_actors_destroyed"] = all(dead(actor) for actor in self.actors)
        self.report["original_pawn_health_unchanged"] = hasattr(self, "health_before") and self.healths() == self.health_before
    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 220., "native footprint total timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "warm":
                require(time.monotonic()-self.phase_started < 20., "native footprint warmup timeout")
                self.warm_ticks = self.warm_ticks+1 if self.warm_component.call_function("IsActive") else 0
                if self.warm_ticks >= 3: self.report["native_warmup_ready"] = True; self.visual_trials()
            elif self.phase == "timer": self.timer()
            elif self.phase == "hold": self.hold()
            self.report["phase"] = self.phase; self.write(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False
    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try: self.cleanup()
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error); self.write()
        (ue.log_error if error else ue.log)("UEP_FOOTSTEP_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED")); ue.request_exit()
    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_FOOTSTEP_SHUTDOWN_"+self.report["status"].upper())


result = next((v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPFootstepResult=")), None)
if result:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
