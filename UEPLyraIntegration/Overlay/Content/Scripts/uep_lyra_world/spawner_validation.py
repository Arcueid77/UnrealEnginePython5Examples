"""Actual Lyra Pawn collision/GAS/inventory, native timers and message RPC."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayTagContainer
from uep_runtime import SubscriptionScope
from uep_lyra_hud.ammo_mixin import _stat, MAGAZINE_AMMO
from .inventory_pad_player_validation import Validation as InventoryFixture, path
from .effect_pad_mixin import valid
from . import spawner_mixin as policy
from .spawner_contract import CASES, equal, require, choose_unowned_weapon

class Validation(InventoryFixture):
    def __init__(self,result):
        super().__init__(result)
        self.prepared = False
        self.scopes_created = self.scopes_closed = 0
        self.scope = self.message_scope = self.helper = None
        self.messages, self.rows, self.cooldowns = [], [], {}
        self.reload_added = False
        self.report = {"schema_version":1,"status":"running","error":None,"cases":[],
            "fixture_native_inventory_and_gas_setup":True,"fixture_native_pawn_teleport":True,"original_player_restored":False}
        for flag in ("full_acceptance","network_acceptance","packaged_runtime","handler_called_by_probe","give_weapon_called_by_probe",
                     "timeline_driven_by_probe","cooldown_duration_overridden","ammo_properties_written","inventory_properties_written",
                     "health_properties_written","postgame_native_branch_tested","culture_switch_tested"):
            self.report[flag] = False

    def set_health(self,value):
        current = float(self.health.call_function("GetHealth"))
        if abs(current-value) < .001:
            return
        result = self.bridge.call_function("ApplyAuthorityHealthDelta","spawner."+str(self.index)+"."+str(value),value-current,False)
        require(result.bApplied and abs(float(result.HealthAfter)-value)<.001,"spawner native GAS baseline rejected: "+str(result.Status))

    def begin(self):
        if not self.prepared:
            self.prepared = True
            self.classes = [ue.load_class(value) for value in policy.CLASSES]
            self.bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
            self.health = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            self.original_health = float(self.health.call_function("GetHealth"))
            self.report.update(initial_player_health=self.original_health,maximum_health=float(self.health.call_function("GetMaxHealth")))
            self.report["initial_inventory"] = self.normalized()
            self.weapon_kind = choose_unowned_weapon(self.report["initial_inventory"]["items"])
            self.definition = ue.load_class("/ShooterCore/Weapons/"+self.weapon_kind+"/ID_"+self.weapon_kind+".ID_"+self.weapon_kind+"_C")
            self.report["fresh_weapon_definition"] = path(self.definition)
            self.reload_tags = GameplayTagContainer(GameplayTags=[GameplayTag(TagName="Event.Movement.Reload")])
            self.tag_library = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
            self.helper = ue.new_object(ue.load_class("/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C"),self.pawn)
            self.helper.add_to_root()
            self.message_scope = SubscriptionScope()
            def read(proxy):
                payload,success = self.helper.call_function("ReadFailure",proxy)
                require(success is True,"native spawner failure payload unavailable")
                return payload.clone()
            self.message_scope.listen_gameplay_message(self.pawn,"Ability.UserFacingSimpleActivateFail.Message",
                ue.find_struct("LyraAbilitySimpleFailureMessage"),read,lambda channel,payload:
                self.messages.append({"owner":path(payload.PlayerController),"reason":str(payload.UserFacingReason)}))
        self.name = CASES[self.index//2]
        self.profile = ("BlueprintFallback","Python")[self.index%2]
        self.stats_before, self.messages_before, self.events = policy.snapshot(),len(self.messages),[]
        self.case_health = 75.0 if self.name == CASES[7] else self.report["maximum_health"] if self.name == CASES[8] else self.original_health
        self.set_health(self.case_health)
        self.before_items = len(self.items())
        duplicate = self.name in (CASES[2],CASES[3],CASES[6])
        self.existing = None
        if duplicate:
            self.existing = self.inventory.call_function("AddItemDefinition",self.definition,1)
            slot = int(self.quickbar.call_function("GetNextFreeItemSlot"));require(slot>=0,"spawner duplicate fixture has no slot")
            self.quickbar.call_function("AddItemToSlot",slot,self.existing)
            if self.name == CASES[2]:
                count = int(_stat(self.existing,policy.SPARE));require(count>=5,"native spare default too small")
                self.existing.call_function("RemoveStatTagStack",GameplayTag(TagName=policy.SPARE),5)
        if self.name == CASES[1]:
            for slot,item in enumerate(self.quickbar.call_function("GetSlots")):
                if not valid(item):
                    self.quickbar.call_function("AddItemToSlot",slot,self.inventory.call_function("AddItemDefinition",self.definition,1))
        self.fixture_count = len(self.items())
        self.fixture_inventory = self.normalized()
        self.expected_slot = int(self.quickbar.call_function("GetNextFreeItemSlot"))
        self.initial_spare = int(_stat(self.existing,policy.SPARE)) if valid(self.existing) else None
        center = ue.FVector(self.original_location.x+6000.0+self.index*1100.0,self.original_location.y,self.original_location.z+800.0)
        transform = ue.FTransform();transform.translation = center
        self.cls = self.classes[int(self.name.startswith("ability"))]
        self.pad = self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,self.cls,transform,1,None)
        require(valid(self.pad),"spawner native deferred spawn failed");self.actors.append(self.pad)
        ue.set_mixin_profile(self.pad,self.profile)
        asset = ("/ShooterCore/Items/HealthPickup/WeaponPickupData_Heal_Small.WeaponPickupData_Heal_Small" if self.name.startswith("ability") else
                 "/ShooterCore/Weapons/"+self.weapon_kind+"/WeaponPickupData_"+self.weapon_kind+".WeaponPickupData_"+self.weapon_kind)
        definition = ue.load_object(ue.find_class("LyraWeaponPickupDefinition"),asset)
        self.pad.set_property("WeaponDefinition",definition)
        if self.name in (CASES[1],CASES[6]):
            self.pad.set_property("GiveAmmoForDuplicatedWeapons",False)
        if self.name == CASES[5]:
            self.pad.set_property("IgnorePickUpWhenReload",False)
        self.statics.call_function("FinishSpawningActor",self.pad,transform)
        require(self.pad.get_class() == self.cls and float(self.pad.CoolDownTime) == 10.0,"spawner native class/data default differs")
        if self.name in (CASES[4],CASES[5]):
            require(not ue.call_function_by_class(self.pad,self.cls,policy.RELOAD,{"Pawn":self.pawn})["ReturnValue"],"original player already has reload tag")
            require(self.tag_library.call_function("AddLooseGameplayTags",self.pawn,self.reload_tags,False),"native reload fixture tag rejected")
            self.reload_added = True
            require(ue.call_function_by_class(self.pad,self.cls,policy.RELOAD,{"Pawn":self.pawn})["ReturnValue"],"native reload interface did not observe fixture tag")
        self.constructed = self.construction()
        self.scope = SubscriptionScope();self.scopes_created += 1
        self.scope.bind_event(self.pad.CollisionVolume,"OnComponentBeginOverlap",lambda component,actor,*rest:self.events.append("begin") if actor == self.pawn else None)
        self.scope.bind_event(self.pad.CollisionVolume,"OnComponentEndOverlap",lambda component,actor,*rest:self.events.append("end") if actor == self.pawn else None)
        self.start_time = float(self.statics.call_function("GetTimeSeconds",self.world))
        require(self.pawn.set_actor_location(self.pad.CollisionVolume.call_function("K2_GetComponentLocation")),"native spawner entry rejected")
        self.enter("overlap")

    def niagara(self,component,name):
        result = ue.call_function_by_class(component,ue.find_class("NiagaraComponent"),"GetVariableFloat",{"InVariableName":name})
        require(result["bIsValid"] is True,"native Niagara parameter missing: "+name)
        return float(result["ReturnValue"])

    def construction(self):
        color = self.pad.MID_Pad.call_function("K2_GetVectorParameterValue","Color")
        location = self.pad.WeaponMesh.get_property("RelativeLocation")
        return {"glow":float(self.pad.MID_Pad.call_function("K2_GetScalarParameterValue","Intensity")),
            "color":[float(getattr(color,key)) for key in ("r","g","b","a")],
            "light_intensity":float(self.pad.PointLight.get_property("Intensity")),
            "radius":float(self.pad.PointLight.get_property("AttenuationRadius")),
            "offset":[float(getattr(location,key)) for key in ("x","y","z")],
            "mesh_collision":int(self.pad.WeaponMesh.call_function("GetCollisionEnabled")),
            "loading_lifetime":self.niagara(self.pad.NS_GunPad_Loading,"LifeTime")}

    def sample_pickup(self):
        successful = self.name not in (CASES[1],CASES[3],CASES[8])
        self.report["current_trial"] = {"name":self.name,"profile":self.profile,"events":list(self.events),
            "inventory":self.normalized(),"available":bool(self.pad.bIsWeaponAvailable),"messages":copy.deepcopy(self.messages[self.messages_before:]),
            "policy":policy.snapshot(),"weapon_definition":path(self.pad.WeaponDefinition)}
        require(self.events == ["begin"],"spawner physical begin missing/duplicated")
        require(bool(self.pad.bIsWeaponAvailable) is (not successful),"native spawner success/availability differs")
        self.value = {"construction":self.constructed,"cooldown_duration":float(self.pad.CoolDownTime),
            "available_after_pickup":bool(self.pad.bIsWeaponAvailable),"item_delta":len(self.items())-self.fixture_count,
            "active_slot":int(self.quickbar.call_function("GetActiveSlotIndex")),"health":float(self.health.call_function("GetHealth")),
            "failure_messages":[row["reason"] for row in self.messages[self.messages_before:]],
            "failure_owner_matches":all(row["owner"] == path(self.controller) for row in self.messages[self.messages_before:]),
            "cooldown_completed":False,"curve_matches":False,"respawn_light":False}
        if self.name == CASES[2]:
            current = int(_stat(self.existing,policy.SPARE))
            require(current == self.initial_spare+5,"spawner native spare refill differs")
            self.value["spare_delta"] = current-self.initial_spare
        if self.name in (CASES[0],CASES[4],CASES[5],CASES[6]):
            require(self.value["item_delta"] == 1,"native spawner did not grant exactly one item")
            expected_active = self.original["active"] if self.name == CASES[4] else self.expected_slot
            require(self.value["active_slot"] == expected_active,"native spawner reload/select policy differs")
        elif self.name in (CASES[1],CASES[3],CASES[8]):
            require(self.normalized() == self.fixture_inventory,"rejected spawner changed inventory")
        if self.name == CASES[7]:
            require(abs(self.value["health"]-100.0)<.001,"native ability spawner did not heal 75 -> 100")
        require(self.pawn.set_actor_location(ue.FVector(self.pad.get_actor_location().x+500.0,self.pad.get_actor_location().y,self.pad.get_actor_location().z)),"spawner native leave rejected")
        require(self.events == ["begin","end"],"spawner native leave missing/duplicated")
        if self.name == CASES[0]:
            self.item = self.quickbar.call_function("GetActiveSlotItem")
            equipment = self.quickbar.get_property("EquippedItem")
            require(valid(equipment) and equipment.call_function("GetInstigator") == self.item,"spawner native equipment instigator differs")
            self.value.update(native_equipment_matches=True,magazine_before=int(_stat(self.item,MAGAZINE_AMMO)))
            self.enter("fire")
        elif self.name == CASES[7]:
            self.enter("cooldown")
        else:
            self.side_done()

    def side_done(self):
        require(not policy.snapshot()["errors"],"spawner Python policy failed: "+repr(policy.snapshot()["errors"]))
        if self.reload_added:
            require(self.tag_library.call_function("RemoveLooseGameplayTags",self.pawn,self.reload_tags,False),"native reload tag removal failed")
            self.reload_added = False
        self.value["reload_tag_removed"] = not ue.call_function_by_class(self.pad,self.cls,policy.RELOAD,{"Pawn":self.pawn})["ReturnValue"]
        self.scope.close();self.scopes_closed += 1
        self.pad.actor_destroy()
        self.rollback();self.value["fixture_inventory_rollback"] = self.fingerprint() == self.original
        self.value["physical_events"] = list(self.events)
        self.rows.append(copy.deepcopy(self.value))
        counters = {key:value-self.stats_before[key] for key,value in policy.snapshot().items() if key != "errors"}
        if self.index%2:
            require(equal(self.rows[0],self.rows[1]),"spawner BP/Python differs: "+self.name+" "+repr(self.rows))
            self.report["cases"].append({"name":self.name,"passed":True,"same_class":True,"blueprint":self.rows[0],"python":self.rows[1],
                "python_counters":counters,"observed_cooldowns":copy.deepcopy(self.cooldowns)})
            ue.log("UEP_SPAWNER_CASE_PASSED "+self.name)
            self.rows,self.cooldowns = [],{}
        self.index += 1
        if self.index == len(CASES)*2:
            self.finish()
        else:
            self.begin()

    def tick(self,delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started<240,"spawner timeout: "+self.phase)
            if self.phase == "ready":
                self.ready()
            elif self.phase == "overlap" and time.monotonic()-self.phase_started>.15:
                self.sample_pickup()
            elif self.phase == "fire":
                current = int(_stat(self.item,MAGAZINE_AMMO))
                if current < self.value["magazine_before"]:
                    self.value["magazine_after"] = current;self.input(False);self.enter("cooldown")
                else:
                    require(time.monotonic()-self.phase_started<5.0,"native spawner newly granted weapon did not fire")
                    self.input((time.monotonic()-self.phase_started)%.30<.10)
            elif self.phase == "cooldown" and self.pad.bIsWeaponAvailable:
                self.cooldowns[self.profile] = float(self.statics.call_function("GetTimeSeconds",self.world))-self.start_time
                self.value["cooldown_completed"] = True;self.enter("respawn-curve")
            elif self.phase == "respawn-curve" and time.monotonic()-self.phase_started>.2:
                position = float(self.pad.Timeline_Spawn.call_function("GetPlaybackPosition"))
                bp = ue.load_object(ue.find_class("Blueprint"),policy.CLASSES[0][:-2])
                expected = float(bp.Timelines[0].FloatTracks[0].CurveFloat.call_function("GetFloatValue",position))
                actual = self.niagara(self.pad.NS_GunPad,"Luminosity")
                self.value["curve_matches"] = abs(actual-expected)<.002
                self.value["respawn_light"] = bool(self.pad.PointLight.get_property("bVisible"))
                require(self.value["curve_matches"] and self.value["respawn_light"],"native spawner curve/respawn visuals differ")
                self.side_done()
            return not self.finished
        except Exception:
            self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:
            return
        self.finished = True
        try:
            if self.scope is not None and not self.scope.closed:
                self.scope.close();self.scopes_closed += 1
            if self.reload_added:
                self.tag_library.call_function("RemoveLooseGameplayTags",self.pawn,self.reload_tags,False);self.reload_added=False
            if self.message_scope is not None:
                self.message_scope.close()
            if self.helper is not None:
                self.helper.remove_from_root();self.helper=None
            if self.original_items is not None:
                self.rollback();self.set_health(self.original_health)
                self.pawn.set_actor_location(self.original_location)
                self.movement.call_function("StopMovementImmediately")
                self.movement.call_function("SetMovementMode",self.original_mode,self.original_custom_mode)
                self.controller.call_function("SetControlRotation",self.original_rotation)
                location,rotation = self.pawn.get_actor_location(),self.controller.call_function("GetControlRotation")
                restore = {"inventory_identity_equal":self.fingerprint() == self.original,
                    "position_error":max(abs(getattr(location,k)-getattr(self.original_location,k)) for k in ("x","y","z")),
                    "aim_error":max(abs(getattr(rotation,k)-getattr(self.original_rotation,k)) for k in ("roll","pitch","yaw")),
                    "health":float(self.health.call_function("GetHealth")),"expected_health":self.original_health,
                    "movement":[int(self.movement.MovementMode),int(self.movement.CustomMovementMode)],
                    "expected_movement":[self.original_mode,self.original_custom_mode]}
                self.report["player_restore"] = restore
                self.report["original_player_restored"] = (restore["inventory_identity_equal"] and restore["position_error"]<.01 and restore["aim_error"]<.01 and
                    restore["movement"] == restore["expected_movement"] and abs(restore["health"]-self.original_health)<.01)
            for actor in self.actors:
                if valid(actor):
                    actor.actor_destroy()
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error,actors_created=len(self.actors),
            actors_destroyed=sum(not valid(actor) for actor in self.actors),collision_scopes_created=self.scopes_created,
            collision_scopes_closed=self.scopes_closed,message_scope_closed=self.message_scope is None or self.message_scope.closed,
            message_helper_unrooted=self.helper is None,elapsed_seconds=time.monotonic()-self.started)
        self.result.write_text(json.dumps(self.report,indent=2),encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_SPAWNER_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                from .spawner_contract import validate
                self.report["status"]="passed";validate(self.report)
            except Exception:
                self.report.update(status="failed",error=traceback.format_exc())
        self.result.write_text(json.dumps(self.report,indent=2),encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_SPAWNER_SHUTDOWN_"+self.report["status"].upper())

result = next(v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPSpawnerResult="))
validation=Validation(result)
atexit.register(validation.finalize)
ticker=ue.add_ticker(validation.tick)
