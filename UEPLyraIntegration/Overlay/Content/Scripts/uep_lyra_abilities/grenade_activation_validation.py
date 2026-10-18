"""Real granted ASC Grenade activation; native collision/typed-message witnesses.

Test destroys observed projectiles before a world tick. Explosion/damage is a
separate unaccepted migration, never restored by raw Health/inventory writes.
"""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from unreal_engine.enums import ETraceTypeQuery,EDrawDebugTrace
from uep_runtime import SubscriptionScope
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_helpers_validation import Validation as Ready,instances,specs
from .auto_respawn_events_mixin import ADAPTER
from .dash_local_direction_validation import restore_control
from .melee_trace_mixin import trace_outputs,break_hit
from .grenade_widget_validation import roots
from .grenade_activation_contract import CLASS,PROJECTILE,PLAN,require,validate
from . import grenade_activation_mixin as policy


def path(obj): return obj.get_path_name() if valid(obj) else None
def v(obj): return [float(obj.x),float(obj.y),float(obj.z)]
def rot(obj): return [float(obj.roll),float(obj.pitch),float(obj.yaw)]
def config(ability):
    return dict(range=float(ability.get_property("Default Targeting Range")),offset=float(ability.get_property("Start Trace Offset")),montage=path(ability.get_property("GrenadeThrowMontage")))
