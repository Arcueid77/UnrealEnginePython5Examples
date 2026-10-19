"""Native Actor startup and real native team changes; callbacks never replayed."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.enums import ESpawnActorCollisionHandlingMethod,ESpawnActorScaleMethod
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from . import weapon_actor_begin_mixin as policy,weapon_actor_helpers_mixin as helpers
from .weapon_actor_begin_contract import CLASSES,PROFILES,OWNERS,require,validate


def path(value):return value.get_path_name() if valid(value) else None
def dead(value):return not valid(value) or value.call_function("IsActorBeingDestroyed")
def proxies():return {path(value):value for value in ue.tobject_iterator(ue.find_class("AsyncAction_ObserveTeamColors")) if valid(value) and value.call_function("IsActive")}
def all_proxies():return {path(value):value for value in ue.tobject_iterator(ue.find_class("AsyncAction_ObserveTeamColors")) if valid(value)}


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.owned=[];self.target=None;self.events=[];self.begins=0;self.original_classes={}
        self.report=dict(schema_version=1,status="running",error=None,cases=[],observation_errors=[],full_acceptance=False,network_acceptance=False,packaged_runtime=False,
            health_properties_written=False,begin_play_replayed=False,team_callback_replayed=False,python_callback_retained=False,production_proxy_cancelled_by_script=False)
    def team(self):
        found,number,_=ue.find_class("LyraTeamStatics").get_cdo().call_function("FindTeamFromObject",self.pawn,False)
        require(found,"native owner team missing");return int(number)
    def change(self,number):
        self.team_cheats.call_function("SetTeam",number)
        require(self.team()==number,"native development team change rejected")
    def begin(self):
        bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world)
        self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        require(self.report["native_mode"]=="Standalone","team fixture restricted to standalone")
        self.parent=ue.load_class(helpers.CLASS);ue.register_declared_mixin(self.parent)
        self.teams=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        self.original_team=self.team();self.health_before=self.healths();self.initial_proxies=set(proxies())
        manager=self.controller.get_property("CheatManager")
        require(valid(manager),"native standalone development CheatManager required")
        self.team_cheats=ue.new_object(ue.find_class("LyraTeamCheats"),manager)
        self.report["native_team_change_entry"]="LyraTeamCheats.SetTeam -> LyraTeamSubsystem.ChangeTeamForActor"
        self.nonpawn=self.world.actor_spawn(ue.find_class("Actor"));self.actors.append(self.nonpawn)
        self.unassigned=self.world.actor_spawn(ue.find_class("Pawn"));self.actors.append(self.unassigned)
        binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.parent]
        self.original_classes={name:row["python_class"] for name,row in binding["profiles"].items()};owner=self
        for name,base in self.original_classes.items():
            def around_begin(handler):
                def invoke(actor):
                    watched=actor==owner.target
                    handler(actor)
                    if watched:owner.begins+=1
                return invoke
            def around_changed(handler,profile):
                def invoke(actor,bTeamSet,TeamId,DisplayAsset):
                    watched=actor==owner.target
                    before=copy.deepcopy(helpers.evidence(actor)) if watched else None
                    handler(actor,bTeamSet,TeamId,DisplayAsset)
                    if watched:
                        after=helpers.evidence(actor)
                        owner.events.append(dict(profile=profile,assigned=bool(bTeamSet),team=int(TeamId),display=path(DisplayAsset),
                            stencil_delta=sum(after[k]-before[k] for k in ("stencil_python","stencil_fallback")),
                            color_delta=sum(after[k]-before[k] for k in ("colors_python","colors_fallback"))))
                invoke.override=policy.CALLBACK;return invoke
            methods={key:value for key,value in vars(base).items() if not key.startswith("__") and callable(value)}
            methods["ReceiveBeginPlay"]=around_begin(base.ReceiveBeginPlay)
            methods["ObservedTeamChanged"]=around_changed(base.ObservedTeamChanged,name)
            ue.register_mixin_profile(self.parent,name,type("ObservedWeaponBegin"+name,(),methods))
        self.plan=[(cls,profile,owner_kind) for cls in CLASSES for profile in PROFILES for owner_kind in OWNERS]
        self.enter("trial")
    def trial(self):
        cls_path,profile,owner_kind=self.plan[self.index];cls=ue.load_class(cls_path)
        owner_obj=self.pawn if owner_kind=="pawn" else self.unassigned if owner_kind=="unassigned-pawn" else self.nonpawn if owner_kind=="actor" else None
        transform=ue.FTransform(ue.FVector(200000.,200000.,2000.),ue.FRotator(),ue.FVector(1.,1.,1.));scale=ESpawnActorScaleMethod.OverrideRootScale
        before=set(all_proxies());self.events=[];self.begins=0
        actor=self.statics.call_function("BeginDeferredActorSpawnFromClass",self.world,cls,transform,ESpawnActorCollisionHandlingMethod.AlwaysSpawn,owner_obj,scale)
        self.actors.append(actor);self.target=actor;ue.set_mixin_profile(actor,profile)
        self.statics.call_function("FinishSpawningActor",actor,transform,scale)
        added=[value for key,value in all_proxies().items() if key not in before];self.owned.extend(added)
        row=dict(**{"class":path(cls)},profile=profile,owner=owner_kind,actual_native_begin_count=self.begins,native_proxies_added=len(added),
            owner_matches=actor.get_property("OwnerAsPawn")==owner_obj,owner_field_is_null=actor.get_property("OwnerAsPawn") is None,
            proxy_inactive_after_initial_broadcast=all(not value.call_function("IsActive") for value in added))
        if owner_kind=="pawn":
            other_team=2 if self.original_team!=2 else 1
            other_profile="Python" if profile=="BlueprintFallback" else "BlueprintFallback"
            self.change(other_team)
            size=len(proxies());ue.set_mixin_profile(actor,other_profile);switched=len(proxies())==size
            self.change(self.original_team)
            ue.set_mixin_profile(actor,profile);self.change(other_team)
            row.update(original_team=self.original_team,other_team=other_team,other_profile=other_profile,profile_switch_did_not_create_proxy=switched)
        row["events"]=copy.deepcopy(self.events)
        actor.call_function("K2_DestroyActor");row["actor_destroyed"]=dead(actor)
        if owner_kind=="pawn":
            count=len(self.events);self.change(other_team);self.change(self.original_team)
            row.update(no_dead_actor_callbacks=len(self.events)==count,proxy_active_after_actor_destroy=all(valid(value) and value.call_function("IsActive") for value in added))
        for value in added:
            if valid(value) and value.call_function("IsActive"):value.call_function("Cancel")
        self.target=None;self.report["cases"].append(row);self.index+=1
        ue.log("UEP_WEAPON_ACTOR_BEGIN_CASE_CAPTURED "+cls_path+" "+profile+" "+owner_kind)
        if self.index==len(self.plan):self.finish()
    def cleanup(self):
        if hasattr(self,"original_team") and self.team()!=self.original_team:self.change(self.original_team)
        self.target=None
        for actor in self.actors:
            if not dead(actor):actor.call_function("K2_DestroyActor")
        for value in self.owned:
            if valid(value) and value.call_function("IsActive"):value.call_function("Cancel")
        if self.original_classes:
            for name,base in self.original_classes.items():ue.register_mixin_profile(self.parent,name,base)
            binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==self.parent]
            self.report["production_profiles_restored"]=all(binding["profiles"][name]["python_class"] is base for name,base in self.original_classes.items())
        self.report.update(test_actors_destroyed=all(dead(actor) for actor in self.actors),test_owned_proxies_cancelled=all(not valid(value) or not value.call_function("IsActive") for value in self.owned),
            original_team_restored=hasattr(self,"original_team") and self.team()==self.original_team,
            original_pawn_health_unchanged=hasattr(self,"health_before") and self.healths()==self.health_before,
            original_active_proxies_preserved=set(proxies())==self.initial_proxies if hasattr(self,"initial_proxies") else False)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180.,"native weapon BeginPlay total timeout")
            if self.phase=="ready":self.ready()
            elif self.phase=="trial":self.trial()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_ACTOR_BEGIN_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_ACTOR_BEGIN_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPWeaponActorBeginResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
