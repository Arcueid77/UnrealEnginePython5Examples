"""Real child startup/latent continuation/team messages with base-only bindings."""
import atexit
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraVerbMessage
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import music_manager_mixin as controls,music_manager_lifecycle_mixin as lifecycle,music_family_mixin as policy
from .music_family_contract import CLASSES,PLAN,require,validate


def path(obj):return obj.get_path_name() if valid(obj) else None
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.components=[];self.owned_proxies=[];self.roots=[];self.current=None;self.positives=[]
        self.report=dict(status="running",error=None,cases=[],full_acceptance=False,network_acceptance=False,begin_play_replayed=False,delay_callback_replayed=False,
            message_callback_replayed=False,python_subscription_roots_added=False,production_proxies_cancelled_by_probe=False,cpp_compile_executed=False)
    def own(self):
        actor=self.world.actor_spawn(ue.find_class("Actor"));actor.call_function("SetReplicates",False);self.actors.append(actor);return actor
    def proxies(self):return {p.get_path_name():p for p in ue.tobject_iterator(ue.find_class("AsyncAction_ListenForGameplayMessage")) if valid(p)}
    def gi_refs(self):return {p.get_path_name() for p in self.game.get_property("ReferencedObjects") if valid(p)}
    def begin(self):
        from unreal_engine.structs import LyraControlPointStatusMessage
        self.payload_type=LyraControlPointStatusMessage
        self.health_before=float(self.health.call_function("GetHealth"));self.game=self.statics.call_function("GetGameInstance",self.world);self.old_music=self.game.get_property("MusicSystem")
        self.cls=ue.load_class(controls.CLASS);self.manager=self.statics.call_function("GetGameState",self.world).get_component_by_type(self.cls);self.fields={n:self.manager.get_property(n) for n in ("Music System","Alpha_Intensity","Alpha_Mvmt","bIsMenu")}
        self.router=controls.lib("SubsystemBlueprintLibrary").call_function("GetGameInstanceSubsystem",self.world,ue.find_class("GameplayMessageSubsystem"))
        self.teams=controls.lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"));part,self.team=self.teams.call_function("FindTeamFromActor",self.pawn)
        self.probe=ue.load_class("/Game/UEPValidation/BP_MusicFamilyProbe.BP_MusicFamilyProbe_C").get_cdo();self.verb=ue.load_class("/Game/UEPValidation/BP_MusicListenerProbe.BP_MusicListenerProbe_C").get_cdo()
        for obj in (self.probe,self.verb):
            if not obj.is_rooted():obj.add_to_root();self.roots.append(obj)
        self.observe_stinger();self.index=0;self.phase="trial"
    def observe_stinger(self):
        row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.cls];self.original_classes={name:value["python_class"] for name,value in row["profiles"].items()};owner=self
        for profile,source in self.original_classes.items():
            methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            def observed(handler):
                def invoke(component,Positive):
                    if component==owner.current:owner.positives.append(bool(Positive))
                    return handler(component,Positive)
                invoke.override="Fire Stinger";return invoke
            methods["Stinger"]=observed(source.Stinger);ue.register_mixin_profile(self.cls,profile,type("ObservedFamilyStinger"+profile,(),methods))
    def start_trial(self):
        label,profile,mode=PLAN[self.index];owner=self.own();self.before=set(self.proxies());component=ue.new_object(ue.load_class(CLASSES[label]),owner);self.current=component;self.components.append(component);ue.set_mixin_profile(component,profile)
        self.start_time=self.game_time();component.register_component();component.call_function("SetComponentTickEnabled",False)
        base=lifecycle.evidence(component);self.row=dict(index=self.index,**{"class":label},profile=profile,mode=mode,native_parent_begin_calls=base["begin_python"]+base["begin_fallback"],immediate_proxy_count=len(set(self.proxies())-self.before))
        root=owner.add_actor_root_component(ue.find_class("SceneComponent"),"UEPFamilyRoot");self.audio=owner.add_actor_component(ue.find_class("AudioComponent"),"UEPFamilyAudio",root);self.audio.set_property("bAutoDestroy",False)
        self.audio.call_function("SetSound",ue.load_object(ue.find_class("SoundBase"),lifecycle.SOUND));self.audio.call_function("Play",0.);component.set_property("Music System",self.audio)
        self.switched=False;self.destroyed=False;self.after_seen=False;self.phase="waiting"
    def waiting(self):
        label,profile,mode=PLAN[self.index];elapsed=self.game_time()-self.start_time
        if elapsed>=.08 and not self.switched and mode=="switch":ue.set_mixin_profile(self.current,"Python" if profile=="BlueprintFallback" else "BlueprintFallback");self.switched=True
        if elapsed>=.08 and not self.destroyed and mode=="destroy":self.current.call_function("K2_DestroyComponent",self.current);self.destroyed=True
        stats=policy.evidence(self.current) if valid(self.current) else None;after=(stats["after_python"]+stats["after_fallback"]) if stats else 0
        if after and not self.after_seen:self.row["after_delay_elapsed"]=elapsed;self.row["after_delay_profile"]=str(ue.get_mixin_profile(self.current));self.after_seen=True
        if elapsed<.35:return
        self.row["after_delay_calls"]=after;added=[p for name,p in self.proxies().items() if name not in self.before];self.owned_proxies.extend(added);self.row["proxy_count_after_delay"]=len(added)
        if mode!="destroy":
            params={str(p.ParamName):p for p in self.audio.get_property("InstanceParameters")};self.row["audio_menu"]=bool(params["bIsMenu"].BoolParam) if "bIsMenu" in params else None;self.row["component_menu"]=bool(self.current.get_property("bIsMenu"))
            if label=="control_point":
                self.positives=[];before=stats["captured_python"]+stats["captured_fallback"]
                for team in (self.team,self.team+1,-1):self.probe.call_function("BroadcastCaptured",self.router,GameplayTag(TagName="ShooterGame.ControlPoint.Captured.Message"),self.payload_type(OwnerTeamID=team))
                self.row["stinger_positive_arguments"]=list(self.positives);self.row["captured_callback_entries"]=stats["captured_python"]+stats["captured_fallback"]-before
            self.current.call_function("K2_DestroyComponent",self.current)
        self.audio.call_function("Stop");self.keys={p.get_path_name() for p in added};self.pending_proxies=added;self.current=None;self.gc_ticks=0;controls.lib("KismetSystemLibrary").call_function("CollectGarbage");self.phase="gc-wait"
    def release_messages(self):
        for channel in ("Lyra.Elimination.Message","Lyra.Damage.Taken.Message"):self.verb.call_function("BroadcastVerb",self.router,GameplayTag(TagName=channel),LyraVerbMessage())
        self.probe.call_function("BroadcastCaptured",self.router,GameplayTag(TagName="ShooterGame.ControlPoint.Captured.Message"),self.payload_type(OwnerTeamID=-1))
    def after_gc(self):
        self.release_messages();self.row["proxy_refs_after_gc_and_messages"]=len(self.keys.intersection(self.gi_refs()));self.row["proxies_inactive_after_gc_and_messages"]=all(not p.call_function("IsActive") for p in self.pending_proxies if valid(p))
        self.report["cases"].append(self.row);self.index+=1
        if self.index==len(PLAN):self.finish()
        else:self.phase="trial"
    def cleanup(self):
        for component in self.components:
            if valid(component):component.call_function("K2_DestroyComponent",component)
        if hasattr(self,"router"):self.release_messages()
        if hasattr(self,"original_classes"):
            for name,source in self.original_classes.items():ue.register_mixin_profile(self.cls,name,source)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.cls];self.report["base_profile_family_restored"]=all(row["profiles"][name]["python_class"] is source for name,source in self.original_classes.items())
        if hasattr(self,"fields"):
            for name,value in self.fields.items():self.manager.set_property(name,value)
            self.report["natural_manager_fields_restored"]=all(self.manager.get_property(name)==value for name,value in self.fields.items());self.report["original_gi_music_preserved"]=self.game.get_property("MusicSystem")==self.old_music
            self.report["all_owned_proxy_gi_references_released"]=not {p.get_path_name() for p in self.owned_proxies if valid(p)}.intersection(self.gi_refs())
        for actor in self.actors:
            if valid(actor):actor.call_function("K2_DestroyActor")
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.actors)
        for obj in self.roots:
            if valid(obj):obj.remove_from_root()
        self.report["diagnostic_probe_roots_removed"]=all(not valid(obj) or not obj.is_rooted() for obj in self.roots)
        if hasattr(self,"health_before"):self.report["player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            if self.phase=="ready":self.ready()
            elif self.phase=="trial":self.start_trial()
            elif self.phase=="waiting":self.waiting()
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
        (ue.log_error if error else ue.log)("UEP_MUSIC_FAMILY_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_MUSIC_FAMILY_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPMusicFamilyResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
