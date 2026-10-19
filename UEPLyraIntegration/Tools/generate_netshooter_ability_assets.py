"""Retain all prototype ability graphs and compiler-owned montage callbacks."""
import hashlib
import json
import struct
import zlib
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from uep_lyra_weapons.netshooter_ability_mixin import METHODS,CALLBACKS,BIND

PACKAGE="/ShooterCore/Weapons/NetShooter_PROTO/GA_WeaponNetShooter.GA_WeaponNetShooter"
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/Weapons/NetShooter_PROTO/GA_WeaponNetShooter.uasset"
PARENT="Content/Weapons/GA_Weapon_Fire.uasset"


def generate(stage):
    official=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    digest=hashlib.sha256(official.read_bytes()).hexdigest();parent_hash=hashlib.sha256((stage/PARENT).read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError("fresh original NetShooter ability required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"netshooter-ability-before");class_name=bp.GeneratedClass.get_path_name()
    if bp.ParentClass.get_path_name()!="/Game/Weapons/GA_Weapon_Fire.GA_Weapon_Fire_C":raise RuntimeError("original shared-fire parent required")
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if {g.get_name():len(keys) for g,keys in originals}!={"EventGraph":22,"GetDirectionAndLocation_2":9,"TempHackOffsetFX_2":17}:raise RuntimeError("original NetShooter ability graph footprint differs")
    hashes={g.get_name():semantics(g,keys,set()) for g,keys in originals};variables=[str(v.VarName) for v in bp.NewVariables]
    graph,=[g for g,_ in originals if g.get_name()=="EventGraph"];nodes={n.get_name():n for n in graph.Nodes};task=nodes["K2Node_LatentAbilityCall_0"]
    parts=[int(task.NodeGuid.get_field(key))&0xffffffff for key in ("A","B","C","D")]
    suffix="".join(format(value,"08X") for value in parts[:3])+format(zlib.crc32(struct.pack("<4I",*parts)),"08X")
    if CALLBACKS!={event:event+"_"+suffix for event in CALLBACKS}:raise RuntimeError("original NetShooter montage callback identities differ")
    if nodes["K2Node_Event_2"].node_find_pin("then").get_linked_to():raise RuntimeError("original target-data override must remain empty")
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in METHODS}
    binding=ue.blueprint_add_function(bp,BIND);entry=binding.Nodes[0];task_class=ue.find_class("AbilityTask_PlayMontageAndWait")
    entry.node_create_pin(1,EdGraphPinType(PinCategory="object",PinSubCategoryObject=task_class),"Task")
    owner=binding.graph_add_node(K2Node_Self);previous=entry
    for event,callback in CALLBACKS.items():
        add=binding.graph_add_node(K2Node_AddDelegate);add.DelegateReference=MemberReference(MemberName=event,MemberParent=task_class,bSelfContext=False);binding.graph_reconstruct_node(add)
        delegate=binding.graph_add_node(K2Node_CreateDelegate);connect(entry,"Task",add,"self");connect(previous,"then",add,"execute")
        connect(owner,"self",delegate,"self");connect(delegate,"OutputDelegate",add,"Delegate");delegate.SelectedFunctionName=callback;previous=add
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_NetShooterAbilityMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.netshooter_ability_mixin",PythonClass="LyraNetShooterAbility"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"netshooter-ability-after")!=before:raise RuntimeError("original NetShooter ability class/full CDO changed")
    if len(binding.Nodes)!=8 or any(semantics(g,keys,set())!=hashes[g.get_name()] or len(g.Nodes)!=len(keys) for g,keys in originals):raise RuntimeError("original NetShooter business graphs changed")
    if [str(v.VarName) for v in bp.NewVariables]!=variables or any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()):raise RuntimeError("original signatures or inherited selector changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass]
        counts={key:len(value["functions"]) for key,value in row["profiles"].items()}
        if counts!=dict(Python=5,BlueprintFallback=5):raise RuntimeError("five own NetShooter methods/Profile required")
        ue.register_declared_mixin(bp.ParentClass);parent,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.ParentClass]
        if any(len(value["functions"])!=10 for value in parent["profiles"].values()):raise RuntimeError("shared parent namespace lost")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    if hashlib.sha256((stage/PARENT).read_bytes()).hexdigest()!=parent_hash:raise RuntimeError("shared fire parent bytes changed")
    return dict(status="passed",kind="netshooterability",runtime_acceptance=False,full_acceptance=False,original_class=class_name,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_graphs_unmodified=True,
        original_graphs=hashes,original_graph_nodes=48,transport_nodes=8,new_business_nodes=0,native_end_adapter_nodes=0,
        actual_registered_profile_method_counts=counts,native_register_restore_passed=True,original_native_task_callback_names=CALLBACKS,
        native_weak_named_task_binding=True,original_empty_target_data_override_preserved=True,inherited_selector_redeclared=False,
        inherited_parent_namespace_preserved=True,parent_asset_sha256=parent_hash,python_callback_roots_or_scopes_added=False,
        assets=[RELATIVE,"Content/UEPMixins/DA_NetShooterAbilityMixin.uasset"],reference_hashes={str(official):digest})
