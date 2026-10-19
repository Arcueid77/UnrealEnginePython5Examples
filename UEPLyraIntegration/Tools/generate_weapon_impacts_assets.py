"""Route all impact policy methods while retaining original native latent action."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import snapshot

PACKAGE="/Game/Effects/Blueprints/B_WeaponImpacts.B_WeaponImpacts"
RELATIVE="Content/Effects/Blueprints/B_WeaponImpacts.uasset"
DELAY,AFTER="UEPWeaponImpactsBeginNativeDelay","UEPWeaponImpactsAfterNativeDelay"
COUNTS=dict(UserConstructionScript=1,SpawnFromDataChannels=36,AddImpactsToBuckets=47,SpawnParticlesFromImpacts=23,SpawnFromArrays=63,EventGraph=24)


def generate(stage):
    source=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError("fresh original weapon impacts required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    before=snapshot(bp,"weapon-impacts-before");class_name=bp.GeneratedClass.get_path_name()
    methods=("Fire","AddImpactsToBuckets","SpawnParticlesFromImpacts","SpawnFromArrays","SpawnFromDataChannels")
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in methods+("ReceiveBeginPlay",)}
    graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(bp)}
    if {key:len(g.Nodes) for key,g in graphs.items()}!=COUNTS:raise RuntimeError("original impact graph footprint differs")
    nodes={key:{n.get_name():n for n in g.Nodes} for key,g in graphs.items()}
    arrays=nodes["SpawnFromArrays"];channels=nodes["SpawnFromDataChannels"]
    if str(arrays["K2Node_PromotableOperator_1"].FunctionReference.MemberName)!="Greater_DoubleDouble":raise RuntimeError("original inverted impact reuse comparison differs")
    reuse,=arrays["K2Node_IfThenElse_2"].node_find_pin("then").get_linked_to()
    if reuse.owning_node!=arrays["K2Node_VariableSet_4"]:raise RuntimeError("original greater-distance reuse branch differs")
    for key,method in (("K2Node_CallFunction_2","SetNiagaraArrayPosition"),("K2Node_CallFunction_17","SetNiagaraArrayVector"),
                       ("K2Node_CallFunction_12","SetVariablePosition"),("K2Node_CallFunction_11","Activate")):
        if str(arrays[key].FunctionReference.MemberName)!=method:raise RuntimeError("original native impact parameter API differs")
    if arrays["K2Node_CallArrayFunction_2"].node_find_pin("bSizeToFit").default_value!="true":raise RuntimeError("original system array growth differs")
    if str(channels["K2Node_CallFunction_1"].FunctionReference.MemberName)!="WriteToNiagaraDataChannel":raise RuntimeError("original legacy channel API differs")
    if any(channels["K2Node_CallFunction_1"].node_find_pin(key).default_value!="true" for key in ("bVisibleToGame","bVisibleToCPU","bVisibleToGPU")):raise RuntimeError("original channel visibility differs")
    selector=nodes["SpawnParticlesFromImpacts"]
    if {selector[key].node_find_pin("B").default_value for key in ("K2Node_EnumEquality_0","K2Node_EnumEquality_1")}!={"SurfaceType2","SurfaceType3"}:raise RuntimeError("original concrete/glass channel selection differs")
    graph=graphs["EventGraph"];delay=nodes["EventGraph"]["K2Node_CallFunction_10"];cleanup=nodes["EventGraph"]["K2Node_VariableSet_7"]
    if str(delay.FunctionReference.MemberName)!="RetriggerableDelay" or delay.node_find_pin("Duration").default_value!="3.000000":raise RuntimeError("original impact latent delay differs")
    link,=delay.node_find_pin("then").get_linked_to()
    if link.owning_node!=cleanup or link.name!="execute":raise RuntimeError("original impact cleanup continuation differs")
    ignored={(delay.get_name(),"then"),(cleanup.get_name(),"execute")}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in graphs.values()]
    hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
    begin=graph.graph_add_node(K2Node_CustomEvent);begin.CustomFunctionName=DELAY;graph.graph_reconstruct_node(begin);connect(begin,"then",delay,"execute")
    after=graph.graph_add_node(K2Node_CustomEvent);after.CustomFunctionName=AFTER;graph.graph_reconstruct_node(after);connect(after,"then",cleanup,"execute")
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_WeaponImpactsMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_impacts_mixin",PythonClass="LyraWeaponImpacts"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,AFTER))
    delay.node_find_pin("then").break_link_to(cleanup.node_find_pin("execute"));connect(delay,"then",call,"execute")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"weapon-impacts-after")!=before:raise RuntimeError("original impact class/full CDO changed")
    if len(graph.Nodes)-COUNTS["EventGraph"]!=3 or any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError("original impact graph changed outside two dispatch endpoints")
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()):raise RuntimeError("original impact signatures changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==bp.GeneratedClass]
        counts={key:len(row["functions"]) for key,row in binding["profiles"].items()}
        if counts!=dict(Python=6,BlueprintFallback=6):raise RuntimeError("all five impact methods and latent cleanup must register")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="weaponimpacts",runtime_acceptance=False,full_acceptance=False,original_class=class_name,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_graphs_unmodified=False,
        original_business_graphs_preserved_with_dispatch=True,original_graphs=hashes,original_graph_counts=COUNTS,extra_signatures=signatures,
        implemented_methods=list(methods)+( [AFTER]),native_end_adapter_nodes=0,transport_nodes=3,new_business_nodes=0,
        original_retriggerable_delay_node_reused=True,native_delay_seconds=3.,native_delay_uuid_preserved=True,cleanup_tests_validity_not_active=True,
        original_greater_distance_reuse_rule_preserved=True,original_typed_array_and_legacy_channel_apis_preserved=True,
        actual_registered_profile_method_counts=counts,native_register_restore_passed=True,
        assets=[RELATIVE,"Content/UEPMixins/DA_WeaponImpactsMixin.uasset"],reference_hashes={str(source):digest})
