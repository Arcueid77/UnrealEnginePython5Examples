"""Original real firing harness plus actual GAS Cue/material and typed payloads."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from . import weapon_ability_fire_validation as firing,weapon_fire_cue_mixin as policy
from .weapon_fire_cue_contract import validate,PROFILES,require


def xyz(value):return [float(value.x),float(value.y),float(value.z)]


class Validation(firing.Validation):
    def __init__(self,result):
        super().__init__(result);self.cue_originals={};self.cue_profiles={};self.cue_classes={};self.cue_events=[];self.current_cue=None;self.controlled_done=set();self.materials=[]
        self.report.update(controlled_cue_cases=[],native_input_cue_cases=[],native_static_audio_abi_preserved=True,cue_handler_replayed=False)
    def begin(self):
        owner=self
        for weapon,path in policy.CLASSES.items():
            cls=ue.load_class(path);ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls]
            self.cue_classes[weapon]=cls;self.cue_profiles[cls]=str(ue.get_mixin_profile(cls.get_cdo()));originals={name:value["python_class"] for name,value in row["profiles"].items()};self.cue_originals[cls]=originals
            for profile,source in originals.items():
                def observe(handler,label,selected):
                    def invoke(cue,Target,Parameters,SpawnResults):
                        row=None
                        if Target==getattr(owner,"pawn",None):
                            surface=int(Parameters.PhysicalMaterial.get_property("SurfaceType")) if firing.valid(Parameters.PhysicalMaterial) else 0
                            row=dict(weapon=label,profile=selected,surface=surface,location=xyz(Parameters.Location),normal=xyz(Parameters.Normal),payloads=[],rifle_sounds=[])
                            owner.current_cue=row
                        try:result=handler(cue,Target,Parameters,SpawnResults)
                        finally:
                            if row is not None:
                                orders=policy.evidence(cue)["last_orders"];row["order"]=copy.deepcopy(orders[-1]) if selected=="Python" and orders else None
                                owner.cue_events.append(row);owner.current_cue=None
                        return result
                    return invoke
                ue.register_mixin_profile(cls,profile,type("ObservedFiringCue"+weapon+profile,(),dict(OnBurst=observe(source.OnBurst,weapon,profile))))
        for surface in (1,4):
            material=ue.new_object(ue.find_class("PhysicalMaterial"));material.set_property("SurfaceType",surface);material.add_to_root();self.materials.append(material)
        super().begin()
    def observe(self,cls):
        super().observe(cls)
        if cls.get_path_name()!="/Game/Weapons/B_Weapon.B_Weapon_C":return
        owner=self;row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls]
        for profile,value in row["profiles"].items():
            source=value["python_class"];methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            def observe_fire(handler):
                def invoke(actor,ImpactPositions,ImpactNormals,ImpactSurfaceTypes):
                    if owner.current_cue is not None:owner.current_cue["payloads"].append(dict(positions=[xyz(p) for p in ImpactPositions],normals=[xyz(n) for n in ImpactNormals],surfaces=[int(s) for s in ImpactSurfaceTypes]))
                    return handler(actor,ImpactPositions,ImpactNormals,ImpactSurfaceTypes)
                return invoke
            def observe_audio(handler):
                def invoke(actor,Sound,Actor):
                    if owner.current_cue is not None:owner.current_cue["rifle_sounds"].append(dict(sound=firing.path(Sound),target_matches=Actor==owner.pawn))
                    return handler(actor,Sound,Actor)
                return invoke
            methods["Fire"]=observe_fire(source.Fire);methods["TriggerFireAudio"]=observe_audio(source.TriggerFireAudio)
            ue.register_mixin_profile(cls,profile,type("ObservedCuePayload"+profile,(),methods))
    def model(self,events):
        require(len(events)==1,"one actual native Cue entry required");event=events[0];payloads=event["payloads"]
        expected=["SendWeaponFire","Weapon.Fire"]+(["Weapon.TriggerFireAudio"] if event["weapon"]=="Rifle" else [])+["SetWeaponSoundParams","EarlyReflections","WhizBy"]
        match=len(payloads)==1 and payloads[0]==dict(positions=[event["location"]],normals=[event["normal"]],surfaces=[event["surface"]])
        return dict(weapon=event["weapon"],profile=event["profile"],surface=event["surface"],native_cue_entries=len(events),native_weapon_fire_entries=len(payloads),typed_payload_matches=match,
            rifle_audio_entries=len(event["rifle_sounds"]),rifle_sound_matches=all(row["sound"]==policy.RIFLE_SOUND and row["target_matches"] for row in event["rifle_sounds"]),python_order_matches=event["order"]==expected,
            native_observation=copy.deepcopy(event))
    def controlled(self,weapon):
        if weapon in self.controlled_done:return
        cls=self.cue_classes[weapon];lib=ue.find_class("AbilitySystemBlueprintLibrary").get_cdo();math=ue.find_class("KismetMathLibrary").get_cdo()
        for profile in PROFILES:
            ue.set_mixin_profile(cls.get_cdo(),profile)
            for material in (None,*self.materials):
                self.cue_events=[];params=lib.call_function("MakeGameplayCueParameters",NormalizedMagnitude=0.,RawMagnitude=0.,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),
                    AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=math.call_function("MakeVector",12000.25,-45.5,456.875),Normal=math.call_function("MakeVector",0.,0.,1.),
                    Instigator=None,EffectCauser=None,SourceObject=None,PhysicalMaterial=material,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
                ue.find_class("GameplayCueFunctionLibrary").get_cdo().call_function("ExecuteGameplayCueOnActor",self.pawn,GameplayTag(TagName="GameplayCue.Weapon."+weapon+".Fire"),params)
                row=self.model(self.cue_events);row["native_gas_cue_requests"]=1;self.report["controlled_cue_cases"].append(row)
        self.controlled_done.add(weapon)
    def prepare_shot(self):
        weapon=self.weapon.title();self.controlled(weapon);super().prepare_shot();ue.set_mixin_profile(self.cue_classes[weapon].get_cdo(),self.profile)
    def start_shot(self):self.cue_events=[];super().start_shot()
    def shot(self):
        before=len(self.report["shots"]);events=self.cue_events
        super().shot()
        if len(self.report["shots"])>before:self.report["native_input_cue_cases"].append(self.model(events))
    def begin_lifecycle_case(self):
        profile=PROFILES[self.lifecycle_index//4];ue.set_mixin_profile(self.cue_classes["Pistol"].get_cdo(),profile);self.cue_events=[];super().begin_lifecycle_case()
    def lifecycle_tick(self):
        before=len(self.report["lifecycle_cases"]);events=self.cue_events;super().lifecycle_tick()
        if len(self.report["lifecycle_cases"])>before:self.report["native_input_cue_cases"].append(self.model(events))
    def cleanup(self):
        super().cleanup();restored=True
        for material in self.materials:
            if firing.valid(material):material.remove_from_root()
        for cls,profiles in self.cue_originals.items():
            ue.set_mixin_profile(cls.get_cdo(),self.cue_profiles[cls])
            for name,source in profiles.items():ue.register_mixin_profile(cls,name,source)
            row,=[r for r in ue.get_registered_mixins() if r["target_class"]==cls];restored&=all(row["profiles"][name]["python_class"] is source for name,source in profiles.items())
        self.report["cue_observers_and_profiles_restored"]=restored
    def finish(self,error=None):
        super().finish(error)
        if self.report["status"]=="awaiting_shutdown":ue.log("UEP_WEAPON_FIRE_CUES_DIFFERENTIAL_PASSED")
        elif self.report["status"]=="failed":ue.log_error("UEP_WEAPON_FIRE_CUES_DIFFERENTIAL_FAILED")
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try:self.report["status"]="passed";validate(self.report)
            except Exception:self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_FIRE_CUES_SHUTDOWN_"+self.report["status"].upper())


result=next((v.split("=",1)[1] for v in sys.argv if v.startswith("-UEPWeaponFireCuesResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