def counts(ability): return {k:v for k,v in policy.evidence(ability).items() if isinstance(v,int)}


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.cleaned=False;self.fixtures=[];self.test_projectiles=[]
        self.target=None;self.native_events=[];self.messages=[];self.observation_errors=[];self.scope=SubscriptionScope();self.installed=False
        self.report=dict(schema_version=1,status="running",error=None,cases=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            physical_input_tested=False,activation_event_replayed=False,task_callbacks_replayed=False,ability_granted_by_fixture=False,
            health_properties_written=False,inventory_properties_written=False,ability_spec_properties_written=False,projectile_actor_business_migrated=False,
            explosion_damage_tested=False,denied_body_native_tested=False,request_entry="ASC.TryActivateAbilityByClass",observation_errors=self.observation_errors)
    def box(self,label,location,extent):
        actor=self.world.actor_spawn(ue.find_class("Actor"),location);require(valid(actor),"native fixture actor missing")
        self.fixtures.append(actor);actor.call_function("SetReplicates",False)
        box=actor.add_actor_root_component(ue.find_class("BoxComponent"),label);box.call_function("SetBoxExtent",extent,False)
        box.call_function("SetCollisionObjectType",0);box.call_function("SetCollisionResponseToAllChannels",2);box.call_function("SetCollisionEnabled",1)
        require(actor.call_function("K2_TeleportTo",location,ue.FRotator()),"native fixture transform refused");return actor,box
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","far-field fixture restricted to standalone")
        values=instances(self.asc,ue.load_class(CLASS));require(len(values)==1,"one actual granted Grenade primary instance required");self.grenade=values[0]
        self.original=dict(profile=str(ue.get_mixin_profile(self.grenade)),config=config(self.grenade),specs=specs(self.asc),handle=int(roots(self.asc)[0].Handle.Handle),
            location=self.pawn.get_actor_location(),rotation=self.pawn.get_actor_rotation(),control=self.controller.call_function("GetControlRotation"))
        self.report.update(native_class=path(self.grenade.get_class()),actual_granted_primary_instance=True)
        self.math=ue.find_class("KismetMathLibrary").get_cdo();self.system=ue.find_class("KismetSystemLibrary").get_cdo();self.gas=ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
        self.floor,_=self.box("UEPGrenadeFloor",ue.FVector(200000.,200000.,1980.),ue.FVector(5000.,5000.,20.))
        self.wall,self.wall_box=self.box("UEPGrenadeAim",ue.FVector(200000.,202000.,2100.),ue.FVector(2.,30.,30.));self.wall_box.call_function("SetCollisionEnabled",0)
        self.install()
        reader=ue.load_class(ADAPTER).get_cdo()
        def read(proxy):
            payload,success=reader.call_function("ReadDuration",proxy);require(success is True,"native typed Grenade duration extraction failed");return payload
        def received(channel,payload):
            try:
                if path(payload.Instigator)==self.target:
                    self.messages.append(dict(channel=str(channel.TagName),instigator=path(payload.Instigator),duration=float(payload.Duration),
                        native_active=bool(self.grenade.get_property("bIsActive")),native_montage_task_count=len([task for task in self.grenade.get_property("ActiveTasks") if valid(task) and task.is_a(ue.find_class("AbilityTask_PlayMontageAndWait"))])))
            except Exception: self.observation_errors.append(traceback.format_exc())
        self.scope.listen_gameplay_message(self.world,policy.CHANNEL,ue.find_struct("LyraInteractionDurationMessage"),read,received)
        self.enter("reset")
    def install(self):
        owner=self
        def around(handler,profile):
            def invoke(ability):
                watched=ability==owner.grenade and owner.target is not None
                before=None
                if watched:
                    try: before=owner.view()
                    except Exception: owner.observation_errors.append(traceback.format_exc())
                handler(ability) # Native-selected production handler, exactly once.
                if watched:
                    try:
                        actors=[actor for actor in owner.projectiles() if path(actor) not in owner.pre_projectiles]
                        evidence=[]
                        for actor in actors:
                            evidence.append(dict(path=path(actor),**{"class":path(actor.get_class())},instigator=path(actor.get_property("Instigator")),owner=path(actor.call_function("GetOwner")),
                                location=v(actor.get_actor_location()),rotation=rot(actor.get_actor_rotation()),scale=v(actor.call_function("GetActorScale3D"))))
                            owner.test_projectiles.append(actor)
                        owner.native_events.append(dict(profile=profile,before=before,location=v(ability.get_property("Location")),direction=rot(ability.get_property("Direction")),
                            cooldown=float(ability.get_property("Cooldown Time")),native_cooldown=float(ability.call_function("GetCooldownTimeRemaining")),
                            active_after=bool(ability.get_property("bIsActive")),tasks_after=len([task for task in ability.get_property("ActiveTasks") if valid(task)]),
                            projectiles=evidence,montage=path(owner.pawn.call_function("GetCurrentMontage"))))
                        for actor in actors: actor.call_function("K2_DestroyActor")
                    except Exception: owner.observation_errors.append(traceback.format_exc())
            invoke.override="K2_ActivateAbility";return invoke
        for name,base in (("Python",policy.LyraGrenadeActivationPythonProfile),("BlueprintFallback",policy.LyraGrenadeActivationBlueprintFallbackProfile)):
            ue.register_mixin_profile(ue.load_class(CLASS),name,type("ObservedGrenadeActivation"+name,(),dict(K2_ActivateAbility=around(base.K2_ActivateAbility,name),
                K2_OnPawnAvatarSet=base.K2_OnPawnAvatarSet,K2_OnAbilityRemoved=base.K2_OnAbilityRemoved)))
        self.installed=True
    def projectiles(self):
        actors,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.load_class(PROJECTILE));return actors
    def healths(self):
        actors,=self.statics.call_function("GetAllActorsOfClass",self.world,ue.find_class("Pawn"));result={}
        for actor in actors:
            health=actor.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if valid(health): result[path(actor)]=dict(health=float(health.call_function("GetHealth")),death=int(health.call_function("GetDeathState")))
        return result
    def reset(self):
        if self.grenade.call_function("GetCooldownTimeRemaining")>0: return
        self.old_pawn=path(self.controller.get_controlled_pawn());self.target=None
        owner=self.controller.PlayerState;tag=GameplayTag(TagName="GameplayEvent.RequestReset")
        self.gas.call_function("SendGameplayEventToActor",owner,tag,GameplayEventData(EventTag=tag,Instigator=owner,Target=owner));self.enter("respawn")
    def respawn(self):
        require(time.monotonic()-self.phase_started<30.,"native Grenade restock/Pawn replacement timeout")
        pawn=self.controller.get_controlled_pawn()
        if not valid(pawn) or path(pawn)==self.old_pawn: return
        if not self.attach(self.world,self.controller): return
        if self.asc.call_function("GetGameplayTagCount",GameplayTag(TagName="Gameplay.DamageImmunity")): return
        require(instances(self.asc,ue.load_class(CLASS))==[self.grenade],"persistent granted Grenade instance changed")
        require(self.pawn.call_function("K2_TeleportTo",ue.FVector(200000.,200000.,2100.),ue.FRotator()),"native standalone player pose refused")
        self.pawn.call_function("GetMovementComponent").call_function("StopMovementImmediately")
        self.controller.call_function("SetControlRotation",ue.FRotator());self.wall_box.call_function("SetCollisionEnabled",0)
        self.enter("settle")
    def view(self):
        camera=self.controller.get_property("PlayerCameraManager");eye=camera.call_function("GetCameraLocation");look=camera.call_function("GetCameraRotation")
        facing=self.math.call_function("Conv_RotatorToVector",look)
        start=self.math.call_function("Add_VectorVector",eye,self.math.call_function("Multiply_VectorFloat",facing,self.original["config"]["offset"]))
        end=self.math.call_function("Add_VectorVector",eye,self.math.call_function("Multiply_VectorFloat",facing,self.original["config"]["range"]))
        raw=self.system.call_function("LineTraceSingle",WorldContextObject=self.grenade,Start=start,End=end,TraceChannel=ETraceTypeQuery.TraceTypeQuery4,
            bTraceComplex=False,ActorsToIgnore=[self.pawn],DrawDebugType=getattr(EDrawDebugTrace,"None"),bIgnoreSelf=True,TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=5.)
        hit,record=trace_outputs("LineTraceSingle",raw);fields=break_hit(record)
        return dict(actor_location=v(self.pawn.get_actor_location()),forward=v(self.pawn.call_function("GetActorForwardVector")),up=v(self.pawn.call_function("GetActorUpVector")),
            control=rot(self.controller.call_function("GetControlRotation")),eye=v(eye),camera=rot(look),
            trace=dict(hit=bool(hit),distance=float(fields["Distance"]),location=v(fields["Location"]),start=v(start),end=v(end)))
    def aim_fixture(self):
        name,profile=PLAN[self.index];view=self.view()
        if name!="miss":
            start,end=view["trace"]["start"],view["trace"]["end"];delta=[b-a for a,b in zip(start,end)];length=sum(x*x for x in delta)**.5
            distance=32. if name=="near" else 182.
            point=ue.FVector(*[a+distance*b/length for a,b in zip(start,delta)])
            require(self.wall.call_function("K2_TeleportTo",point,ue.FRotator()),"native Grenade collision fixture refused");self.wall_box.call_function("SetCollisionEnabled",1)
        self.target=path(self.pawn);ue.set_mixin_profile(self.grenade,profile);self.enter("request")
    def request(self):
        name,profile=PLAN[self.index];self.native_events=[];self.messages=[];self.pre_projectiles=[path(actor) for actor in self.projectiles()]
        self.before_counts=counts(self.grenade);self.health_before=self.healths()
        self.row=dict(name=name,profile=profile,pawn=path(self.pawn),native_role=int(self.pawn.call_function("GetLocalRole")),
            native_cost_ready=bool(self.grenade.call_function("K2_CheckAbilityCost")),native_cooldown_ready=bool(self.grenade.call_function("K2_CheckAbilityCooldown")))
        require(self.row["native_cost_ready"] and self.row["native_cooldown_ready"],"real ASC grenade inventory/cooldown not ready after native Reset")
        self.row["native_request_accepted"]=bool(self.asc.call_function("TryActivateAbilityByClass",ue.load_class(CLASS),False))
        require(self.row["native_request_accepted"] and len(self.native_events)==1,"actual Grenade ASC activation/callback missing: "+str(self.observation_errors))
        self.row.update(copy.deepcopy(self.native_events[0]));self.row.update(native_callback_count=len(self.native_events),messages=copy.deepcopy(self.messages))
        self.row["native_repeat_rejected"]=self.asc.call_function("TryActivateAbilityByClass",ue.load_class(CLASS),False) is False
        self.row["montage_continues_after_end"]=self.row["montage"]==self.original["config"]["montage"] and not self.row["active_after"]
        self.after_counts=counts(self.grenade);self.row["stats"]={k:value-self.before_counts[k] for k,value in self.after_counts.items()}
        self.quiet_ticks=0;self.enter("quiet")
    def quiet(self):
        require(time.monotonic()-self.phase_started<12.,"native Grenade montage/quiet interval timeout")
        require(len(self.native_events)==1 and self.messages==self.row["messages"] and counts(self.grenade)==self.after_counts,"late Grenade activation/message/handler")
        require(self.healths()==self.health_before,"Grenade activation fixture changed real Pawn Health; never restore it")
        require([path(actor) for actor in self.projectiles()]==self.pre_projectiles,"test-owned grenade projectile survived observation")
        self.quiet_ticks+=1
        if self.quiet_ticks<20 or path(self.pawn.call_function("GetCurrentMontage"))==self.original["config"]["montage"]: return
        self.row.update(quiet_ticks=self.quiet_ticks,all_pawn_health_unchanged=True,native_montage_completed=True,projectile_destroyed_by_fixture=True,
            persistent_handle_preserved=[int(item.Handle.Handle) for item in roots(self.asc)]==[self.original["handle"]],
            specs_preserved=specs(self.asc)==self.original["specs"],config_preserved=config(self.grenade)==self.original["config"])
        self.report["cases"].append(copy.deepcopy(self.row));ue.log("UEP_GRENADE_ACTIVATION_CASE_PASSED "+self.row["name"]+" "+self.row["profile"])
        self.index+=1;self.target=None
        if self.index==len(PLAN): self.finish()
        else: self.enter("reset")
    def cleanup(self):
        if self.cleaned: return
        self.target=None
        try: self.scope.close()
        finally: self.report["listener_closed"]=self.scope.closed
        for actor in self.test_projectiles+self.fixtures:
            if valid(actor) and not actor.call_function("IsActorBeingDestroyed"): actor.call_function("K2_DestroyActor")
        if self.installed:
            for name,base in (("Python",policy.LyraGrenadeActivationPythonProfile),("BlueprintFallback",policy.LyraGrenadeActivationBlueprintFallbackProfile)):
                ue.register_mixin_profile(ue.load_class(CLASS),name,base)
            binding,=[item for item in ue.get_registered_mixins() if item["target_class"]==ue.load_class(CLASS)]
            self.report["observers_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in (("Python",policy.LyraGrenadeActivationPythonProfile),("BlueprintFallback",policy.LyraGrenadeActivationBlueprintFallbackProfile)))
        if hasattr(self,"original"):
            ue.set_mixin_profile(self.grenade,self.original["profile"])
            self.report.update(profile_restored=str(ue.get_mixin_profile(self.grenade))==self.original["profile"],specs_preserved=specs(self.asc)==self.original["specs"],
                config_preserved=config(self.grenade)==self.original["config"],native_pose_restored=bool(self.pawn.call_function("K2_TeleportTo",self.original["location"],self.original["rotation"])),
                native_control_restored=restore_control(self.controller,self.original["control"])["control_rotation"],
                remaining_test_projectiles=len([actor for actor in self.test_projectiles if valid(actor) and not actor.call_function("IsActorBeingDestroyed")]),
                remaining_fixture_actors=len([actor for actor in self.fixtures if valid(actor) and not actor.call_function("IsActorBeingDestroyed")]))
        self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<250.,"native Grenade activation total timeout: "+self.phase)
            if hasattr(self,"world"): isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
            if self.phase=="ready": self.ready()
            elif self.phase=="reset": self.reset()
            elif self.phase=="respawn": self.respawn()
            elif self.phase=="settle" and time.monotonic()-self.phase_started>=.5: self.aim_fixture()
            elif self.phase=="request": self.request()
            elif self.phase=="quiet": self.quiet()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_ACTIVATION_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_ACTIVATION_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeActivationResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
