"""Actual equipment/input activation; original Cue transport and montage ends."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import capture,services
from uep_lyra_network_bots import isolate_bots
from uep_lyra_hud.weapon_validation_helpers import set_stat
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities import reload_weapon_fixture as fixtures,reload_magazine_mixin as ammo
from uep_lyra_abilities.melee_trace_mixin import break_hit
from .weapon_fire_fx_validation import dead,vec
from .netshooter_actor_validation import near,rotation
from . import netshooter_ability_mixin as policy,weapon_ability_fire_mixin as parent
from .netshooter_ability_contract import PLAN,require,validate

ITEM="/ShooterCore/Weapons/NetShooter_PROTO/ID_NetShooter.ID_NetShooter_C"
CUE="/ShooterCore/Weapons/Shotgun/GCN_Weapon_Shotgun_Fire.GCN_Weapon_Shotgun_Fire_C"


def path(value):return value.get_path_name() if valid(value) else None


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.fixture=None;self.observers={};self.created=[];self.recording=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[])
        for key in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
                    "activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed","health_properties_written",
                    "ammo_properties_written","projectile_spawn_requested_by_fixture","projectile_physics_accepted"):self.report[key]=False
    def projectiles(self):return [value for value in self.world.all_actors() if valid(value) and value.is_a(self.projectile_cls) and not dead(value)]
    def observe(self):
        ue.register_declared_mixin(self.cls);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls]
        self.observers={name:value["python_class"] for name,value in binding["profiles"].items()};owner=self
        for profile,base in self.observers.items():
            def around_activate(handler):
                def invoke(actor):
                    before=set(owner.projectiles());watch=owner.recording and actor==owner.ability
                    if watch:
                        owner.activations+=1;owner.before_location,owner.before_rotation=owner.expected_pose()
                    result=handler(actor)
                    if watch:
                        anim=owner.pawn.get_property("Mesh").call_function("GetAnimInstance");montage=actor.get_property("CharacterFireMontage")
                        owner.montage_observed=valid(montage) and bool(anim.call_function("Montage_IsPlaying",montage))
                        owner.pose_matches=near(vec(actor.get_property("Location")),vec(owner.before_location)) and near(rotation(actor.get_property("Direction")),rotation(owner.before_rotation))
                        new=[value for value in owner.projectiles() if value not in before];owner.spawn_count=len(new)
                        owner.spawn_matches=bool(new);owner.spawn_defaults=bool(new);owner.spawn_hit_default=bool(new);owner.projectile_cleanup=bool(new)
                        for projectile in new:
                            owner.created.append(projectile)
                            owner.spawn_matches&=near(vec(projectile.get_actor_location()),vec(owner.before_location)) and near(rotation(projectile.get_actor_rotation()),rotation(owner.before_rotation)) and near(vec(projectile.call_function("GetActorScale3D")),[.1,.1,.1])
                            owner.spawn_defaults&=projectile.call_function("GetOwner") is None and projectile.call_function("GetInstigator")==owner.pawn
                            hit=break_hit(projectile.get_property("HitBreakResult"));owner.spawn_hit_default&=not hit["bBlockingHit"]
                            owner.projectile_cleanup&=projectile.get_property("ProjectileMovement").call_function("IsActive") and not getattr(projectile,"_uep_netshooter_actor",{}).get("hit_bodies",0)
                            projectile.call_function("K2_DestroyActor");owner.projectile_cleanup&=dead(projectile)
                        if owner.kind=="cancel":actor.call_function("K2_CancelAbility")
                        elif owner.kind=="interrupt":owner.pawn.call_function("StopAnimMontage",montage)
                    return result
                invoke.override="K2_ActivateAbility";return invoke
            def around_data(handler):
                def invoke(actor,TargetData):
                    if owner.recording and actor==owner.ability:owner.data_entries+=1
                    return handler(actor,TargetData)
                invoke.override="OnRangedWeaponTargetDataReady";return invoke
            methods=dict(Activate=around_activate(base.Activate),TargetData=around_data(base.TargetData))
            for name,event in (("Completed","OnCompleted"),("Interrupted","OnInterrupted"),("Cancelled","OnCancelled")):
                def around_callback(handler,label):
                    def invoke(actor):
                        if owner.recording and actor==owner.ability:owner.callbacks.append(label)
                        return handler(actor)
                    invoke.override=policy.CALLBACKS[label];return invoke
                methods[name]=around_callback(getattr(base,name),event)
            ue.register_mixin_profile(self.cls,profile,type("ObservedNetAbility"+profile,(),methods))
    def expected_pose(self):
        camera=self.controller.get_property("PlayerCameraManager");forward=self.controller.call_function("GetActorForwardVector");point=camera.call_function("GetCameraLocation")
        return self.math.call_function("MakeVector",point.x+forward.x*350.,point.y+forward.y*350.,point.z+forward.z*350.),camera.call_function("GetCameraRotation")
    def cue_values(self,params):
        mesh=self.pawn.get_property("Mesh");point=vec(mesh.call_function("GetSocketLocation","weapon_r_muzzle"));offset=self.ability.get_property("OffsetGCN")
        for name,amount in (("GetActorForwardVector",offset.x),("GetActorUpVector",offset.z),("GetActorRightVector",offset.y)):
            basis=vec(self.pawn.call_function(name));point=[a+b*amount for a,b in zip(point,basis)]
        normal=self.math.call_function("Conv_RotatorToVector",mesh.call_function("GetSocketRotation","weapon_r_muzzle"))
        defaults=(params.NormalizedMagnitude==0. and params.RawMagnitude==0. and params.GameplayEffectLevel==1 and params.AbilityLevel==1 and
            not params.bReplicateLocationWhenUsingMinimalRepProxy and all(getattr(params,name) is None for name in ("Instigator","EffectCauser","SourceObject","PhysicalMaterial","TargetAttachComponent")))
        return dict(location=vec(params.Location),normal=vec(params.Normal),geometry_matches=near(vec(params.Location),point) and near(vec(params.Normal),vec(normal)),defaults_match=defaults)
    def observe_cue(self):
        self.cue_cls=ue.load_class(CUE);require(not any(row["target_class"]==self.cue_cls for row in ue.get_registered_mixins()),"do not replace production Cue Profile")
        self.original_cue=self.cue_cls.get_cdo().find_function("OnBurst");owner=self
        class ObserveCue:
            def OnBurst(self,Target,Parameters,SpawnResults):
                if owner.recording and Target==owner.pawn:owner.cues.append(owner.cue_values(Parameters))
                return self.call_mixin_original("OnBurst",Target,Parameters,SpawnResults)
        ue.register_mixin_profile(self.cue_cls,"UEPNetAbilityCueObserve",ObserveCue,make_default=True)
    def begin(self):
        self.report["native_mode"]=str(policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world).call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","native NetShooter ability standalone required")
        self.original=fixtures.baseline(self.controller);self.player_health=float(self.health.call_function("GetHealth"));self.original_control=self.controller.call_function("GetControlRotation")
        self.original_view_target=self.controller.call_function("GetViewTarget")
        self.original_point=self.pawn.get_actor_location();self.original_rotation=self.pawn.get_actor_rotation();self.movement=self.pawn.get_property("CharacterMovement")
        self.original_mode=int(self.movement.get_property("MovementMode"));self.original_custom=int(self.movement.get_property("CustomMovementMode"))
        self.movement.call_function("SetMovementMode",5,0);self.movement.call_function("StopMovementImmediately")
        require(self.pawn.call_function("K2_TeleportTo",ue.FVector(50000.,50000.,10000.),ue.FRotator()),"native isolated ability pose refused")
        self.camera_fixture=self.world.actor_spawn(ue.find_class("CameraActor"));self.created.append(self.camera_fixture)
        require(self.camera_fixture.call_function("K2_TeleportTo",ue.FVector(50000.,50000.,10200.),ue.FRotator(0.,65.,35.)),"native independent view-target pose refused")
        self.controller.call_function("SetViewTargetWithBlend",self.camera_fixture,0.,0,0.,False);self.report["native_independent_camera_view_target_fixture"]=True
        self.math=policy.lib("KismetMathLibrary");self.cls=ue.load_class(policy.CLASS);self.projectile_cls=ue.load_class(policy.PROJECTILE);self.observe()
        self.observe_cue()
        self.actions=[ue.load_object(ue.find_class("InputAction"),"/Game/Input/Actions/"+name+"."+name) for name in ("IA_Weapon_Fire","IA_Weapon_Fire_Auto")]
        inventory,quickbar=services(self.controller);slot=int(quickbar.call_function("GetNextFreeItemSlot"));require(slot>0,"native temporary NetShooter slot missing")
        item=inventory.call_function("AddItemDefinition",ue.load_class(ITEM),1);require(valid(item),"native NetShooter inventory item not created")
        self.fixture=dict(self.original,owned_item=path(item),slot=slot,weapon="netshooter");quickbar.call_function("AddItemToSlot",slot,item);quickbar.call_function("SetActiveSlotIndex",slot);self.enter("weapon-ready")
    def weapon_ready(self):
        model=capture(self.controller)
        if model is None or model["definition"]!=ITEM:return
        found=[value for spec in self.asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class()==self.cls
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
        if len(found)!=1 or found[0].get_property("bIsActive"):return
        self.ability=found[0];self.item=self.ability.call_function("GetAssociatedItem");self.original_profile=str(ue.get_mixin_profile(self.ability));self.original_montage=self.ability.get_property("CharacterFireMontage");self.original_offset=self.ability.get_property("OffsetGCN")
        self.added_initial=parent.evidence(self.ability)["added"]+parent.evidence(self.ability)["fallback_added"];self.start_case()
    def inject(self,value):
        for action in self.actions:self.controller.inject_enhanced_input_for_action(action,value)
    def start_case(self):
        self.profile,self.kind=PLAN[self.index];ue.set_mixin_profile(self.ability,self.profile)
        self.ability.set_property("OffsetGCN",self.math.call_function("MakeVector",25.125,-10.5,42.25) if self.kind=="complete-offset" else self.original_offset)
        self.ability.set_property("CharacterFireMontage",None if self.kind=="null-montage" else self.original_montage)
        set_stat(self.item,ammo.MAGAZINE,8);self.controller.call_function("SetControlRotation",ue.FRotator(0.,55.,80.));self.enter("aim")
    def start_input(self):
        self.callbacks=[];self.cues=[];self.activations=0;self.data_entries=0;self.spawn_count=0;self.montage_observed=False;self.pose_matches=False
        self.spawn_matches=False;self.spawn_defaults=False;self.spawn_hit_default=False;self.projectile_cleanup=False
        self.parent_before=copy.deepcopy(parent.evidence(self.ability));self.ammo_before=ammo.ammo(self.item)[0];self.case_started=self.game_time();self.recording=True
        camera=self.controller.get_property("PlayerCameraManager");a=vec(self.controller.call_function("GetActorForwardVector"));b=vec(self.math.call_function("Conv_RotatorToVector",camera.call_function("GetCameraRotation")));self.forward_differs=any(abs(x-y)>.1 for x,y in zip(a,b))
        self.inject(True);self.enter("case")
    def case_tick(self):
        self.inject(False)
        if self.game_time()-self.case_started<1.2:return
        self.recording=False;after=parent.evidence(self.ability)
        self.report["cases"].append(dict(profile=self.profile,kind=self.kind,native_input_used=True,activations=self.activations,native_ammo_cost=self.ammo_before-ammo.ammo(self.item)[0],target_data_entries=self.data_entries,
            parent_target_data_calls=sum(after[key]-self.parent_before[key] for key in ("target_data_calls","fallback_target_data_calls")),parent_fire_timers_or_complete=sum(after[key]-self.parent_before[key] for key in ("fire_timers","fire_complete","fallback_fire_complete")),
            native_firing_cue_entries=len(self.cues),native_cue_geometry_matches=bool(self.cues) and all(row["geometry_matches"] for row in self.cues),native_cue_default_fields_match=bool(self.cues) and all(row["defaults_match"] for row in self.cues),
            controller_forward_differs_from_camera_forward=self.forward_differs,native_location_direction_match=self.pose_matches,native_projectile_spawns=self.spawn_count,native_projectile_transform_matches=self.spawn_matches,native_owner_none_instigator_source=self.spawn_defaults,native_default_exposed_hit=self.spawn_hit_default,
            projectile_destroyed_by_fixture_before_movement_tick=self.projectile_cleanup,native_ability_ended=not self.ability.get_property("bIsActive"),native_callbacks=copy.deepcopy(self.callbacks),native_montage_observed=self.montage_observed,native_cue_observations=copy.deepcopy(self.cues)))
        self.index+=1
        if self.index==len(PLAN):self.finish()
        else:self.start_case()
    def cleanup(self):
        self.recording=False
        if hasattr(self,"actions"):self.inject(False)
        if hasattr(self,"original_montage"):
            if self.ability.get_property("bIsActive"):self.ability.call_function("K2_CancelAbility")
            self.ability.set_property("CharacterFireMontage",self.original_montage);self.ability.set_property("OffsetGCN",self.original_offset);ue.set_mixin_profile(self.ability,self.original_profile)
            counts=parent.evidence(self.ability);self.report["inherited_added_listener_once"]=self.added_initial==1 and counts["added"]+counts["fallback_added"]==1
        if hasattr(self,"original_view_target"):
            self.controller.call_function("SetViewTargetWithBlend",self.original_view_target,0.,0,0.,False)
            self.report["original_view_target_restored"]=self.controller.call_function("GetViewTarget")==self.original_view_target
        for projectile in self.created:
            if not dead(projectile):projectile.call_function("K2_DestroyActor")
        if self.fixture is not None:fixtures.restore(self.controller,self.fixture);self.fixture=None
        if hasattr(self,"original_point"):
            self.pawn.call_function("K2_TeleportTo",self.original_point,self.original_rotation);self.controller.call_function("SetControlRotation",self.original_control);self.movement.call_function("SetMovementMode",self.original_mode,self.original_custom)
            self.report["original_player_pose_control_movement_restored"]=near(vec(self.pawn.get_actor_location()),vec(self.original_point)) and near(rotation(self.pawn.get_actor_rotation()),rotation(self.original_rotation)) and near(rotation(self.controller.call_function("GetControlRotation")),rotation(self.original_control)) and int(self.movement.get_property("MovementMode"))==self.original_mode and int(self.movement.get_property("CustomMovementMode"))==self.original_custom
            self.report["original_inventory_restored"]=capture(self.controller)==self.original["original_model"];self.report["original_player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.player_health
        self.report["all_test_actors_destroyed"]=all(dead(value) for value in self.created)
        for profile,base in self.observers.items():ue.register_mixin_profile(self.cls,profile,base)
        rows=[row for row in ue.get_registered_mixins() if row["target_class"]==self.cls] if hasattr(self,"cls") else []
        self.report["production_profiles_restored"]=len(rows)==1 and all(rows[0]["profiles"][name]["python_class"] is base for name,base in self.observers.items())
        if hasattr(self,"original_cue"):self.report["cue_observer_restored"]=bool(ue.unregister_mixin(self.cue_cls)) and self.cue_cls.get_cdo().find_function("OnBurst")==self.original_cue
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<160.,"native NetShooter ability timeout")
            if self.phase=="ready":self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="weapon-ready":self.weapon_ready()
                elif self.phase=="aim" and time.monotonic()-self.phase_started>=.35:self.start_input()
                elif self.phase=="case":self.case_tick()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_NETSHOOTER_ABILITY_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_NETSHOOTER_ABILITY_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPNetShooterAbilityResult=")),None)
if result:
    selected=Validation
    if '-UEPNetShooterAmmoExhaustion' in sys.argv:
        from .netshooter_ammo_validation import Standalone as selected
    validation=selected(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
