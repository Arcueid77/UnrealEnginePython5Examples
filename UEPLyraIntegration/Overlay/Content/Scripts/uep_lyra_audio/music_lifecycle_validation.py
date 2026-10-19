"""Natural component registration, real GMS broadcasts, native GI proxy ownership."""
import atexit
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraVerbMessage
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import music_manager_mixin as controls,music_manager_lifecycle_mixin as policy
from .music_lifecycle_contract import PLAN,require,validate


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.components=[];self.owned_proxies=[];self.created_music=[]
        self.report=dict(status="running",error=None,cases=[],full_acceptance=False,network_acceptance=False,child_delay_business_migrated=False,
            begin_play_replayed=False,callback_replayed=False,python_subscription_roots_added=False,native_proxies_cancelled_by_probe=False,cpp_compile_executed=False)
    def own(self,cls="Actor"):
        actor=self.world.actor_spawn(ue.find_class(cls));actor.call_function("SetReplicates",False);self.actors.append(actor);return actor
    def proxies(self):return {p.get_path_name():p for p in ue.tobject_iterator(ue.find_class("AsyncAction_ListenForGameplayMessage")) if valid(p)}
    def gi_proxies(self):return {p.get_path_name() for p in self.game.get_property("ReferencedObjects") if valid(p) and p.is_a(ue.find_class("AsyncAction_ListenForGameplayMessage"))}
    def broadcast(self,channel,target):self.probe.call_function("BroadcastVerb",self.router,GameplayTag(TagName=channel),LyraVerbMessage(Target=target))
    def begin(self):
        self.health_before=float(self.health.call_function("GetHealth"));self.game=self.statics.call_function("GetGameInstance",self.world);self.old_music=self.game.get_property("MusicSystem")
        self.cls=ue.load_class(controls.CLASS);self.manager=self.statics.call_function("GetGameState",self.world).get_component_by_type(self.cls)
        require(valid(self.manager),"natural music manager missing");self.report["natural_python_begin_before_probe"]=policy.evidence(self.manager)["begin_python"]
        self.manager_fields={name:self.manager.get_property(name) for name in ("Music System","Alpha_Intensity","Alpha_Mvmt","bIsMenu")}
        self.router=controls.lib("SubsystemBlueprintLibrary").call_function("GetGameInstanceSubsystem",self.world,ue.find_class("GameplayMessageSubsystem"))
        self.probe=ue.load_class("/Game/UEPValidation/BP_MusicListenerProbe.BP_MusicListenerProbe_C").get_cdo();self.probe_root_added=not self.probe.is_rooted()
        if self.probe_root_added:self.probe.add_to_root()
        self.foreign=self.own("Pawn");self.foreign_state=self.own("PlayerState")
        self.targets=dict(local_state=self.controller.PlayerState,local_pawn=self.pawn,foreign_state=self.foreign_state,foreign_pawn=self.foreign,null=None)
        self.plan=[(profile,mode) for profile in ("BlueprintFallback","Python") for mode in ("reuse","create")];self.trial_index=0;self.phase="trial"
    def trial(self,profile,mode):
        self.game.set_property("MusicSystem",self.old_music if mode=="reuse" else None);before=set(self.proxies());owner=self.own()
        component=ue.new_object(self.cls,owner);self.components.append(component);ue.set_mixin_profile(component,profile);component.register_component();component.call_function("SetComponentTickEnabled",False)
        stats=policy.evidence(component);begin_count=stats["begin_python"]+stats["begin_fallback"];require(begin_count==1,"component registration did not naturally execute BeginPlay once")
        added=[p for name,p in self.proxies().items() if name not in before];self.owned_proxies.extend(added);sound=component.get_property("Music System")
        if mode=="create" and valid(sound):self.created_music.append(sound)
        row=dict(index=len(self.report["cases"]),profile=profile,mode=mode,native_begin_calls=begin_count,native_proxies_added=len(added),
            component_gi_music_same=sound==self.game.get_property("MusicSystem"),created_new_music=valid(sound) and sound!=self.old_music,messages=[])
        for channel,label,expected in PLAN:
            component.set_property("Alpha_Intensity",.2);before_count=stats["elimination_python"]+stats["damage_python"]+stats["elimination_fallback"]+stats["damage_fallback"]
            self.broadcast(channel,self.targets[label]);after_count=stats["elimination_python"]+stats["damage_python"]+stats["elimination_fallback"]+stats["damage_fallback"]
            row["messages"].append(dict(channel=channel,target=label,intensity=float(component.get_property("Alpha_Intensity")),callback_entries=after_count-before_count))
        gi_before=self.gi_proxies();other="Python" if profile=="BlueprintFallback" else "BlueprintFallback";ue.set_mixin_profile(component,other)
        row["profile_switch_proxy_count_unchanged"]=self.gi_proxies()==gi_before;component.set_property("Alpha_Intensity",.2)
        before_count=stats["damage_python"]+stats["damage_fallback"];self.broadcast("Lyra.Damage.Taken.Message",self.pawn)
        row.update(switched_message_intensity=float(component.get_property("Alpha_Intensity")),switched_callback_entries=stats["damage_python"]+stats["damage_fallback"]-before_count)
        component.call_function("K2_DestroyComponent",component);row["component_destroyed"]=not valid(component);keys={p.get_path_name() for p in added}
        row["proxy_gi_references_immediately_after_destroy"]=len(keys.intersection(self.gi_proxies()))
        self.broadcast("Lyra.Elimination.Message",None);self.broadcast("Lyra.Damage.Taken.Message",None)
        row["proxy_gi_references_after_pre_gc_broadcast"]=len(keys.intersection(self.gi_proxies()))
        self.game.set_property("MusicSystem",self.old_music);self.pending=(row,keys,added);self.gc_ticks=0
        controls.lib("KismetSystemLibrary").call_function("CollectGarbage");self.phase="gc-wait"
    def after_gc(self):
        row,keys,added=self.pending;self.broadcast("Lyra.Elimination.Message",None);self.broadcast("Lyra.Damage.Taken.Message",None)
        row["proxy_gi_references_after_broadcast"]=len(keys.intersection(self.gi_proxies()));row["owned_proxies_inactive_after_broadcast"]=all(not p.call_function("IsActive") for p in added if valid(p))
        row["native_gc_boundary_observed"]=True;self.report["cases"].append(row);self.pending=None;self.trial_index+=1
        if self.trial_index==len(self.plan):self.finish()
        else:self.phase="trial"
    def cleanup(self):
        if hasattr(self,"game"):
            for component in self.components:
                if valid(component):component.call_function("K2_DestroyComponent",component)
            if hasattr(self,"router"):
                self.broadcast("Lyra.Elimination.Message",None);self.broadcast("Lyra.Damage.Taken.Message",None)
            self.game.set_property("MusicSystem",self.old_music);self.report["original_music_pointer_restored"]=self.game.get_property("MusicSystem")==self.old_music
            self.report["all_owned_proxy_gi_references_released"]=not {p.get_path_name() for p in self.owned_proxies if valid(p)}.intersection(self.gi_proxies())
        for sound in self.created_music:
            if valid(sound):sound.call_function("Stop")
            if valid(sound):sound.call_function("K2_DestroyComponent",sound)
        if hasattr(self,"manager_fields"):
            for name,value in self.manager_fields.items():self.manager.set_property(name,value)
            self.report["natural_manager_fields_restored"]=all(self.manager.get_property(name)==value for name,value in self.manager_fields.items())
        for actor in self.actors:
            if valid(actor):actor.call_function("K2_DestroyActor")
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.actors)
        if getattr(self,"probe_root_added",False) and valid(self.probe):self.probe.remove_from_root();self.probe_root_added=False
        self.report["diagnostic_probe_root_removed"]=not getattr(self,"probe_root_added",False)
        if hasattr(self,"health_before"):self.report["player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            if self.phase=="ready":self.ready()
            elif self.phase=="trial":self.trial(*self.plan[self.trial_index])
            elif self.phase=="gc-wait":
                self.gc_ticks+=1
                if self.gc_ticks>=3:self.after_gc()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_MUSIC_LIFECYCLE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_MUSIC_LIFECYCLE_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPMusicLifecycleResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
