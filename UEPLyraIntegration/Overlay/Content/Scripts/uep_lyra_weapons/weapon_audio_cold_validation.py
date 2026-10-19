"""Real equipped input, no audio/Cue class preload or explicit registration."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from uep_lyra_abilities import reload_weapon_fixture as fixtures,reload_magazine_mixin as ammo_policy
from uep_lyra_hud.weapon_validation_helpers import set_stat
from . import weapon_ability_fire_validation as firing
from .weapon_audio_cold_contract import ROUTERS,validate


class Validation(firing.Validation):
    def __init__(self,result):
        super().__init__(result);self.selected=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPAudioColdWeapon=")),"pistol")
        self.report.update(selected_weapon=self.selected,cold_shots=[],manual_audio_registration=False,audio_helpers_preloaded_by_probe=False,
            audio_profiles_changed_by_probe=False,cue_profiles_changed_by_probe=False,cue_handler_replayed=False,native_global_seed_api_used=False,default_field_property_preserved=True)
    def snapshot(self):
        paths=dict(ROUTERS);name=self.selected.title();paths["cue"]=("/ShooterCore/Weapons/"+name+"/GCN_Weapon_"+name+"_Fire.GCN_Weapon_"+name+"_Fire_C","_uep_weapon_fire_cue")
        resident={row["target_class"].get_path_name():row for row in ue.get_registered_mixins()};values={}
        for key,(path,attribute) in paths.items():
            row=resident.get(path)
            if row is None:values[key]=dict(registered=False,counters={});continue
            # A declared registered class already has a CDO. Do not load absent
            # classes, register bindings or call production evidence() helpers.
            cdo=row["target_class"].get_cdo();raw=getattr(cdo,attribute,None)
            values[key]=dict(registered=True,selected_profile=str(ue.get_mixin_profile(cdo)),
                counters={name:int(value) for name,value in (raw or {}).items() if isinstance(value,int)},
                providers={name:value["python_class"].__module__+"."+value["python_class"].__name__ for name,value in row["profiles"].items()})
        return values
    def begin(self):
        self.report["before_gameplay_setup"]=self.snapshot()
        bridge=firing.policy.lib("UEPLyraBridgeLibrary").call_function("GetBridgeForWorld",self.world);self.report["native_mode"]=str(bridge.call_function("CaptureSnapshot").NetMode)
        firing.require(self.report["native_mode"]=="Standalone","natural cold fire requires standalone")
        self.player_health=float(self.health.call_function("GetHealth"));self.original_control=self.controller.call_function("GetControlRotation")
        self.original=fixtures.baseline(self.controller);self.original_ammo=ammo_policy.ammo(firing.services(self.controller)[1].call_function("GetActiveSlotItem"))
        self.actions=[ue.load_object(ue.find_class("InputAction"),"/Game/Input/Actions/"+name+"."+name) for name in ("IA_Weapon_Fire","IA_Weapon_Fire_Auto")]
        self.team=firing.policy.lib("SubsystemBlueprintLibrary").call_function("GetWorldSubsystem",self.world,ue.find_class("LyraTeamSubsystem"))
        state=self.statics.call_function("GetGameState",self.world);self.bot_component=state.get_component_by_type(ue.find_class("LyraBotCreationComponent"))
        self.observe(ue.load_class("/Game/Weapons/B_Weapon.B_Weapon_C"));self.observe(ue.load_class(firing.policy.CLASS));self.next_weapon()
    def montage_trials(self,dummy):pass
    def next_weapon(self):
        if self.index>=2:self.finish();return
        if self.weapon!=self.selected:
            self.restore_weapon();self.weapon=self.selected
            if self.weapon!="pistol":self.fixture=fixtures.install(self.controller,self.weapon)
            self.enter("weapon-ready");return
        self.prepare_shot()
    def prepare_shot(self):
        self.profile=str(ue.get_mixin_profile(self.ability));self.saved_field=self.ability.get_property("FieldActorToSpawnOnImpact");self.field_enabled=self.saved_field is not None
        firing.require(not self.ability.get_property("bIsActive"),"previous natural fire is still active")
        set_stat(self.item,ammo_policy.MAGAZINE,max(3,self.weapon_ammo[1]//2));self.enter("enemy-ready")
    def start_shot(self):
        self.audio_before=copy.deepcopy(self.snapshot());super().start_shot()
    def shot(self):
        before=len(self.report["shots"]);super().shot()
        if len(self.report["shots"])!=before:
            self.report["cold_shots"].append(dict(index=before,kind="first" if before==0 else "repeat",before=self.audio_before,after=copy.deepcopy(self.snapshot())))
            self.report["default_field_property_preserved"]&=self.ability.get_property("FieldActorToSpawnOnImpact")==self.saved_field
    def advance(self):self.index+=1;self.enter("cold-advance")
    def start_failure(self):self.advance()
    def tick(self,seconds):
        if self.finished:return False
        if self.phase=="cold-advance":
            try:self.next_weapon();self.write();return not self.finished
            except Exception:self.finish(traceback.format_exc());return False
        return super().tick(seconds)
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_COLD_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_COLD_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponAudioColdResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
