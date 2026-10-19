"""Real predicted/remote firing Cue Profiles and typed native weapon payloads."""
import atexit
import copy
import sys
import traceback
import unreal_engine as ue
from . import weapon_ability_fire_network_validation as base,weapon_fire_cue_mixin as policy


class Witness(base.Witness):
    def init_witness(self,result,peer,run):
        super().init_witness(result,peer,run);self.cue_events=[];self.current_cue=None
        self.report.update(cue_handler_replayed=False,cue_assets_or_policy_changed=False)
        self.audio_network="-UEPWeaponAudioNetwork" in sys.argv
        if self.audio_network:self.report.update(manual_audio_registration=False,audio_helpers_preloaded_by_probe=False,audio_profiles_changed_by_probe=False)
    def read_audio(self):
        from .weapon_audio_cold_contract import ROUTERS
        resident={row["target_class"].get_path_name():row for row in ue.get_registered_mixins()};values={}
        for key,(path,attribute) in ROUTERS.items():
            row=resident.get(path)
            if row is None:values[key]=dict(registered=False,counters={});continue
            cdo=row["target_class"].get_cdo();raw=getattr(cdo,attribute,None)
            values[key]=dict(registered=True,selected_profile=str(ue.get_mixin_profile(cdo)),
                counters={name:int(value) for name,value in (raw or {}).items() if isinstance(value,int)})
        return values
    def install(self):
        super().install();owner=self;self.cue_cls=ue.load_class(policy.CLASSES[self.weapon.title()]);ue.register_declared_mixin(self.cue_cls)
        row,=[r for r in ue.get_registered_mixins() if r["target_class"]==self.cue_cls];originals={name:value["python_class"] for name,value in row["profiles"].items()};self.observers[self.cue_cls]=originals
        for profile,source in originals.items():
            def observe(handler,selected):
                def invoke(cue,Target,Parameters,SpawnResults):
                    watched=owner.armed and base.wire.same(base.wire.read(Target),owner.command["source_identity"]);row=None
                    if watched:
                        surface=int(Parameters.PhysicalMaterial.get_property("SurfaceType")) if base.valid(Parameters.PhysicalMaterial) else 0
                        row=dict(profile=selected,target=base.wire.read(Target),location=base.vector(Parameters.Location),normal=base.vector(Parameters.Normal),surface=surface,payloads=[],rifle_sounds=[]);owner.current_cue=row
                        if owner.audio_network:row["audio_before"]=owner.read_audio()
                    try:result=handler(cue,Target,Parameters,SpawnResults)
                    except Exception:
                        owner.report["observation_errors"].append(traceback.format_exc());raise
                    finally:
                        if row is not None:
                            if owner.audio_network:row["audio_after"]=owner.read_audio()
                            orders=policy.evidence(cue)["last_orders"];row["python_order"]=copy.deepcopy(orders[-1]) if selected=="Python" and orders else None
                            owner.cue_events.append(row);owner.current_cue=None
                    return result
                return invoke
            ue.register_mixin_profile(self.cue_cls,profile,type("ObservedNetworkFiringCue"+self.peer+profile,(),dict(OnBurst=observe(source.OnBurst,profile))))
        weapon_cls=ue.load_class("/Game/Weapons/B_Weapon.B_Weapon_C");row,=[r for r in ue.get_registered_mixins() if r["target_class"]==weapon_cls]
        for profile,value in row["profiles"].items():
            source=value["python_class"];methods={name:fn for name,fn in vars(source).items() if not name.startswith("__") and callable(fn)}
            def observe_weapon(handler):
                def invoke(actor,ImpactPositions,ImpactNormals,ImpactSurfaceTypes):
                    if owner.current_cue is not None:owner.current_cue["payloads"].append(dict(positions=[base.vector(v) for v in ImpactPositions],normals=[base.vector(v) for v in ImpactNormals],surfaces=[int(v) for v in ImpactSurfaceTypes]))
                    return handler(actor,ImpactPositions,ImpactNormals,ImpactSurfaceTypes)
                return invoke
            def observe_audio(handler):
                def invoke(actor,Sound,Actor):
                    if owner.current_cue is not None:owner.current_cue["rifle_sounds"].append(dict(sound=base.path(Sound),target=base.wire.read(Actor)))
                    return handler(actor,Sound,Actor)
                return invoke
            methods["Fire"]=observe_weapon(source.Fire);methods["TriggerFireAudio"]=observe_audio(source.TriggerFireAudio)
            ue.register_mixin_profile(weapon_cls,profile,type("ObservedNetworkCuePayload"+self.peer+profile,(),methods))
    def arm(self):
        super().arm();self.cue_events=[];self.current_cue=None;self.select_profile(self.cue_cls.get_cdo(),self.command["profile"])
        if self.audio_network:self.audio_case_before=self.read_audio()
    def snapshot(self):
        row=super().snapshot();row["native_firing_cues"]=copy.deepcopy(self.cue_events)
        if self.audio_network:row.update(audio_case_before=copy.deepcopy(self.audio_case_before),audio_case_after=self.read_audio())
        return row


class Client(Witness,base.Client):
    def prepare(self):
        result=super().prepare()
        model=base.capture(self.controller);current=self.controller.get_controlled_pawn();item=base.services(self.controller)[1].call_function("GetActiveSlotItem")
        asc=base.ability_system(self.pawn)
        resident=any(base.valid(spec.Ability) and spec.Ability.get_class().get_path_name()==base.WEAPONS[self.weapon] and any(base.valid(v) for v in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances)) for spec in asc.get_property("ActivatableAbilities").Items) if base.valid(asc) else False
        self.report["cue_prepare_readiness"]=dict(observer_pawn=base.path(self.pawn),controller_pawn=base.path(current),same_pawn=current==self.pawn,
            actual_inventory=model,expected_ammo=self.command["ammo_before"][self.peer],actual_ammo=base.ammo_policy.ammo(item)[0] if base.valid(item) else None,
            source_present=self.find_identity(self.command["source_identity"]) is not None,target_binding=base.binding_ready(self.find_identity(self.command["target_identity"])),
            humans_ready=self.humans_for(self.command) is not None,own_ability_present=resident,diagnostics_after_original_prepare=True,diagnostic_class_preload=False)
        return result
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_CUE_NETWORK_SHUTDOWN_"+self.report["status"].upper())


class Server(Witness,base.Server):
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":self.report["status"]="passed"
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_WEAPON_CUE_NETWORK_"+self.report["status"].upper())


if any(value.startswith("-UEPWeaponFireCueNetworkResult=") for value in sys.argv):
    result,peer,run=base.arg("-UEPWeaponFireCueNetworkResult="),base.arg("-UEPJumpPeer="),base.arg("-UEPJumpRun=")
    validation=Server(result,run) if peer=="server" else Client(result,peer,run);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
