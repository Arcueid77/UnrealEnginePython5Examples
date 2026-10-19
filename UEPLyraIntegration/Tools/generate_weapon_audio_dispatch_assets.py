"""Extend only the accepted math library with four static void dispatch gates."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile

script=globals().get("__file__") or next(v for v in sys.argv if Path(v).name=="generate_weapon_audio_dispatch_assets.py")
sys.path.insert(0,str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from generate_weapon_audio_math_assets import kind,renamed,locals_snapshot,PACKAGE,RELATIVE
from uep_lyra_weapons.weapon_audio_dispatch_mixin import METHODS,CLASS

HELPER="Content/UEPMixins/BP_WeaponAudioDispatchRouter.uasset"
SET="Content/UEPMixins/DA_WeaponAudioDispatchMixin.uasset"
PROBE="Content/UEPValidation/BP_WeaponAudioDispatchCaller.uasset"


def arg(name):return next(v.split("=",1)[1] for v in sys.argv if v.startswith("-"+name+"="))
def generate():
    stage=require_authoring_stage(arg("UEPAudioDispatchStage"),ue.convert_relative_path_to_full(ue.get_content_dir()))
    baseline=json.loads(Path(arg("UEPAudioMathBaseline")).read_text(encoding="utf-8-sig"))
    if baseline["status"]!="passed" or baseline["kind"]!="weaponaudiomath" or len(baseline["assets"])!=3:raise RuntimeError("accepted math baseline required")
    for asset in baseline["assets"]:
        for field in ("stage","overlay"):
            if hashlib.sha256(Path(asset[field]).read_bytes()).hexdigest().lower()!=asset["sha256"].lower():raise RuntimeError("math baseline bytes changed")
    if any((stage/p).exists() for p in (HELPER,SET,PROBE)):raise RuntimeError("fresh audio dispatch helper/set/caller required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"audio-dispatch-before")
    original_class=bp.GeneratedClass.get_path_name();originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if sum(len(keys) for _,keys in originals)!=354:raise RuntimeError("accepted full math library footprint differs")
    graphs={g.get_name():g for g,_ in originals};signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in graphs if name!="EventGraph"}
    entries={};ignored={}
    for name in METHODS:
        graph=graphs[name];entry,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_FunctionEntry"];first,=entry.node_find_pin("then").get_linked_to()
        entries[name]=(entry,first);ignored[name]={(entry.get_name(),"then"),(first.owning_node.get_name(),first.name)}
        if not signatures[name]["flags"]&0x2000 or any(p["output"] for p in signatures[name]["parameters"]):raise RuntimeError("static void signature required")
    hashes={g.get_name():semantics(g,keys,ignored.get(g.get_name(),set())) for g,keys in originals};local_before={g.get_name():locals_snapshot(g) for g,_ in originals}
    helper=ue.create_blueprint(ue.find_class("Object"),CLASS.split(".")[0])
    for name,method in METHODS.items():
        graph=ue.blueprint_add_function(helper,method);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
        for pin in entries[name][0].node_pins():
            if pin.category not in ("exec","delegate"):entry.node_create_pin(1,kind(pin),renamed(pin.name))
        result.node_create_pin(0,EdGraphPinType(PinCategory="bool"),"UseOriginal");result.node_find_pin("UseOriginal").default_value="true";connect(entry,"then",result,"execute")
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_WeaponAudioDispatchMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_audio_dispatch_mixin",PythonClass="LyraWeaponAudioDispatch"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(helper,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(helper);ue.unregister_all_mixins()
    if int(helper.Status)==2:raise RuntimeError("audio dispatch helper compile failed")
    for name,method in METHODS.items():
        graph=graphs[name];entry,first=entries[name];call=graph.graph_add_node_call_function(getattr(helper.GeneratedClass,method));call.node_find_pin("self").default_object=helper.GeneratedClass.get_cdo()
        branch=graph.graph_add_node(K2Node_IfThenElse);result=graph.graph_add_node(K2Node_FunctionResult)
        entry.node_find_pin("then").break_link_to(first);connect(entry,"then",call,"execute");connect(call,"then",branch,"execute");connect(call,"UseOriginal",branch,"Condition")
        branch.node_find_pin("then").make_link_to(first);connect(branch,"else",result,"execute")
        for pin in entry.node_pins():
            if pin.category not in ("exec","delegate"):connect(entry,pin.name,call,renamed(pin.name))
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"audio-dispatch-after")!=before:raise RuntimeError("static library compile/class/full CDO changed")
    if any(ue.describe_function(bp.GeneratedClass,name)!=sig for name,sig in signatures.items()):raise RuntimeError("static audio ABI changed")
    if any(semantics(g,keys,ignored.get(g.get_name(),set()))!=hashes[g.get_name()] or locals_snapshot(g)!=local_before[g.get_name()] or len(g.Nodes)!=len(keys)+(3 if g.get_name() in METHODS else 0) for g,keys in originals):raise RuntimeError("existing audio business/default/math transport changed")
    try:
        ue.register_declared_mixin(helper.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==helper.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=4,BlueprintFallback=4):raise RuntimeError("four typed methods/Profile required")
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_WeaponAudioDispatchCaller")
    for name,method in METHODS.items():
        graph=ue.blueprint_add_function(probe,"Call"+method);entry=graph.Nodes[0];call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,name));result=graph.graph_add_node(K2Node_FunctionResult)
        for pin in call.node_pins():
            if pin.category in ("exec","delegate") or pin.name=="self":continue
            if pin.direction!=0:raise RuntimeError("void static output appeared")
            entry.node_create_pin(1,kind(pin),renamed(pin.name));connect(entry,renamed(pin.name),call,pin.name)
        connect(entry,"then",call,"execute");connect(call,"then",result,"execute")
    ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError("static audio dispatch caller compile failed")
    bp.save_package();helper.save_package();mixin.save_package();probe.save_package()
    return dict(status="passed",kind="weaponaudiodispatch",runtime_acceptance=False,full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_static_signatures_flags_preserved=True,
        original_business_graphs_preserved_with_dispatch=True,original_local_defaults_preserved=True,existing_math_transport_preserved=True,
        original_graph_nodes=348,baseline_graph_nodes=354,transport_nodes=20,new_business_nodes=0,native_end_adapter_nodes=0,
        static_functions_registered_as_mixins=False,actual_registered_profile_method_counts=counts,original_graphs=hashes,signatures=signatures,
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=[RELATIVE,HELPER,SET])


try:report=generate()
except Exception:report=dict(status="failed",error=traceback.format_exc());ue.log_error(report["error"])
Path(arg("UEPHeroAbilityAssetsResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
if report["status"]!="passed":raise RuntimeError(report["error"])
ue.log("UEP_WEAPON_AUDIO_DISPATCH_ASSETS_PASSED")
