"""Existing original Lyra level spawners: natural timers and two real owners."""
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer
from uep_runtime import SubscriptionScope
from uep_lyra_hud import state as hud_state,weapon_observer,ability_failure_mixin as failure
from uep_lyra_hud.shutdown_validation import defer_until_shutdown
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_weapon_input import aim_above_players
from .inventory_pad_network_validation import InventoryNetwork
from .effect_pad_network_validation import PadNetworkProbe
from .inventory_pad_network_state import capture,services,path
from .spawner_contract import CASES,choose_unowned_weapon
from .spawner_network_protocol import PLAN,PEERS,require,near,baseline_ready,expected_inventory,validate_ack,validate_cases
from . import spawner_mixin as policy
from .effect_pad_mixin import valid

class SpawnerNetwork(InventoryNetwork):
    def __init__(self):
        super().__init__()
        self.timeout_seconds=620
        self.current_visual=None
        self.pads,self.saved_pads,self.client_saved_profiles={},{},{}
        self.players_restored=False
        self.scopes_created=self.scopes_closed=0
        self.reload_added=False
        self.failure_count,self.failure_text=0,None
        self.original_health={}

    def pad_state(self,pad):
        return {"name":pad.get_name(),"class":path(pad.get_class()),"profile":ue.get_mixin_profile(pad),
            "available":bool(pad.bIsWeaponAvailable),"light":bool(pad.PointLight.get_property("bVisible")),
            "weapon_visible":bool(pad.WeaponMesh.get_property("bVisible"))}

    def _status(self):
        result=super()._status()
        result.update(health_visual=copy.deepcopy(self.current_visual),failure_count=self.failure_count,
            failure_text=self.failure_text,failure_widget_count=getattr(self,"failure_widget_count",0),spawner_stage=self.stage,spawner_case=self.index)
        if self.peer!="server":result["ready"]=result["ready"] and self.current_visual is not None
        return result

    def health_values(self):
        return {peer:float(owner["pawn"].get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth"))
                for peer,owner in self.owners.items()}

    def set_health(self,peer,value):
        current=self.health_values()[peer]
        if near(current,value):return
        result=self.bridge.call_function("ApplyAuthorityHealthDeltaToPlayer","spawner."+str(self.index)+"."+peer+"."+str(value),
            value-current,self.roster[peer]["player_token"])
        require(result.bApplied and near(float(result.HealthAfter),value),"native spawner GAS setup rejected: "+str(result.Status))

    def select_level_pads(self):
        self.classes=[ue.load_class(value) for value in policy.CLASSES]
        for kind,cls in zip(("weapon","ability"),self.classes):
            actors,=self.gameplay_statics.call_function("GetAllActorsOfClass",self.world,cls)
            candidates=[]
            for actor in actors:
                if actor.get_class()!=cls or not valid(actor.WeaponDefinition) or not actor.bIsWeaponAvailable:continue
                definition=actor.WeaponDefinition
                matching=(definition.InventoryItemDefinition==self.definition if kind=="weapon" else
                    actor.GameplayEffectToApply==cls.get_cdo().GameplayEffectToApply and "Heal_Small" in path(definition))
                pawns=ue.call_function_by_class(actor,ue.find_class("Actor"),"GetOverlappingActors",
                    {"ClassFilter":ue.find_class("Pawn")})["OverlappingActors"]
                if matching and float(actor.CoolDownTime)==10.0 and not pawns:candidates.append(actor)
            require(candidates,"no unoccupied original level spawner for "+kind)
            # A stable fixture selection, NOT gameplay owner inference.
            actor=sorted(candidates,key=lambda value:value.get_path_name())[0]
            self.pads[kind]=actor
            self.saved_pads[kind]={"name":actor.get_name(),"class":path(cls),"profile":ue.get_mixin_profile(actor),
                "give_ammo":bool(actor.GiveAmmoForDuplicatedWeapons),"ignore_reload":bool(actor.IgnorePickUpWhenReload),
                "definition":path(actor.WeaponDefinition),"replicates":bool(actor.get_property("bReplicates"))}

    def prepare(self,roster):
        self.roster=copy.deepcopy(roster)
        if not self.owners:
            for peer,row in roster.items():
                controller,pawn=ue.find_object(row["controller_path"]),ue.find_object(row["pawn_path"])
                movement=pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
                self.owners[peer]={"controller":controller,"pawn":pawn,"movement":movement,"location":pawn.get_actor_location(),
                    "mode":int(movement.MovementMode),"custom_mode":int(movement.CustomMovementMode),"fingerprint":self.fingerprint(controller)}
                self.original_health[peer]=float(row["health"])
                movement.call_function("StopMovementImmediately");movement.call_function("DisableMovement")
            self.pristine={peer:capture(owner["controller"]) for peer,owner in self.owners.items()}
            require(all(self.pristine.values()),"native pristine spawner inventories unavailable")
            kind=choose_unowned_weapon([value for state in self.pristine.values() for value in state["items"]])
            self.definition=ue.load_class("/ShooterCore/Weapons/"+kind+"/ID_"+kind+".ID_"+kind+"_C")
            self.reload_tags=GameplayTagContainer(GameplayTags=[GameplayTag(TagName="Event.Movement.Reload")])
            self.tag_library=ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
            self.select_level_pads()
        target,name,profile=PLAN[self.index]
        self.pad=self.pads["ability" if name.startswith("ability") else "weapon"]
        require(valid(self.pad) and self.pad.bIsWeaponAvailable,"original level pad unavailable before trial")
        ue.set_mixin_profile(self.pad,profile)
        self.pad.set_property("GiveAmmoForDuplicatedWeapons",name not in (CASES[1],CASES[6]))
        self.pad.set_property("IgnorePickUpWhenReload",name!=CASES[5])
        owner=self.owners[target];inventory,quickbar=services(owner["controller"])
        if name in (CASES[2],CASES[3],CASES[6]):
            item=inventory.call_function("AddItemDefinition",self.definition,1)
            slot=int(quickbar.call_function("GetNextFreeItemSlot"));require(slot>=0,"spawner fixture duplicate has no slot")
            quickbar.call_function("AddItemToSlot",slot,item);quickbar.call_function("SetActiveSlotIndex",slot)
            if name==CASES[2]:item.call_function("RemoveStatTagStack",GameplayTag(TagName=policy.SPARE),5)
        if name==CASES[1]:
            for slot,item in enumerate(quickbar.call_function("GetSlots")):
                if not valid(item):quickbar.call_function("AddItemToSlot",slot,inventory.call_function("AddItemDefinition",self.definition,1))
        if name in (CASES[4],CASES[5]):
            require(self.tag_library.call_function("AddLooseGameplayTags",owner["pawn"],self.reload_tags,False),"native spawner reload tag setup failed")
            self.reload_added=True
        self.set_health(target,75.0 if name==CASES[7] else 100.0 if name==CASES[8] else self.original_health[target])
        prepared={peer:capture(row["controller"]) for peer,row in self.owners.items()}
        if not all(prepared.values()):
            # Wait for native equipment construction, without repeating setup.
            self.stage="equipment-ready";self.phase_started=time.monotonic();return
        self.prepared_ready(prepared)

    def prepared_ready(self,prepared):
        target,name,profile=PLAN[self.index]
        statuses={peer:self._peer_status(peer) for peer in PEERS}
        require(all(statuses.values()),"spawner current peer snapshots missing")
        self.current={"run_id":self.run_id,"case_index":self.index,"target":target,"scenario":name,"profile":profile,
            "pad_name":self.pad.get_name(),"pad_class":path(self.pad.get_class()),"pad_replicates":bool(self.pad.get_property("bReplicates")),
            "cooldown_duration":float(self.pad.CoolDownTime),"prepared":copy.deepcopy(prepared),"original":copy.deepcopy(self.pristine),
            "prepared_health":self.health_values(),"original_health":copy.deepcopy(self.original_health),"roster":copy.deepcopy(self.roster),
            "client_pawns":{peer:statuses[peer]["player"]["pawn_path"] for peer in PEERS},
            "client_worlds":{peer:statuses[peer]["player"]["world_token"] for peer in PEERS},
            "failure_baseline":{peer:statuses[peer]["failure_count"] for peer in PEERS},"acks":{},
            "success":name not in (CASES[1],CASES[3],CASES[8])}
        self.prepared_at=float(self.gameplay_statics.call_function("GetTimeSeconds",self.world))
        self.publish("prepared");self.stage="prepared-ack";self.phase_started=time.monotonic()

    def publish(self,stage):atomic_write(self.root/"spawner-command.json",dict(self.current,stage=stage))

    def collect(self,stage):
        rows={peer:read_json(self.root/"spawner-acks"/(str(self.index)+"-"+stage+"-"+peer+".json")) for peer in PEERS}
        if not all(rows.values()):return False
        for peer in PEERS:validate_ack(self.current,rows[peer],peer,stage)
        self.current["acks"][stage]=rows
        return True

    def trigger(self):
        pawn=self.owners[self.current["target"]]["pawn"]
        self.stats_before,self.physical=policy.snapshot(),[]
        self.scope=SubscriptionScope();self.scopes_created+=1
        self.scope.bind_event(self.pad.CollisionVolume,"OnComponentBeginOverlap",lambda component,actor,*rest:self.physical.append("begin") if actor==pawn else None)
        self.scope.bind_event(self.pad.CollisionVolume,"OnComponentEndOverlap",lambda component,actor,*rest:self.physical.append("end") if actor==pawn else None)
        self.cooldown_started=float(self.gameplay_statics.call_function("GetTimeSeconds",self.world))
        require(pawn.set_actor_location(self.pad.CollisionVolume.call_function("K2_GetComponentLocation")),"native level spawner entry failed")
        self.stage,self.stage_started="overlap",time.monotonic()

    def server_tick(self):
        if self.stage=="release":
            release=read_json(self.root/"release.json")
            if release is not None:
                require(release["run_id"]==self.run_id,"foreign spawner release");self.finish()
            return
        if self.stage=="complete-ack":
            if all(read_json(self.root/("ready-"+p+".json")) is not None for p in PEERS):
                self.stage="release";atomic_write(self.root/"ready-server.json",{"run_id":self.run_id})
            return
        if self.stage=="ready":
            roster=self._roster(PEERS)
            if roster is not None:self.prepare(roster)
        elif self.stage=="equipment-ready":
            prepared={peer:capture(row["controller"]) for peer,row in self.owners.items()}
            if all(prepared.values()):self.prepared_ready(prepared)
        elif self.stage=="prepared-ack" and self.collect("prepared"):
            # ResetCoolDown schedules a native overlap recheck. The previous
            # trial's Pawn is outside; let that real callback finish before
            # entering a new trial. Do not weaken one-producer/message gates.
            now=float(self.gameplay_statics.call_function("GetTimeSeconds",self.world))
            if now-self.prepared_at<float(self.pad.CheckExistingOverlapDelay)+.1:return
            self.trigger()
        elif self.stage=="overlap" and time.monotonic()-self.stage_started>.2:
            expected={peer:capture(row["controller"]) for peer,row in self.owners.items()}
            if not all(expected.values()):return
            require(self.physical==["begin"] and bool(self.pad.bIsWeaponAvailable) is (not self.current["success"]),"native spawner collision/availability differs")
            self.current.update(expected=expected,expected_health=self.health_values())
            require(not policy.snapshot()["errors"],"Python spawner error: "+repr(policy.snapshot()["errors"]))
            self.publish("observed");self.stage="observed-ack"
        elif self.stage=="observed-ack" and self.collect("observed"):
            after={peer:capture(row["controller"]) for peer,row in self.owners.items()}
            if not all(after[p]==self.current["acks"]["observed"][p]["inventory"] for p in PEERS):return
            self.current["after"]=after
            pawn=self.owners[self.current["target"]]["pawn"];location=self.pad.get_actor_location()
            require(pawn.set_actor_location(ue.FVector(location.x+500.0,location.y,location.z+100.0)),"native spawner leave failed")
            require(self.physical==["begin","end"],"native spawner overlap lifecycle differs")
            self.scope.close();self.scopes_closed+=1
            self.stage="cooldown"
        elif self.stage=="cooldown" and self.pad.bIsWeaponAvailable:
            self.current.update(cooldown_seconds=float(self.gameplay_statics.call_function("GetTimeSeconds",self.world))-self.cooldown_started,
                physical_events=list(self.physical),fixture_scope_closed=self.scope.closed,original_level_actor_preserved=valid(self.pad),
                python_gives=(policy.snapshot()["ability_gives"]-self.stats_before["ability_gives"] if self.current["scenario"].startswith("ability") else
                              policy.snapshot()["weapon_gives"]-self.stats_before["weapon_gives"]),
                python_failures=policy.snapshot()["failures"]-self.stats_before["failures"])
            key="fallback_ability_gives" if self.current["scenario"].startswith("ability") else "fallback_weapon_gives"
            self.current["fallback_gives"]=policy.snapshot()[key]-self.stats_before[key]
            if self.reload_added:
                require(self.tag_library.call_function("RemoveLooseGameplayTags",self.owners[self.current["target"]]["pawn"],self.reload_tags,False),"native reload tag cleanup failed")
                self.reload_added=False
            self.rollback()
            for peer in PEERS:self.set_health(peer,self.original_health[peer])
            self.publish("restored");self.stage="restored-ack"
        elif self.stage=="restored-ack" and self.collect("restored"):
            self.history.append(copy.deepcopy(self.current));ue.log("UEP_SPAWNER_NETWORK_CASE_PASSED "+str(self.index))
            self.index+=1;self.phase_started=time.monotonic()
            if self.index==len(PLAN):
                validate_cases(self.history);self.restore()
                atomic_write(self.root/"spawner-command.json",{"run_id":self.run_id,"stage":"complete","original":self.pristine,
                    "health":self.original_health,"positions":self.restore_positions,"modes":self.restore_modes})
                self.stage="complete-ack"
            else:self.stage="ready"

    def local_pad(self,packet):
        cls=ue.load_class(packet["pad_class"])
        actors,=self.gameplay_statics.call_function("GetAllActorsOfClass",self.world,cls)
        matches=[actor for actor in actors if actor.get_name()==packet["pad_name"] and actor.get_class()==cls]
        require(len(matches)==1,"original replicated level spawner missing/ambiguous")
        return matches[0]

    def client_tick(self):
        packet=read_json(self.root/"spawner-command.json")
        if packet is None or self.local_inventory is None or self.current_visual is None:return
        require(packet["run_id"]==self.run_id,"foreign spawner command")
        if packet["stage"]=="complete":
            if self.players_restored:return
            pawn=ue.find_object(self.player["pawn_path"]);location=pawn.get_actor_location()
            expected=packet["positions"][self.peer]
            movement=pawn.get_component_by_type(ue.find_class("CharacterMovementComponent"))
            if (self.local_inventory==packet["original"][self.peer] and near(self.player["health"],packet["health"][self.peer]) and
                max(abs(getattr(location,k)-value) for k,value in zip(("x","y","z"),expected))<10.0 and int(movement.MovementMode)==packet["modes"][self.peer]):
                require(len(self.history)==len(PLAN),"spawner completed before client matrix")
                for actor,profile in self.client_saved_profiles.values():
                    ue.set_mixin_profile(actor,profile) if profile is not None else ue.clear_mixin_profile(actor)
                controller=ue.find_object(self.player["controller_path"])
                self.input(False);controller.call_function("SetControlRotation",self.original_aim)
                actual=controller.call_function("GetControlRotation")
                require(max(abs(getattr(actual,k)-getattr(self.original_aim,k)) for k in ("pitch","yaw","roll"))<.01,"native spawner client aim restore failed")
                self.players_restored=True;atomic_write(self.root/("ready-"+self.peer+".json"),{"run_id":self.run_id})
            return
        index,stage=packet["case_index"],packet["stage"]
        if index<=self.last_ack:return
        if self.seen!=index:self.seen,self.input_frames,self.fire_started=index,0,time.monotonic()
        pad=self.local_pad(packet)
        if pad.get_name() not in self.client_saved_profiles:self.client_saved_profiles[pad.get_name()]=(pad,ue.get_mixin_profile(pad))
        if ue.get_mixin_profile(pad)!=packet["profile"]:ue.set_mixin_profile(pad,packet["profile"])
        if stage=="observed" and packet["target"]==self.peer and packet["scenario"]==CASES[0]:
            desired=expected_inventory(packet,self.peer)
            if self.local_inventory!=desired:
                if self.local_inventory==packet["expected"][self.peer]:
                    require(time.monotonic()-self.fire_started<20,"native spawner client weapon did not fire")
                    aim_above_players(ue.find_object(self.player["controller_path"]))
                    self.input((time.monotonic()-self.fire_started)%.30<.10);self.input_frames+=1
                return
        self.input(False)
        ack={"run_id":self.run_id,"case_index":index,"peer":self.peer,"stage":stage,"player":copy.deepcopy(self.player),
            "inventory":copy.deepcopy(self.local_inventory),"health_visual":copy.deepcopy(self.current_visual),"pad":self.pad_state(pad),
            "failure_delta":self.failure_count-packet["failure_baseline"][self.peer],"failure_text":self.failure_text,"input_frames":self.input_frames}
        try:validate_ack(packet,ack,self.peer,stage)
        except RuntimeError:return
        atomic_write(self.root/"spawner-acks"/(str(index)+"-"+stage+"-"+self.peer+".json"),ack)
        if stage=="restored":self.history.append(ack);self.last_ack=index

    def restore(self):
        if self.peer!="server" or self.players_restored:return
        self.scope.close()
        if self.reload_added:
            self.tag_library.call_function("RemoveLooseGameplayTags",self.owners[PLAN[self.index][0]]["pawn"],self.reload_tags,False);self.reload_added=False
        self.rollback();self.restore_positions,self.restore_modes,self.restored_players={},{},{}
        for peer,row in self.owners.items():
            self.set_health(peer,self.original_health[peer]);row["movement"].call_function("StopMovementImmediately")
            row["pawn"].set_actor_location(row["location"]);row["movement"].call_function("SetMovementMode",row["mode"],row["custom_mode"])
            actual=row["pawn"].get_actor_location()
            require(max(abs(getattr(actual,k)-getattr(row["location"],k)) for k in ("x","y","z"))<.01 and
                    int(row["movement"].MovementMode)==row["mode"],"native spawner player restore postcondition differs")
            self.restored_players[peer]=True;self.restore_positions[peer]=[float(getattr(actual,k)) for k in ("x","y","z")];self.restore_modes[peer]=row["mode"]
        for kind,pad in self.pads.items():
            saved=self.saved_pads[kind]
            pad.set_property("GiveAmmoForDuplicatedWeapons",saved["give_ammo"]);pad.set_property("IgnorePickUpWhenReload",saved["ignore_reload"])
            ue.set_mixin_profile(pad,saved["profile"]) if saved["profile"] is not None else ue.clear_mixin_profile(pad)
            require(valid(pad) and path(pad.WeaponDefinition)==saved["definition"] and pad.bIsWeaponAvailable and
                    bool(pad.get_property("bReplicates"))==saved["replicates"] and
                    bool(pad.GiveAmmoForDuplicatedWeapons)==saved["give_ammo"] and bool(pad.IgnorePickUpWhenReload)==saved["ignore_reload"] and
                    (saved["profile"] is None or ue.get_mixin_profile(pad)==saved["profile"]),"original level spawner not preserved/restored")
        self.players_restored=True

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.restore()
        except Exception:error=(error or "")+traceback.format_exc()
        report={"schema_version":1,"status":"failed" if error else "passed","error":error,"run_id":self.run_id,"peer":self.peer,
            "cases":self.history,"players_restored":self.players_restored,"scopes_created":self.scopes_created,"scopes_closed":self.scopes_closed,
            "original_level_actors_used":True,"fixture_actors_created":0,"fixture_actors_destroyed":0,"policy":policy.snapshot(),
            "native_players_restored":getattr(self,"restored_players",{}),"level_spawners":self.saved_pads,
            "hud":hud_state.snapshot(),"weapon_observer":weapon_observer.snapshot(),"gameplay_slice":{"enabled":False},"shutdown":None,
            "elapsed_seconds":self._wall_elapsed(),"fixture_native_inventory_gas_tag_and_teleport":True}
        for flag in ("full_acceptance","packaged_runtime","handler_called_by_probe","launch_called_by_probe","give_weapon_called_by_probe",
                     "timer_or_timeline_driven_by_probe","cooldown_duration_overridden","pad_replication_forced","ammo_properties_written",
                     "inventory_properties_written","health_properties_written","physical_client_input_tested","construction_profile_parity_tested",
                     "cue_audio_visual_parity_tested","culture_switch_tested"):
            report[flag]=False
        if error is None:defer_until_shutdown(report,self.result_path)
        atomic_write(Path(self.result_path),report)
        (ue.log_error if error else ue.log)("UEP_SPAWNER_NETWORK_"+("FAILED "+error if error else "PASSED"))
        self.shutdown_binding();self._request_quit()

    def tick(self,delta):
        if self.finished:return False
        try:
            now=time.monotonic();require(self._wall_elapsed()<self.timeout_seconds,"spawner network total timeout")
            if now<self.next_tick:return True
            self.next_tick=now+.03
            world=self._game_world()
            if not valid(world) or not self._attach(world):return True
            self.peer_frame_snapshots.clear()
            self.rows=[self._snapshot_report(row) for row in self.bridge.call_function("CapturePlayerSnapshots")]
            self.player=self.rows[0] if self.peer!="server" and len(self.rows)==1 else None
            if self.peer=="server":self._isolate_bot_combat()
            elif self.player is not None and self._player_ready(self.player):
                controller=ue.find_object(self.player["controller_path"]);self.local_inventory=capture(controller)
                if self.original_aim is None and self.local_inventory is not None:self.original_aim=controller.call_function("GetControlRotation")
                PadNetworkProbe.visual(self)
                state=failure.snapshot();self.failure_count=state["messages"]
                self.failure_widget_count=state["active_count"]
                if len(state["active_widgets"])==1:
                    widget=ue.find_object(state["active_widgets"][0]);self.failure_text=str(widget.FailureReasonTextWidget.call_function("GetText"))
            atomic_write(self.root/"status"/(self.peer+".json"),self._status())
            if self.peer=="server":
                require(now-self.phase_started<(300 if not self.owners else 100),"spawner network case timeout: "+str(self.index)+"/"+self.stage)
                self.server_tick()
            else:
                release=read_json(self.root/"release.json")
                if release is not None:
                    require(release["run_id"]==self.run_id and self.players_restored,"premature spawner release");self.finish()
                else:self.client_tick()
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

runtime=SpawnerNetwork()
ticker=ue.add_ticker(runtime.tick)
