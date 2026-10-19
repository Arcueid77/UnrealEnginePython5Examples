"""Retain original decal graph and reuse its original latent-action node/UUID."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import snapshot

PACKAGE="/Game/Effects/Blueprints/B_WeaponDecals.B_WeaponDecals"
RELATIVE="Content/Effects/Blueprints/B_WeaponDecals.uasset"
DELAY,AFTER="UEPWeaponDecalsBeginNativeDelay","UEPWeaponDecalsAfterNativeDelay"


def generate(stage):
    source=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError("fresh original weapon decal required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    before=snapshot(bp,"weapon-decals-before");class_name=bp.GeneratedClass.get_path_name()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ("fire","ReceiveBeginPlay")}
    graph,=[g for g in ue.blueprint_get_all_graphs(bp) if g.get_name()=="EventGraph"];nodes={n.get_name():n for n in graph.Nodes}
    if len(nodes)!=52:raise RuntimeError("original weapon decal footprint differs")
    for name,method in (("K2Node_CallFunction_2","SetNiagaraArrayPosition"),("K2Node_CallFunction_30","SetNiagaraArrayInt32"),
                        ("K2Node_CallFunction_17","SetNiagaraArrayVector"),("K2Node_CallFunction_4","IsValid")):
        if str(nodes[name].FunctionReference.MemberName)!=method:raise RuntimeError("original decal array/cleanup native function differs")
    if nodes["K2Node_CallArrayFunction_1"].node_find_pin("bSizeToFit").default_value!="true":raise RuntimeError("original decal grow-without-truncation policy differs")
    delay,branch=nodes["K2Node_CallFunction_10"],nodes["K2Node_IfThenElse_0"]
    if str(delay.FunctionReference.MemberName)!="RetriggerableDelay" or delay.node_find_pin("Duration").default_value!="3.000000":raise RuntimeError("original decal delay differs")
    link,=delay.node_find_pin("then").get_linked_to()
    if link.owning_node!=branch or link.name!="execute":raise RuntimeError("original decal latent cleanup link differs")
    ignored={(delay.get_name(),"then"),(branch.get_name(),"execute")}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
    begin=graph.graph_add_node(K2Node_CustomEvent);begin.CustomFunctionName=DELAY;graph.graph_reconstruct_node(begin);connect(begin,"then",delay,"execute")
    after=graph.graph_add_node(K2Node_CustomEvent);after.CustomFunctionName=AFTER;graph.graph_reconstruct_node(after);connect(after,"then",branch,"execute")
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_WeaponDecalsMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_decals_mixin",PythonClass="LyraWeaponDecals"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,AFTER))
    delay.node_find_pin("then").break_link_to(branch.node_find_pin("execute"));connect(delay,"then",call,"execute")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"weapon-decals-after")!=before:raise RuntimeError("original decal class/full CDO changed")
    if len(graph.Nodes)-len(nodes)!=3 or any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError("original decal graph changed outside two dispatch endpoints")
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()):raise RuntimeError("original decal signatures changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==bp.GeneratedClass]
        counts={key:len(row["functions"]) for key,row in binding["profiles"].items()}
        if counts!=dict(Python=2,BlueprintFallback=2):raise RuntimeError("decal fire and native latent cleanup must both register")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="weapondecals",runtime_acceptance=False,full_acceptance=False,original_class=class_name,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_graphs_unmodified=False,
        original_business_graphs_preserved_with_dispatch=True,original_graphs=hashes,extra_signatures=signatures,
        native_end_adapter_nodes=0,transport_nodes=3,new_business_nodes=0,original_retriggerable_delay_node_reused=True,
        native_delay_seconds=3.,native_delay_uuid_preserved=True,cleanup_tests_validity_not_active=True,
        original_position_array_type_preserved=True,original_surface_array_tail_preserved=True,
        actual_registered_profile_method_counts=counts,native_register_restore_passed=True,
        assets=[RELATIVE,"Content/UEPMixins/DA_WeaponDecalsMixin.uasset"],reference_hashes={str(source):digest})
