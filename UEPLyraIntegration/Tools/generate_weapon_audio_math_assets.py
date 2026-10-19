"""Keep static ABI/business graphs; add a typed ordinary Object branch per helper."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot
from uep_lyra_weapons.weapon_audio_math_mixin import METHODS,CLASS

PACKAGE="/ShooterCore/System/Audio/WeaponAudioFunctions.WeaponAudioFunctions"
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/System/Audio/WeaponAudioFunctions.uasset"
HELPER="Content/UEPMixins/BP_WeaponAudioMathRouter.uasset"
PROBE="Content/UEPValidation/BP_WeaponAudioMathCaller.uasset"


def kind(pin):return EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category,PinSubCategoryObject=pin.sub_category_object,bIsReference=pin.is_reference,bIsConst=pin.is_const)
def renamed(name):return "WorldContext" if name=="__WorldContext" else name
def locals_snapshot(graph):
    return [(str(v.VarName),str(v.DefaultValue),str(v.VarType.PinCategory),str(v.VarType.PinSubCategory)) for n in graph.Nodes if n.get_class().get_name()=="K2Node_FunctionEntry" for v in n.LocalVariables]


def generate(stage):
    official=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent/RELATIVE;digest=hashlib.sha256(official.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest or (stage/HELPER).exists() or (stage/PROBE).exists():raise RuntimeError("fresh original static library/router/caller required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"audio-math-before");class_name=bp.GeneratedClass.get_path_name()
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];graphs={g.get_name():g for g,_ in originals}
    if sum(len(keys) for _,keys in originals)!=348:raise RuntimeError("original full audio-library footprint differs")
    signatures={g.get_name():ue.describe_function(bp.GeneratedClass,g.get_name()) for g,_ in originals if g.get_name()!="EventGraph"}
    entries={};returns={};ignored={}
    for name in METHODS:
        graph=graphs[name];entry,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_FunctionEntry"];result,=[n for n in graph.Nodes if n.get_class().get_name()=="K2Node_FunctionResult"]
        first,=entry.node_find_pin("then").get_linked_to();entries[name]=(entry,first);returns[name]=result
        ignored[name]={(entry.get_name(),"then"),(first.owning_node.get_name(),first.name)}
        if not signatures[name]["flags"]&0x2000:raise RuntimeError("original static function flag required")
    hashes={g.get_name():semantics(g,keys,ignored.get(g.get_name(),set())) for g,keys in originals};locals_before={g.get_name():locals_snapshot(g) for g,_ in originals}
    helper=ue.create_blueprint(ue.find_class("Object"),CLASS.split(".")[0])
    for name,method in METHODS.items():
        graph=ue.blueprint_add_function(helper,method);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
        for pin in entries[name][0].node_pins():
            if pin.category not in ("exec","delegate"):entry.node_create_pin(1,kind(pin),renamed(pin.name))
        result.node_create_pin(0,EdGraphPinType(PinCategory="bool"),"UseOriginal");result.node_find_pin("UseOriginal").default_value="true"
        for pin in returns[name].node_pins():
            if pin.category!="exec":result.node_create_pin(0,kind(pin),pin.name)
        connect(entry,"then",result,"execute")
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_WeaponAudioMathMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_audio_math_mixin",PythonClass="LyraWeaponAudioMath"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(helper,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(helper);ue.unregister_all_mixins()
    if int(helper.Status)==2:raise RuntimeError("typed ordinary audio router compile failed")
    for name,method in METHODS.items():
        graph=graphs[name];entry,first=entries[name];call=graph.graph_add_node_call_function(getattr(helper.GeneratedClass,method));call.node_find_pin("self").default_object=helper.GeneratedClass.get_cdo()
        branch=graph.graph_add_node(K2Node_IfThenElse);result=graph.graph_add_node(K2Node_FunctionResult)
        existing={p.name for p in result.node_pins()}
        for pin in returns[name].node_pins():
            if pin.category!="exec":
                if pin.name not in existing:result.node_create_pin(0,kind(pin),pin.name)
                connect(call,pin.name,result,pin.name)
        entry.node_find_pin("then").break_link_to(first);connect(entry,"then",call,"execute");connect(call,"then",branch,"execute");connect(call,"UseOriginal",branch,"Condition");branch.node_find_pin("then").make_link_to(first);connect(branch,"else",result,"execute")
        for pin in entry.node_pins():
            if pin.category not in ("exec","delegate"):connect(entry,pin.name,call,renamed(pin.name))
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"audio-math-after")!=before:raise RuntimeError("static library compile/class/full CDO changed")
    if any(ue.describe_function(bp.GeneratedClass,name)!=sig for name,sig in signatures.items()):raise RuntimeError("original static audio ABI changed")
    if any(semantics(g,keys,ignored.get(g.get_name(),set()))!=hashes[g.get_name()] or locals_snapshot(g)!=locals_before[g.get_name()] or len(g.Nodes)!=len(keys)+(3 if g.get_name() in METHODS else 0) for g,keys in originals):raise RuntimeError("original static business/default graph changed outside transport")
    try:
        ue.register_declared_mixin(helper.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==helper.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=2,BlueprintFallback=2):raise RuntimeError("two typed math methods/Profile required")
    finally:ue.unregister_all_mixins()
    probe=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_WeaponAudioMathCaller")
    for name in METHODS:
        graph=ue.blueprint_add_function(probe,"CallSides" if name=="GetSideReflectionAngles" else "CallWhiz");entry=graph.Nodes[0];call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,name));result=graph.graph_add_node(K2Node_FunctionResult)
        for pin in call.node_pins():
            if pin.category in ("exec","delegate") or pin.name=="self":continue
            if pin.direction==0:entry.node_create_pin(1,kind(pin),renamed(pin.name));connect(entry,renamed(pin.name),call,pin.name)
            else:result.node_create_pin(0,kind(pin),pin.name);connect(call,pin.name,result,pin.name)
        if any(p.name=="execute" for p in call.node_pins()):connect(entry,"then",call,"execute");connect(call,"then",result,"execute")
        else:connect(entry,"then",result,"execute")
    ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError("stage-only static Blueprint caller compile failed")
    bp.save_package();helper.save_package();mixin.save_package();probe.save_package()
    return dict(status="passed",kind="weaponaudiomath",runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdo_preserved=True,original_static_signatures_flags_preserved=True,original_business_graphs_preserved_with_dispatch=True,original_graph_nodes=348,
        original_graphs=hashes,original_local_defaults_preserved=True,original_graphs_unmodified=False,native_end_adapter_nodes=0,transport_nodes=10,new_business_nodes=0,
        static_functions_registered_as_mixins=False,native_register_restore_passed=True,actual_registered_profile_method_counts=counts,helper_class=CLASS,signatures=signatures,
        caller_probe=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),
        assets=[RELATIVE,HELPER,"Content/UEPMixins/DA_WeaponAudioMathMixin.uasset"],reference_hashes={str(official):digest})
