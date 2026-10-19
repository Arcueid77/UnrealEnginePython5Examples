"""Rebuild original parent with one named native binding transport only."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile

script=globals().get("__file__") or next(value for value in sys.argv if Path(value).name=="generate_weapon_actor_begin_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from generate_dash_selector_assets import snapshot
from generate_weapon_actor_helpers_assets import PACKAGE,RELATIVE,METHODS,CHILDREN
from uep_lyra_weapons.weapon_actor_begin_mixin import CALLBACK,BIND


def arg(name):return next(value.split("=",1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def generate():
    stage=require_authoring_stage(arg("UEPDashRPCStageRoot"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    source=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE
    original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=original_hash:raise RuntimeError("fresh official parent needed before adding native transport")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    before=snapshot(bp,"weapon-begin-before");name=bp.GeneratedClass.get_path_name()
    signatures={key:ue.describe_function(bp.GeneratedClass,key) for key in METHODS+("Fire","ReceiveBeginPlay",CALLBACK)}
    if [item["name"] for item in signatures[CALLBACK]["parameters"]]!=["bTeamSet","TeamId","DisplayAsset"]:raise RuntimeError("original native team callback signature differs")
    graphs=[(graph,{node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    hashes={graph.get_name():semantics(graph,names,set()) for graph,names in graphs}
    graph=ue.blueprint_add_function(bp,BIND);entry=graph.Nodes[0]
    observer_class=ue.find_class("AsyncAction_ObserveTeamColors")
    entry.node_create_pin(1,EdGraphPinType(PinCategory="object",PinSubCategoryObject=observer_class),"Observer")
    add=graph.graph_add_node(K2Node_AddDelegate)
    add.DelegateReference=MemberReference(MemberName="OnTeamChanged",MemberParent=observer_class,bSelfContext=False)
    graph.graph_reconstruct_node(add)
    delegate=graph.graph_add_node(K2Node_CreateDelegate);owner=graph.graph_add_node(K2Node_Self)
    connect(owner,"self",delegate,"self");connect(entry,"Observer",add,"self")
    connect(entry,"then",add,"execute");connect(delegate,"OutputDelegate",add,"Delegate")
    delegate.SelectedFunctionName=CALLBACK
    mixin=ue.load_object(ue.find_class("UEPPythonMixinSet"),"/Game/UEPMixins/DA_WeaponActorHelpersMixin.DA_WeaponActorHelpersMixin")
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=profile,PythonModule="uep_lyra_weapons.weapon_actor_begin_mixin",PythonClass="LyraWeaponActorBegin"+profile+"Profile") for profile in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or len(graph.Nodes)!=4:raise RuntimeError("four-node exact named native delegate transport failed")
    if snapshot(bp,"weapon-begin-after")!=before or bp.GeneratedClass.get_path_name()!=name:raise RuntimeError("original parent class/full CDO changed")
    if any(semantics(g,keys,set())!=hashes[g.get_name()] for g,keys in graphs) or any(ue.describe_function(bp.GeneratedClass,key)!=value for key,value in signatures.items()):raise RuntimeError("original parent graph/signatures changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[row for row in ue.get_registered_mixins() if row["target_class"]==bp.GeneratedClass]
        counts={key:len(row["functions"]) for key,row in binding["profiles"].items()}
        if counts!=dict(Python=7,BlueprintFallback=7):raise RuntimeError("seven weapon parent methods per Profile required")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package()
    if hashlib.sha256(source.read_bytes()).hexdigest()!=original_hash:raise RuntimeError("official parent changed")
    return dict(status="passed",kind="weaponactorbegin",runtime_acceptance=False,full_acceptance=False,original_class=name,
        original_full_cdo_preserved=True,original_graphs_unmodified=True,original_graphs=hashes,extra_signatures=signatures,
        actual_registered_profile_method_counts=counts,native_register_restore_passed=True,parent_rebuilt_from_official=True,
        begin_play_migrated=True,native_weak_delegate_retained=True,python_callback_retained=False,original_per_call_factory_and_immediate_activation=True,
        transport_nodes=4,new_business_nodes=0,transport_function=BIND,transport_signature=ue.describe_function(bp.GeneratedClass,BIND),inherited_children=list(CHILDREN),
        reference_hashes={str(source):original_hash},assets=[RELATIVE,"Content/UEPMixins/DA_WeaponActorHelpersMixin.uasset"])


try:report=generate()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_ACTOR_BEGIN_ASSETS_PASSED")
