"""Observe natural offline sound/effect creation without preset initialization calls."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .weapon_audio_cold_validation import Validation as Cold
from .weapon_audio_effect_contract import validate


def tap_model(value):return {field:int(getattr(value,field)) if field in ("TapId","TapLineMode","OutputChannel") else float(getattr(value,field)) for field in value.fields()}
def resident(name):
    try:return ue.find_object(name)
    except Exception:return None


class Validation(Cold):
    def __init__(self,result):
        super().__init__(result);self.components_seen={};self.initial_authored=None;self.trigger_events=[]
        self.report.update(effect_shots=[],preset_initialized_by_probe=False,preset_settings_written_by_probe=False,fixture_taps_added=False,
            audio_components_created_by_probe=False,physical_audio_output_tested=False,waveform_output_accepted=False,authored_settings_unchanged=True)
    def preset_state(self):
        preset=resident("TAP_EarlyReflections")
        if not valid(preset):return dict(resident=False)
        settings=preset.get_property("Settings");authored=[tap_model(tap) for tap in settings.Taps];ids,=preset.call_function("GetTapIds")
        if self.initial_authored is None:self.initial_authored=authored
        self.report["authored_settings_unchanged"]&=authored==self.initial_authored
        submix=resident("EarlyReflectionsSubmix")
        chain=[value.get_path_name() for value in submix.get_property("SubmixEffectChain") if valid(value)] if valid(submix) else []
        return dict(resident=True,authored_taps=authored,dynamic_tap_ids=list(ids),dynamic_taps=[tap_model(preset.call_function("GetTap",tap)[0]) for tap in ids],submix_effect_chain=chain)
    def audio_objects(self):return [obj for obj in self.world.all_objects() if valid(obj) and obj.is_a(ue.find_class("AudioComponent"))]
    def record_component(self,component):
        if not valid(component):return
        sound=component.get_property("Sound")
        if not valid(sound) or self.selected not in sound.get_path_name().lower():return
        name=component.get_path_name();row=dict(path=name,sound=sound.get_path_name(),playing=bool(component.call_function("IsPlaying")),auto_destroy=bool(component.get_property("bAutoDestroy")),
            reused_from_before_shot=name in self.component_baseline,
            parameters={str(p.ParamName):dict(kind=int(p.ParamType),integer=int(p.IntParam),scalar=float(p.FloatParam)) for p in component.get_property("InstanceParameters")})
        previous=self.components_seen.get(name)
        if previous is not None:row["playing"]|=previous["playing"]
        self.components_seen[name]=row
    def sample_components(self):
        if not self.recording:return
        for component in self.audio_objects():
            name=component.get_path_name()
            if name in self.component_baseline:continue
            self.record_component(component)
    def observe(self,cls):
        super().observe(cls)
        if cls.get_path_name()!="/Game/Weapons/B_Weapon.B_Weapon_C":return
        owner=self;binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==cls]
        for profile,value in binding["profiles"].items():
            source=value["python_class"];methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            def observe_trigger(handler):
                def invoke(actor,Sound,Actor):
                    before=(getattr(actor,"_uep_weapon_actor_helpers",None) or {}).get("audio_triggers",0)
                    result=handler(actor,Sound,Actor)
                    if owner.recording:
                        component=actor.get_property("AudioComponent");after=(getattr(actor,"_uep_weapon_actor_helpers",None) or {}).get("audio_triggers",0)
                        owner.trigger_events.append(dict(component=component.get_path_name() if valid(component) else None,native_fire_trigger_delta=after-before))
                        owner.record_component(component)
                    return result
                return invoke
            methods["TriggerFireAudio"]=observe_trigger(source.TriggerFireAudio)
            ue.register_mixin_profile(cls,profile,type("ObservedNaturalAudioTrigger"+profile,(),methods))
    def begin(self):
        self.report["preset_before_gameplay_setup"]=self.preset_state();super().begin()
    def start_shot(self):
        self.components_seen={};self.trigger_events=[];self.component_baseline={obj.get_path_name() for obj in self.audio_objects()};self.preset_before_shot=self.preset_state();super().start_shot()
    def shot(self):
        before=len(self.report["shots"]);self.sample_components();super().shot()
        if len(self.report["shots"])!=before:
            self.report["effect_shots"].append(dict(index=before,preset_before=self.preset_before_shot,preset_after=self.preset_state(),weapon_components=list(self.components_seen.values()),trigger_events=list(self.trigger_events)))
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_WEAPON_AUDIO_EFFECT_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_AUDIO_EFFECT_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponAudioEffectResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
