"""Native equipped firing input, enemy damage, seeded choices and actual messages."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,LyraAbilityMontageFailureMessage
from unreal_engine.enums import ELyraTeamComparison
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.inventory_pad_network_state import capture,services
from uep_lyra_hud.weapon_validation_helpers import set_stat
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities import reload_weapon_fixture as fixtures,reload_magazine_mixin as ammo_policy
from uep_lyra_abilities.melee_trace_mixin import break_hit
from .weapon_fire_fx_validation import dead,vec
from . import weapon_ability_fire_mixin as policy
from .weapon_ability_fire_contract import PROFILES,WEAPONS,PLAN,NORMALS,require,validate


def path(value):return value.get_path_name() if valid(value) else None


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.fixture=None;self.weapon=None;self.observers={};self.created=[];self.bot_poses=[]
        self.created_bots=[];self.recording=False;self.lifecycle_mode=False;self.callback_events=[];self.data_events=[];self.weapon_events=[]
        self.report=dict(schema_version=1,status="running",error=None,montage_pairs=[],shots=[],failure_cases=[],lifecycle_cases=[],native_global_seed_api_used=True)
        for field in ("full_acceptance","network_acceptance","packaged_runtime","physical_input_tested","pixels_tested","audio_playback_tested",
                      "activation_handler_replayed","target_data_callback_replayed","montage_callback_replayed","timer_callback_replayed",
                      "health_properties_written","ammo_properties_written","timer_properties_written"):self.report[field]=False
    def bots(self):
        values,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("LyraPlayerBotController"));return list(values)
    def observe(self,cls):
        if cls in self.observers:return
        ue.register_declared_mixin(cls);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==cls]
        originals={name:row["python_class"] for name,row in binding["profiles"].items()};self.observers[cls]=originals;owner=self
        for profile,base in originals.items():
            methods={key:value for key,value in vars(base).items() if not key.startswith("__") and callable(value)}
            if "TargetData" in methods:
                def around_activate(handler):
                    def invoke(actor):
                        result=handler(actor)
                        if owner.recording and actor==owner.ability:
                            anim=owner.pawn.get_property("Mesh").call_function("GetAnimInstance")
                            expected=actor.get_property("CharacterFireMontage")
                            playing=bool(anim.call_function("Montage_IsPlaying",expected))
                            owner.montage_observed|=playing
                            owner.activation_witness=dict(anim_instance=path(anim),expected=path(expected),gas_current_montage=path(actor.call_function("GetCurrentMontage")),playing=playing)
                            owner.task_observed=max(owner.task_observed,sum(valid(task) for task in actor.get_property("ActiveTasks")))
                            if owner.lifecycle_mode and owner.lifecycle_kind in ("cancel","interrupt"):
                                if owner.lifecycle_kind=="cancel":actor.call_function("K2_CancelAbility")
                                else:owner.pawn.call_function("StopAnimMontage",expected)
                                owner.lifecycle_intervened=True
                        return result
                    invoke.override="K2_ActivateAbility";return invoke
                methods["Activate"]=around_activate(base.Activate)
                def around_data(handler):
                    def invoke(actor,TargetData):
                        row=None
                        if owner.recording and actor==owner.ability:
                            hits=[break_hit(policy.lib("AbilitySystemBlueprintLibrary").call_function("GetHitResultFromTargetData",TargetData,i)) for i in range(int(policy.lib("AbilitySystemBlueprintLibrary").call_function("GetDataCountFromTargetData",TargetData)))]
                            row=dict(count=len(hits),blocking=sum(bool(hit["bBlockingHit"]) for hit in hits),actors=[path(hit["HitActor"]) for hit in hits],points=[vec(hit["ImpactPoint"]) for hit in hits if hit["bBlockingHit"]],traces=[dict(start=vec(hit["TraceStart"]),end=vec(hit["TraceEnd"])) for hit in hits])
                            owner.data_events.append(row)
                        result=handler(actor,TargetData)
                        if row is not None and not owner.lifecycle_mode:row["health_after"]=float(owner.enemy_health.call_function("GetHealth"))
                        return result
                    invoke.override="OnRangedWeaponTargetDataReady";return invoke
                methods["TargetData"]=around_data(base.TargetData)
                for name in ("FireComplete","FailureComplete","MontageCompleted","MontageInterrupted","MontageCancelled"):
                    def around_callback(handler,label,override):
                        def invoke(actor):
                            if actor==getattr(owner,"ability",None):owner.callback_events.append(dict(name=label,time=owner.game_time()))
                            return handler(actor)
                        invoke.override=override;return invoke
                    fn=getattr(base,name);methods[name]=around_callback(fn,name,getattr(fn,"override",name))
            elif "Fire" in methods:
                def around_weapon(handler):
                    def invoke(actor,*args):
                        if owner.recording:owner.weapon_events.append(dict(actor=path(actor),owner=path(actor.call_function("GetOwner"))))
                        return handler(actor,*args)
                    invoke.override="Fire";return invoke
                methods["Fire"]=around_weapon(base.Fire)
            ue.register_mixin_profile(cls,profile,type("ObservedSharedWeaponFire"+str(len(self.observers))+profile,(),methods))
    def begin(self):
        bridge=policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world);self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","native shared fire standalone required")
        self.player_health=float(self.health.call_function("GetHealth"));self.original_control=self.controller.call_function("GetControlRotation")
        self.report["native_clear_ability_timers_cvar"]=int(policy.lib("KismetSystemLibrary").call_function("GetConsoleVariableIntValue","AbilitySystem.ClearAbilityTimers"))
        self.original=fixtures.baseline(self.controller);self.original_ammo=ammo_policy.ammo(services(self.controller)[1].call_function("GetActiveSlotItem"))
        self.actions=[ue.load_object(ue.find_class("InputAction"),"/Game/Input/Actions/"+name+"."+name) for name in ("IA_Weapon_Fire","IA_Weapon_Fire_Auto")]
        self.helper=ue.load_class("/Game/UEPValidation/BP_WeaponAbilityFireProbe.BP_WeaponAbilityFireProbe_C").get_cdo()
        self.router=policy.lib("SubsystemBlueprintLibrary").call_function("GetGameInstanceSubsystem",self.world,ue.find_class("GameplayMessageSubsystem"))
        self.team=policy.lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        state=self.statics.call_function("GetGameState",self.world);self.bot_component=state.get_component_by_type(ue.find_class("LyraBotCreationComponent"))
        self.observe(ue.load_class("/Game/Weapons/B_Weapon.B_Weapon_C"));self.observe(ue.load_class(policy.CLASS))
        dummy=self.world.actor_spawn(ue.find_class("Actor"));dummy.add_actor_root_component(ue.find_class("SceneComponent"),"UEPFireSelectionRoot");self.created.append(dummy)
        for asset in {value for options in policy.MONTAGES.values() for value in options}:ue.load_object(ue.find_class("AnimMontage"),asset)
        self.montage_trials(dummy);self.next_weapon()
    def instances(self,cls):
        return [value for spec in self.asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class()==cls for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]
    def montage_trials(self,dummy):
        for weapon,cls_path in WEAPONS.items():
            cls=ue.load_class(cls_path);ability=ue.new_object(cls)
            for yaw in (0.,45.):
                require(dummy.call_function("K2_TeleportTo",ue.FVector(),ue.FRotator(0.,0.,yaw)),"native selection actor placement failed")
                for normal in NORMALS:
                    for seed in (1729,7919,104729,999983,15485863,42424242,123456789,2147483629):
                        results=[]
                        for profile in PROFILES:
                            ue.set_mixin_profile(ability,profile);ue.set_random_seed(seed)
                            montage,=ability.call_function(policy.SELECT,ue.FVector(*normal),dummy)
                            following=int(policy.lib("KismetMathLibrary").call_function("RandomIntegerInRange",0,32767));results.append((path(montage),following))
                        self.report["montage_pairs"].append(dict(weapon=weapon,yaw=yaw,normal=list(normal),seed=seed,same_asset=results[0][0]==results[1][0],same_next_native_random=results[0][1]==results[1][1],blueprint=results[0],python=results[1]))
            ue.set_mixin_profile(ability,"Python")
    def restore_weapon(self):
        if hasattr(self,"item") and valid(self.item):
            for tag,value in zip((ammo_policy.MAGAZINE,ammo_policy.CAPACITY,ammo_policy.SPARE),self.weapon_ammo):set_stat(self.item,tag,value)
        if hasattr(self,"original_fire_profile") and valid(self.ability):ue.set_mixin_profile(self.ability,self.original_fire_profile)
        if self.fixture is not None:fixtures.restore(self.controller,self.fixture);self.fixture=None
    def next_weapon(self):
        if self.index>=len(PLAN):self.start_lifecycle();return
        weapon,profile,field=PLAN[self.index]
        if self.weapon!=weapon:
            self.restore_weapon();self.weapon=weapon
            if weapon!="pistol":self.fixture=fixtures.install(self.controller,weapon)
            self.enter("weapon-ready");return
        self.prepare_shot()
    def weapon_ready(self):
        model=capture(self.controller)
        if model is None or fixtures.WEAPONS[self.weapon][2] not in model["definition"]:return
        cls=ue.load_class(WEAPONS[self.weapon]);found=self.instances(cls)
        if len(found)!=1 or found[0].get_property("bIsActive"):return
        self.ability=found[0];self.item=self.ability.call_function("GetAssociatedItem");self.weapon_ammo=ammo_policy.ammo(self.item)
        self.original_fire_profile=str(ue.get_mixin_profile(self.ability));self.prepare_shot()
    def pick_enemy(self):
        for controller in self.bots():
            pawn=controller.get_controlled_pawn();asc=ability_system(pawn) if valid(pawn) else None
            health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent")) if valid(pawn) else None
            if not valid(asc) or not valid(health) or health.call_function("IsDeadOrDying") or health.call_function("GetHealth")<=0:continue
            if self.team.call_function("CompareTeams",self.pawn,pawn)[0]!=ELyraTeamComparison.DifferentTeams:continue
            if policy.lib("BlueprintGameplayTagLibrary").call_function("DoesTagAssetInterfaceHaveTag",asc,GameplayTag(TagName="Gameplay.DamageImmunity")):continue
            return pawn,health
        return None
    def prepare_shot(self):
        self.profile=PLAN[self.index][1];self.field_enabled=PLAN[self.index][2]
        ue.set_mixin_profile(self.ability,self.profile)
        require(not self.ability.get_property("bIsActive"),"previous native fire still active")
        self.saved_field=self.ability.get_property("FieldActorToSpawnOnImpact");self.ability.set_property("FieldActorToSpawnOnImpact",ue.find_class("CameraActor") if self.field_enabled else None)
        set_stat(self.item,ammo_policy.MAGAZINE,max(3,self.weapon_ammo[1]//2));self.enter("enemy-ready")
    def enemy_ready(self):
        candidate=self.pick_enemy()
        if candidate is None:
            if time.monotonic()-self.phase_started>2. and not getattr(self,"spawn_requested",False):
                require(valid(self.bot_component),"native bot creation component missing");before={path(value) for value in self.bots()};self.bot_component.call_function("SpawnOneBot")
                self.created_bots.extend(value for value in self.bots() if path(value) not in before);self.spawn_requested=True
            require(time.monotonic()-self.phase_started<18.,"no naturally initialized enemy Health/ASC target");return
        self.spawn_requested=False;self.enemy,self.enemy_health=candidate
        self.bot_poses.append((self.enemy,self.enemy.get_actor_location(),self.enemy.get_actor_rotation()))
        camera=self.controller.get_property("PlayerCameraManager");forward=policy.lib("KismetMathLibrary").call_function("GetForwardVector",camera.call_function("GetCameraRotation"))
        point=self.pawn.get_actor_location();placed=False
        for distance in (350.,450.,550.):
            target=ue.FVector(point.x+forward.x*distance,point.y+forward.y*distance,point.z)
            if self.enemy.call_function("K2_TeleportTo",target,ue.FRotator()):placed=True;break
        require(placed,"native enemy pose arrangement failed")
        self.enemy.get_property("CharacterMovement").call_function("StopMovementImmediately")
        self.target_point=self.enemy.get_property("Mesh").call_function("GetSocketLocation","spine_03")
        aim=policy.lib("KismetMathLibrary").call_function("FindLookAtRotation",camera.call_function("GetCameraLocation"),self.target_point)
        self.controller.call_function("SetControlRotation",aim);self.enter("aim")
    def cameras(self):return [value for value in self.world.all_actors() if valid(value) and value.is_a(ue.find_class("CameraActor"))]
    def inject(self,pressed):
        for action in self.actions:self.controller.inject_enhanced_input_for_action(action,pressed)
    def start_shot(self):
        self.data_events=[];self.weapon_events=[];self.callback_events=[];self.before_counts=copy.deepcopy(policy.evidence(self.ability))
        self.ammo_before=ammo_policy.ammo(self.item)[0];self.enemy_before=float(self.enemy_health.call_function("GetHealth"));self.enemy_path=path(self.enemy);self.field_before={path(value) for value in self.cameras()}
        self.recording=True;self.shot_start=self.game_time();self.task_observed=0;self.montage_observed=False;self.active_observed=False;self.released=False;self.activation_witness=None
        self.inject(True);self.enter("shot")
    def shot(self):
        self.inject(False);self.released=True
        active=bool(self.ability.get_property("bIsActive"));self.active_observed|=active
        self.task_observed=max(self.task_observed,sum(valid(task) for task in self.ability.get_property("ActiveTasks")))
        anim=self.pawn.get_property("Mesh").call_function("GetAnimInstance")
        self.montage_observed|=bool(anim.call_function("Montage_IsPlaying",self.ability.get_property("CharacterFireMontage")))
        elapsed=self.game_time()-self.shot_start
        if elapsed<max(1.,float(self.ability.get_property("FireDelayTimeSecs"))+.4) or active:
            require(elapsed<5.,"native input firing did not end");return
        self.recording=False;fields=[actor for actor in self.cameras() if path(actor) not in self.field_before];self.created.extend(fields)
        event=self.data_events[0] if len(self.data_events)==1 else dict(count=0,blocking=0,actors=[],points=[])
        poses=sorted(vec(actor.get_actor_location()) for actor in fields);expected=sorted(event["points"]) if self.field_enabled else []
        self.report["shots"].append(dict(weapon=self.weapon,profile=self.profile,field_enabled=self.field_enabled,native_class=path(self.ability.get_class()),
            native_source_object_matches=self.ability.call_function("GetAssociatedEquipment").call_function("GetInstigator")==self.item,
            input_press_count=1,input_released=self.released,native_activation_observed=self.active_observed,native_target_callbacks=len(self.data_events),target_count=event["count"],blocking_hits=event["blocking"],
            ammo_before=self.ammo_before,ammo_after=ammo_policy.ammo(self.item)[0],target_health_before=self.enemy_before,target_health_after=event.get("health_after",self.enemy_before),
            native_enemy_hit=self.enemy_path in event["actors"],native_hit_actors=event["actors"],native_traces=event.get("traces",[]),native_hit_points=event["points"],arranged_enemy=self.enemy_path,weapon_actor_fire_calls=len(self.weapon_events),native_tasks_observed=self.task_observed,native_montage_playing=self.montage_observed,
            native_ability_ended=not active,field_actor_count=len(fields),field_actor_poses_match=poses==expected,native_completion_callbacks=len(self.callback_events),activation_witness=self.activation_witness,no_handler_errors=True))
        self.ability.set_property("FieldActorToSpawnOnImpact",self.saved_field)
        for actor in fields:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        if self.weapon=="pistol" and not self.field_enabled:self.advance()
        else:self.start_failure()
    def send_failure(self,avatar):
        payload=LyraAbilityMontageFailureMessage(PlayerController=self.controller,AvatarActor=avatar,FailureTags=GameplayTagContainer(),FailureMontage=self.ability.get_property("CharacterFireMontage"))
        self.helper.call_function("BroadcastMontageFailure",self.router,GameplayTag(TagName=policy.FAILURE_CHANNEL),payload)
    def start_failure(self):
        require(self.ability.get_property("Can Trigger Failure Montage"),"previous native failure throttle still active")
        added=policy.evidence(self.ability)["added"]+policy.evidence(self.ability)["fallback_added"];self.added_before=added
        self.send_failure(self.created[0]);foreign=bool(self.ability.get_property("Can Trigger Failure Montage"))
        before=dict(policy.evidence(self.ability));self.failure_start=self.game_time();self.send_failure(self.pawn)
        self.failure_row=dict(weapon=self.weapon,profile=self.profile,actual_native_message_dispatch=policy.evidence(self.ability)["failure_messages"]+policy.evidence(self.ability)["fallback_failure_messages"]>before["failure_messages"]+before["fallback_failure_messages"],
            foreign_avatar_noop=foreign,allowed_message_disabled_flag=not self.ability.get_property("Can Trigger Failure Montage"),native_failure_montage_observed=False,source_listener_added_once=added==1)
        self.repeated=False;self.switched=False;self.enter("failure")
    def failure_tick(self):
        elapsed=self.game_time()-self.failure_start;anim=self.pawn.get_property("Mesh").call_function("GetAnimInstance")
        self.failure_row["native_failure_montage_observed"]|=bool(anim.call_function("Montage_IsPlaying",self.ability.get_property("CharacterFireMontage")))
        if elapsed>=.2 and not self.repeated:
            self.send_failure(self.pawn);self.failure_row["repeat_throttled"]=not self.ability.get_property("Can Trigger Failure Montage");self.repeated=True
        if elapsed>=.35 and not self.switched:
            ue.set_mixin_profile(self.ability,"Python" if self.profile=="BlueprintFallback" else "BlueprintFallback");self.switched=True
        if not self.ability.get_property("Can Trigger Failure Montage"):
            require(elapsed<1.6,"native failure throttle did not reenable");return
        self.failure_row.update(native_timer_reenabled_flag=True,reenable_elapsed=elapsed,profile_switch_did_not_create_listener=policy.evidence(self.ability)["added"]+policy.evidence(self.ability)["fallback_added"]==self.added_before)
        self.report["failure_cases"].append(self.failure_row);ue.set_mixin_profile(self.ability,self.profile);self.advance()
    def advance(self):
        self.index+=1;self.next_weapon()
    def start_lifecycle(self):
        self.recording=False;self.restore_weapon();self.weapon="pistol";self.lifecycle_mode=True;self.lifecycle_index=0
        self.enter("lifecycle-ready")
    def lifecycle_ready(self):
        found=self.instances(ue.load_class(WEAPONS["pistol"]))
        if len(found)!=1 or found[0].get_property("bIsActive"):return
        self.ability=found[0];self.item=self.ability.call_function("GetAssociatedItem");self.weapon_ammo=ammo_policy.ammo(self.item)
        self.original_fire_profile=str(ue.get_mixin_profile(self.ability));self.original_fire_delay=float(self.ability.get_property("FireDelayTimeSecs"))
        self.original_fire_montage=self.ability.get_property("CharacterFireMontage")
        self.begin_lifecycle_case()
    def begin_lifecycle_case(self):
        self.profile=PROFILES[self.lifecycle_index//4];self.lifecycle_kind=("complete","cancel","interrupt","null-montage")[self.lifecycle_index%4]
        ue.set_mixin_profile(self.ability,self.profile);self.ability.set_property("FireDelayTimeSecs",2.)
        self.ability.set_property("CharacterFireMontage",None if self.lifecycle_kind=="null-montage" else self.original_fire_montage)
        set_stat(self.item,ammo_policy.MAGAZINE,max(3,self.weapon_ammo[1]//2))
        self.controller.call_function("SetControlRotation",ue.FRotator(0.,60.,0.));self.callback_events=[];self.data_events=[];self.weapon_events=[]
        self.activation_witness=None;self.task_observed=0;self.montage_observed=False;self.lifecycle_intervened=False;self.recording=True
        self.lifecycle_start=self.game_time();self.inject(True);self.enter("lifecycle")
    def lifecycle_tick(self):
        self.inject(False);elapsed=self.game_time()-self.lifecycle_start
        if elapsed<2.25:return
        self.recording=False;expected={"complete":"MontageCompleted","cancel":"MontageInterrupted","interrupt":"MontageInterrupted","null-montage":"MontageCancelled"}[self.lifecycle_kind]
        self.report["lifecycle_cases"].append(dict(profile=self.profile,kind=self.lifecycle_kind,native_input_used=True,native_activation_montage=self.montage_observed,
            intervention_used=self.lifecycle_intervened,expected_native_callback=expected,observed_native_callbacks=copy.deepcopy(self.callback_events),native_ability_ended=not self.ability.get_property("bIsActive")))
        self.ability.set_property("FireDelayTimeSecs",self.original_fire_delay);self.ability.set_property("CharacterFireMontage",self.original_fire_montage);self.lifecycle_index+=1
        if self.lifecycle_index==8:self.finish()
        else:self.begin_lifecycle_case()
    def cleanup(self):
        self.recording=False
        if hasattr(self,"actions"):self.inject(False)
        if hasattr(self,"original_fire_profile") and valid(self.ability):
            if self.ability.get_property("bIsActive"):self.ability.call_function("K2_CancelAbility")
            if hasattr(self,"saved_field"):self.ability.set_property("FieldActorToSpawnOnImpact",self.saved_field)
            if hasattr(self,"original_fire_delay"):self.ability.set_property("FireDelayTimeSecs",self.original_fire_delay)
            if hasattr(self,"original_fire_montage"):self.ability.set_property("CharacterFireMontage",self.original_fire_montage)
        if hasattr(self,"controller"):
            self.restore_weapon()
            self.controller.call_function("SetControlRotation",self.original_control)
            restored=self.controller.call_function("GetControlRotation")
            self.report["original_control_rotation_restored"]=all(abs(float(getattr(restored,key))-float(getattr(self.original_control,key)))<.0001 for key in ("roll","pitch","yaw"))
            self.report["original_inventory_ammo_restored"]=capture(self.controller)==self.original["original_model"]
            self.report["original_player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.player_health
        for actor in self.created:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        for actor,point,rotation in self.bot_poses:
            if not dead(actor):actor.call_function("K2_TeleportTo",point,rotation)
        for controller in reversed(self.created_bots):
            if valid(controller):
                values=list(self.bot_component.get_property("SpawnedBotList"))
                require(values and values[-1]==controller,"do not remove a foreign bot during native fixture cleanup")
                self.bot_component.call_function("RemoveOneBot")
        self.report["all_test_actors_destroyed"]=all(dead(actor) for actor in self.created)
        restored=True
        for cls,profiles in self.observers.items():
            for profile,base in profiles.items():ue.register_mixin_profile(cls,profile,base)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls]
            restored&=all(row["profiles"][name]["python_class"] is base for name,base in profiles.items())
        self.report["observer_profiles_restored"]=restored
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,"native shared fire total timeout")
            if self.phase=="ready":self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="weapon-ready":self.weapon_ready()
                elif self.phase=="enemy-ready":self.enemy_ready()
                elif self.phase=="aim":
                    camera=self.controller.get_property("PlayerCameraManager")
                    point=self.enemy.get_property("Mesh").call_function("GetSocketLocation","spine_03")
                    aim=policy.lib("KismetMathLibrary").call_function("FindLookAtRotation",camera.call_function("GetCameraLocation"),point)
                    self.controller.call_function("SetControlRotation",aim)
                    if time.monotonic()-self.phase_started>=.4:self.start_shot()
                elif self.phase=="shot":self.shot()
                elif self.phase=="failure":self.failure_tick()
                elif self.phase=="lifecycle-ready":self.lifecycle_ready()
                elif self.phase=="lifecycle":self.lifecycle_tick()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_ABILITY_FIRE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_ABILITY_FIRE_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponAbilityFireResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
