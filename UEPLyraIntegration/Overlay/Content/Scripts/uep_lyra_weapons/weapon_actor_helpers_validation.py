"""Original/Python helpers on native Pistol/Rifle/Shotgun Actor instances."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod, ESpawnActorScaleMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from . import weapon_actor_helpers_mixin as policy
from .weapon_actor_helpers_contract import CLASSES, PROFILES, FAKE_CASES, OWNERS, TEAMS, require, validate


def path(value): return value.get_path_name() if valid(value) else None
def vec(value): return [float(value.x),float(value.y),float(value.z)]
def rgba(value): return [float(value.r),float(value.g),float(value.b),float(value.a)]


class Validation(Ready):
    healths = Health.healths

    def __init__(self, result):
        super().__init__(result)
        self.require_auto_active = False
        self.actors, self.original_classes = [], {}
        self.report = dict(schema_version=1,status="running",error=None,fake_cases=[],stencil_cases=[],color_cases=[],audio_cases=[],
            full_acceptance=False,network_acceptance=False,packaged_runtime=False,audio_playback_tested=False,real_firing_tested=False,
            health_properties_written=False,official_assets_modified=False,child_blueprints_modified=False)

    def primitive(self, actor, name, root=None):
        item = actor.add_actor_component(ue.find_class("StaticMeshComponent"), name, root) if root is not None else actor.add_actor_root_component(ue.find_class("StaticMeshComponent"), name)
        item.call_function("SetStaticMesh", ue.load_object(ue.find_class("StaticMesh"), "/Engine/BasicShapes/Cube.Cube"))
        item.call_function("SetCollisionEnabled", 0)
        material = ue.load_object(ue.find_class("MaterialInterface"), "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")
        item.call_function("SetMaterial", 0, material)
        dynamic = item.call_function("CreateDynamicMaterialInstance", 0, material, "None")
        require(valid(dynamic), "native dynamic material fixture missing")
        return item, dynamic

    def begin(self):
        bridge = policy.library("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld", self.world)
        self.report["native_mode"] = str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"] == "Standalone", "owned helper fixtures require standalone")
        self.parent = ue.load_class(policy.CLASS)
        ue.register_declared_mixin(self.parent)
        binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == self.parent]
        self.original_classes = {name: row["python_class"] for name, row in binding["profiles"].items()}
        self.health_before = self.healths()
        bots, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.find_class("LyraPlayerBotController"))
        bot_pawns = [bot.get_controlled_pawn() for bot in bots if valid(bot.get_controlled_pawn())]
        require(bot_pawns, "actual native local bot required for weapon stencil distinction")
        self.bot = bot_pawns[0]
        require(self.bot.call_function("IsLocallyControlled") and not self.bot.call_function("IsPlayerControlled"), "actual authority-local bot control witness missing")
        self.unpossessed = self.world.actor_spawn(ue.find_class("Pawn"))
        self.actors.append(self.unpossessed)
        self.display = ue.new_object(ue.find_class("LyraTeamDisplayAsset"))
        self.display.set_property("ColorParameters", {"Color": ue.FLinearColor(.2,.4,.6,1.)})
        self.wall = self.world.actor_spawn(ue.find_class("Actor"))
        self.actors.append(self.wall)
        self.wall_box = self.wall.add_actor_root_component(ue.find_class("BoxComponent"), "UEPHelperWall")
        self.wall_box.call_function("SetBoxExtent", ue.FVector(10.,200.,200.), False)
        self.wall_box.call_function("SetCollisionObjectType", 0)
        self.wall_box.call_function("SetCollisionResponseToAllChannels", 2)
        self.enter("class")

    def delta(self, actor, before): return {key:value-before[key] for key,value in policy.evidence(actor).items()}
    def dispatched(self, delta, method, profile):
        key = method+("_python" if profile == "Python" else "_fallback")
        require(delta[key] == 1, "child did not enter selected inherited parent helper: "+method)
        return True

    def trial_class(self):
        cls = ue.load_class(CLASSES[self.index])
        transform = ue.FTransform(ue.FVector(200000.,200000.,2000.), ue.FRotator(), ue.FVector(1.,1.,1.))
        scale = ESpawnActorScaleMethod.OverrideRootScale
        actor = self.statics.call_function("BeginDeferredActorSpawnFromClass", self.world, cls, transform,
            ESpawnActorCollisionHandlingMethod.AlwaysSpawn, self.pawn, scale)
        actor.set_property("Instigator", self.pawn)
        self.statics.call_function("FinishSpawningActor", actor, transform, scale)
        self.actors.append(actor)
        actor.call_function("SetReplicates", False)
        root = actor.get_property("RootComponent")
        extra, material = self.primitive(actor, "UEPHelperMaterial", root)
        child_component = actor.add_actor_component(ue.find_class("ChildActorComponent"), "UEPHelperChild", root)
        child_component.call_function("SetChildActorClass", ue.find_class("Actor"))
        child = child_component.get_property("ChildActor")
        require(valid(child), "actual native child actor missing")
        child_mesh, child_material = self.primitive(child, "UEPHelperChildMaterial")
        components = policy.library("LyraSystemStatics").call_function("FindComponentsByClass", actor, ue.find_class("PrimitiveComponent"), True)
        require(child_mesh in components and extra in components, "native primitive query omitted child")
        self.report["actual_child_actor_recursion"] = True
        audio = actor.add_actor_component(ue.find_class("AudioComponent"), "UEPHelperAudio", root)
        for profile in PROFILES:
            ue.set_mixin_profile(actor, profile)
            for name, number, angle, wall in FAKE_CASES:
                start = actor.get_property("SkeletalMesh").call_function("GetSocketLocation", "Muzzle")
                seed = ue.FVector(start.x+500.,start.y,start.z)
                actor.set_property("Impact Positions", [seed]); actor.set_property("Impact Normals", [ue.FVector(0.,0.,1.)]); actor.set_property("ImpactSurfaceTypes", [0])
                require(self.wall.call_function("K2_TeleportTo", ue.FVector(start.x+1000.,start.y,start.z), ue.FRotator()), "native trace wall placement failed")
                self.wall_box.call_function("SetCollisionEnabled", 1 if wall else 0)
                before = dict(policy.evidence(actor))
                actor.call_function(policy.FAKE, number, angle)
                delta = self.delta(actor, before)
                self.report["fake_cases"].append(dict(name=name,profile=profile,**{"class":path(cls)},number=number,angle=angle,wall_enabled=wall,
                    start=vec(start),seed=vec(seed),wall_front_x=float(start.x+990.),positions=[vec(v) for v in actor.get_property("Impact Positions")],
                    normals=[vec(v) for v in actor.get_property("Impact Normals")],surfaces=[int(v) for v in actor.get_property("ImpactSurfaceTypes")],
                    delta=delta,parent_dispatch_verified=self.dispatched(delta,"fake",profile)))
            for owner in OWNERS:
                actor.set_property("OwnerAsPawn", {"none":None,"player":self.pawn,"bot":self.bot,"unpossessed":self.unpossessed}[owner])
                for team in TEAMS:
                    flags = [bool(item.get_property("bRenderCustomDepth")) for item in components]
                    before = dict(policy.evidence(actor)); actor.call_function("UpdateCustomStencil", team); delta = self.delta(actor,before)
                    self.report["stencil_cases"].append(dict(profile=profile,**{"class":path(cls)},owner=owner,team=team,
                        values=[int(item.get_property("CustomDepthStencilValue")) for item in components],child_components=sum(item.get_owner() == child for item in components),
                        depth_flags_unchanged=flags == [bool(item.get_property("bRenderCustomDepth")) for item in components],
                        parent_dispatch_verified=self.dispatched(delta,"stencil",profile),delta=delta))
            actor.set_property("OwnerAsPawn", self.pawn)
            for asset_valid, opt_in in ((False,True),(True,False),(True,True)):
                for item in (material,child_material): item.call_function("SetVectorParameterValue", "Color", ue.FLinearColor(.8,.8,.8,1.))
                actor.set_property("ApplyTeamColorsToWeapon", opt_in)
                before = dict(policy.evidence(actor)); actor.call_function("UpdateTeamColors", self.display if asset_valid else None); delta=self.delta(actor,before)
                self.report["color_cases"].append(dict(profile=profile,**{"class":path(cls)},asset_valid=asset_valid,opt_in=opt_in,
                    colors=[rgba(item.call_function("K2_GetVectorParameterValue","Color")) for item in (material,child_material)],child_mesh_included=child_mesh in components,
                    parent_dispatch_verified=self.dispatched(delta,"colors",profile),delta=delta))
            for existing in (False,True):
                actor.set_property("AudioComponent", audio if existing else None)
                before=dict(policy.evidence(actor)); actor.call_function("TriggerFireAudio", None, self.pawn); delta=self.delta(actor,before)
                output=actor.get_property("AudioComponent")
                self.report["audio_cases"].append(dict(profile=profile,**{"class":path(cls)},existing=existing,input_component_retained=output == audio,
                    output_is_null=output is None,parent_dispatch_verified=self.dispatched(delta,"audio",profile),delta=delta))
        actor.call_function("K2_DestroyActor")
        require(not valid(actor) or actor.call_function("IsActorBeingDestroyed"), "test weapon Actor not destroyed")
        self.index += 1
        ue.log("UEP_WEAPON_ACTOR_HELPERS_CLASS_CAPTURED "+path(cls))
        if self.index == len(CLASSES): self.finish()

    def cleanup(self):
        for actor in self.actors:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"): actor.call_function("K2_DestroyActor")
        self.report["test_actors_destroyed"] = all(not valid(actor) or actor.call_function("IsActorBeingDestroyed") for actor in self.actors)
        self.report["all_original_pawn_health_unchanged"] = self.healths() == self.health_before if hasattr(self,"health_before") else False
        self.report["production_classes_restored"] = all(row["profiles"][name]["python_class"] is base for row in ue.get_registered_mixins()
            if row["target_class"] == self.parent for name,base in self.original_classes.items()) if self.original_classes else False

    def tick(self, seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 180., "native weapon helper total timeout")
            if self.phase == "ready": self.ready()
            elif self.phase == "class": self.trial_class()
            self.report["phase"] = self.phase; self.write()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_ACTOR_HELPERS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_WEAPON_ACTOR_HELPERS_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponActorHelpersResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
