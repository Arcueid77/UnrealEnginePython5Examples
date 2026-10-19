"""Retain three complete firing Cue graphs/CDOs and expose one method/Profile."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from uep_lyra_weapons.weapon_fire_cue_mixin import WEAPONS,CLASSES


def generate(stage):
    official=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_WeaponFireCueMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_fire_cue_mixin",PythonClass="LyraWeaponFireCue"+name+"Profile") for name in ("Python","BlueprintFallback")]
    records=[];assets=[];references={};counts={}
    for name,nodes in zip(WEAPONS,(26,30,20)):
        relative="Plugins/GameFeatures/ShooterCore/Content/Weapons/"+name+"/GCN_Weapon_"+name+"_Fire.uasset";file=official/relative;digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if hashlib.sha256((stage/relative).read_bytes()).hexdigest()!=digest:raise RuntimeError("fresh original firing Cue required: "+name)
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[name].removesuffix("_C"));ue.unregister_all_mixins()
        before=snapshot(bp,"fire-cue-"+name+"-before");class_name=bp.GeneratedClass.get_path_name();signature=ue.describe_function(bp.GeneratedClass,"OnBurst")
        originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
        if {g.get_name():len(keys) for g,keys in originals}!={"OnBurst":nodes,"EventGraph":0}:raise RuntimeError("original firing Cue graph footprint differs")
        hashes={g.get_name():semantics(g,keys,set()) for g,keys in originals}
        ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or ue.describe_function(bp.GeneratedClass,"OnBurst")!=signature or snapshot(bp,"fire-cue-"+name+"-after")!=before:raise RuntimeError("original Cue class/full CDO/signature changed")
        if any(len(g.Nodes)!=len(keys) or semantics(g,keys,set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError("original Cue business graph changed")
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass]
            value={key:len(profile["functions"]) for key,profile in row["profiles"].items()}
            if value!=dict(Python=1,BlueprintFallback=1):raise RuntimeError("one original OnBurst/Profile required")
            counts[name]=value
        finally:ue.unregister_all_mixins()
        bp.save_package();assets.append(relative);references[str(file)]=digest;records.append(dict(weapon=name,path=class_name,original_nodes=nodes,original_graphs=hashes,signature=signature))
    mixin.save_package();assets.append("Content/UEPMixins/DA_WeaponFireCueMixin.uasset")
    return dict(status="passed",kind="weaponfirecues",runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_preserved=True,original_graphs_unmodified=True,original_graph_nodes=76,native_end_adapter_nodes=0,transport_nodes=0,new_business_nodes=0,
        native_register_restore_passed=True,actual_registered_profile_method_counts=counts,original_native_burst_effects_preserved=True,
        static_audio_library_business_migrated=False,records=records,assets=assets,reference_hashes=references)
