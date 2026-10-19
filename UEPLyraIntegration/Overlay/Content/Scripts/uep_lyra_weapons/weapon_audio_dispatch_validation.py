"""Native Blueprint/Python static calls: messages, AudioComponent and preset state."""
import atexit
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayCueNotify_SpawnResult,TapDelayInfo
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_world.effect_pad_mixin import valid
from . import weapon_audio_dispatch_mixin as policy
from .weapon_audio_dispatch_contract import TAP_PLAN,PARAM_PLAN,FIRE_PLAN,DEBUG_PLAN,PROFILES,require,validate
from . import weapon_audio_math_mixin as math_policy
from .weapon_audio_math_validation import model
from .weapon_audio_math_contract import SIDE_PLAN,WHIZ_PLAN


def tap_model(value):return {field:int(getattr(value,field)) if field in ("TapId","TapLineMode","OutputChannel") else float(getattr(value,field)) for field in value.fields()}
def parameters(audio):return {str(p.ParamName):int(p.IntParam) for p in audio.get_property("InstanceParameters")}


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.music_events=[]
        self.report=dict(status="running",error=None,tap_pairs=[],parameter_pairs=[],fire_pairs=[],debug_pairs=[],math_regression=[],
            full_acceptance=False,network_acceptance=False,audible_playback_tested=False,debug_pixels_tested=False,cpp_compile_executed=False,
            static_functions_registered_as_mixins=False,preset_asset_saved=False)
    def invoke(self,method,args,caller):return (self.caller if caller else self.library).call_function("Call"+policy.METHODS[method] if caller else method,*args,self.world)
    def trial(self,method,index,run,expected):
        values=[];counts=[]
        for profile in PROFILES:
            ue.set_mixin_profile(self.router,profile);before=dict(policy.evidence(self.router))
            values.extend(run(caller) for caller in (False,True));counts.append(policy.evidence(self.router)[method+("_fallback" if profile=="BlueprintFallback" else "_python")]-before[method+("_fallback" if profile=="BlueprintFallback" else "_python")])
        return dict(index=index,observations=values,fallback_dispatches=counts[0],python_dispatches=counts[1],expected_behavior=all(expected(value) for value in values))
    def own(self,cls):
        actor=self.world.actor_spawn(ue.find_class(cls));actor.call_function("SetReplicates",False);self.actors.append(actor);return actor
    def begin(self):
        self.player_health=float(self.health.call_function("GetHealth"));self.instigator=self.pawn.get_property("Instigator")
        self.library_cls=ue.load_class("/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions_C");self.library=self.library_cls.get_cdo()
        self.signatures={name:ue.describe_function(self.library_cls,name) for name in tuple(policy.METHODS)+tuple(math_policy.METHODS)}
        self.router_cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.router_cls);self.router=self.router_cls.get_cdo();self.router_original=str(ue.get_mixin_profile(self.router))
        self.caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioDispatchCaller.BP_WeaponAudioDispatchCaller_C").get_cdo()
        self.remote=self.own("Pawn");self.fixture=self.own("Actor");root=self.fixture.add_actor_root_component(ue.find_class("SceneComponent"),"UEPAudioRoot")
        self.audios=[self.fixture.add_actor_component(ue.find_class("AudioComponent"),"UEPAudio"+str(i),root) for i in range(2)]
        self.cam=self.controller.get_property("PlayerCameraManager");self.preset=policy.tap_preset();ids,=self.preset.call_function("GetTapIds")
        self.preset_before={int(i):tap_model(self.preset.call_function("GetTap",i)[0]) for i in ids};self.tap_id,=self.preset.call_function("AddTap")
        self.report.update(local_pawn=self.pawn.get_path_name(),owned_tap_id=self.tap_id,remote_pawn_seed=ord(policy.lib("KismetSystemLibrary").call_function("GetDisplayName",self.remote)[-1]))
        self.observe_music();self.fire_trials();self.param_trials();self.tap_trials();self.debug_trials();self.math_trials()
        self.report["original_static_signatures_preserved"]=all(ue.describe_function(self.library_cls,name)==value for name,value in self.signatures.items());self.finish()
    def observe_music(self):
        state=self.statics.call_function("GetGameState",self.world);self.manager=state.get_component_by_type(ue.load_class(policy.MUSIC));require(valid(self.manager),"actual native music manager required")
        self.music_cls=self.manager.get_class();require(not any(r["target_class"]==self.music_cls for r in ue.get_registered_mixins()),"music manager observer must not replace an existing Mixin")
        owner=self
        def receive(component,Player,Strength):
            owner.music_events.append(dict(player=Player.get_path_name() if valid(Player) else None,strength=float(Strength)))
            return component.call_mixin_original("Receive Weapon Fire",Player,Strength)
        receive.override="Receive Weapon Fire"
        ue.register_mixin_profile(self.music_cls,"UEPAudioObserve",type("UEPAudioMusicObserver",(),dict(Receive=receive)));self.music_observing=True;ue.set_mixin_profile(self.manager,"UEPAudioObserve")
    def fire_trials(self):
        for index,(label,strength) in enumerate(FIRE_PLAN):
            player={"local":self.pawn,"remote":self.remote,"null":None}[label]
            def run(caller):
                start=len(self.music_events);self.invoke("SendWeaponFire",[player,strength],caller);return self.music_events[start:]
            expected=[dict(player=self.pawn.get_path_name(),strength=strength)] if label=="local" else []
            self.report["fire_pairs"].append(self.trial("SendWeaponFire",index,run,lambda value:value==expected))
    def param_trials(self):
        quickbar=self.controller.get_component_by_type(ue.find_class("LyraQuickBarComponent"));item=quickbar.call_function("GetActiveSlotItem")
        tag=ue.find_struct("GameplayTag")(TagName="Lyra.ShooterGame.Weapon.MagazineAmmo")
        ammo=int(item.call_function("GetStatTagStackCount",tag)) if valid(item) and item.call_function("HasStatTag",tag) else 0
        self.report["actual_magazine_ammo"]=ammo
        for index,label in enumerate(PARAM_PLAN):
            self.pawn.set_property("Instigator",None if label=="invalid-instigator" else self.pawn);self.remote.set_property("Instigator",self.remote if label=="no-controller" else self.pawn)
            actor=self.remote if label in ("remote","no-controller") else self.fixture if label=="not-pawn" else None if label=="null" else self.pawn
            spawn=GameplayCueNotify_SpawnResult(AudioComponents=[] if label=="empty-audio" else [self.audios[0],None,self.audios[1]])
            def run(caller):
                for audio in self.audios:
                    audio.call_function("ResetParameters")
                    for key,value in (("PawnSeed",321),("MagazineAmmo",777),("Unrelated",19)):audio.call_function("SetIntParameter",key,value)
                self.invoke("SetWeaponSoundParams",[actor,spawn],caller);return [parameters(audio) for audio in self.audios]
            expected=dict(PawnSeed=-1,MagazineAmmo=ammo,Unrelated=19) if label=="local" else dict(PawnSeed=321,MagazineAmmo=777,Unrelated=19)
            if label=="remote":expected["PawnSeed"]=ord(policy.lib("KismetSystemLibrary").call_function("GetDisplayName",actor)[-1])
            self.report["parameter_pairs"].append(self.trial("SetWeaponSoundParams",index,run,lambda value:value==[expected,expected]))
        self.pawn.set_property("Instigator",self.instigator)
    def tap_trials(self):
        location=self.cam.call_function("GetCameraLocation")
        right=policy.lib("KismetMathLibrary").call_function("GetRightVector",self.cam.call_function("GetCameraRotation"))
        self.report.update(camera_location=[float(location.x),float(location.y),float(location.z)],camera_right=[float(right.x),float(right.y),float(right.z)])
        for index,(hit,travel,distance,offset) in enumerate(TAP_PLAN):
            point=ue.FVector(location.x+offset[0],location.y+offset[1],location.z+offset[2]);listener=ue.FVector(point.x+distance,point.y+distance/3.,point.z)
            initial=TapDelayInfo(TapLineMode=2,DelayLength=123.25,Gain=-3.5,OutputChannel=7,PanInDegrees=-67.125)
            def run(caller):
                self.preset.call_function("SetTap",self.tap_id,initial)
                self.invoke("Calculate Tap Properties",["DisconnectedDebug",self.cam if hit else None,point,self.tap_id,-9876.5-index,travel,hit,listener],caller)
                return tap_model(self.preset.call_function("GetTap",self.tap_id)[0])
            def expected(value):return value["TapId"]==self.tap_id and value["TapLineMode"]==1 and value["OutputChannel"]==0 and (hit or (value["DelayLength"]==123.25 and value["Gain"]==-60. and value["PanInDegrees"]==-67.125))
            self.report["tap_pairs"].append(self.trial("Calculate Tap Properties",index,run,expected))
    def debug_trials(self):
        for index,args in enumerate(DEBUG_PLAN):
            self.report["debug_pairs"].append(self.trial("DebugPrintTap",index,lambda caller:self.invoke("DebugPrintTap",list(args),caller) is None,lambda value:value is True))
    def math_trials(self):
        cls=ue.load_class(math_policy.CLASS);ue.register_declared_mixin(cls);router=cls.get_cdo();original=str(ue.get_mixin_profile(router))
        caller=ue.load_class("/Game/UEPValidation/BP_WeaponAudioMathCaller.BP_WeaponAudioMathCaller_C").get_cdo()
        try:
            for method,plan,call in (("GetSideReflectionAngles",SIDE_PLAN,"CallSides"),("Calculate Whiz By",WHIZ_PLAN,"CallWhiz")):
                for args in (plan[0],plan[len(plan)//3],plan[len(plan)//2],plan[-1]):
                    args=[ue.FVector(*v) if isinstance(v,tuple) else v for v in args];values=[]
                    for profile in PROFILES:
                        ue.set_mixin_profile(router,profile)
                        for target,name in ((self.library,method),(caller,call)):values.append(model(target.call_function(name,*args,self.world)))
                    self.report["math_regression"].append(values.count(values[0])==4)
        finally:ue.set_mixin_profile(router,original)
    def cleanup(self):
        if hasattr(self,"router_original"):
            ue.set_mixin_profile(self.router,self.router_original);self.report["router_profile_restored"]=str(ue.get_mixin_profile(self.router))==self.router_original
        if getattr(self,"music_observing",False):ue.unregister_mixin(self.music_cls);self.music_observing=False
        self.report["music_observer_removed"]=not hasattr(self,"music_cls") or not any(r["target_class"]==self.music_cls for r in ue.get_registered_mixins())
        if hasattr(self,"tap_id"):self.preset.call_function("RemoveTap",self.tap_id)
        if hasattr(self,"preset_before"):
            ids,=self.preset.call_function("GetTapIds");after={int(i):tap_model(self.preset.call_function("GetTap",i)[0]) for i in ids}
            self.report["preset_state_restored"]=after==self.preset_before
        for actor in self.actors:
            if valid(actor):actor.call_function("K2_DestroyActor")
        self.report["owned_actors_destroyed"]=all(not valid(actor) for actor in self.actors)
        if hasattr(self,"instigator"):
            self.pawn.set_property("Instigator",self.instigator);self.report["original_instigator_restored"]=self.pawn.get_property("Instigator")==self.instigator
            self.report["original_player_health_unchanged"]=float(self.health.call_function("GetHealth"))==self.player_health
    def tick(self,seconds):
        if self.finished:return False
        try:self.ready();self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_DISPATCH_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_DISPATCH_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponAudioDispatchResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
