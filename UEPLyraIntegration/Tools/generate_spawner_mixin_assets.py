"""One spawner parent Set; retain native timers/RPC and original BP blocks."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult, K2Node_IfThenElse, K2Node_Message
from unreal_engine.structs import EdGraphPinType, UEPPythonMixinProfile

script = globals().get("__file__") or next(v for v in sys.argv if Path(v).name == "generate_spawner_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import make_gate, insert_gate, semantics

NAMES = ("B_WeaponSpawner", "B_AbilitySpawner")
PREFIX, RELOAD = "UEPDispatchSpawner", "UEPSpawnerHasReloadTag"

def arg(name):
    return next(v.split("=", 1)[1] for v in sys.argv if v.startswith("-"+name+"="))

def one(values):
    if len(values) != 1:
        raise RuntimeError("expected one spawner graph/entry")
    return values[0]

def function(bp, name):
    return one([g for g in bp.FunctionGraphs if g.get_name() == name])

def make_return_gate(parent, name, source):
    g = ue.blueprint_add_function(parent, name);entry = g.Nodes[0]
    for parameter in ("WeaponItemClass", "ReceivingPawn"):
        pin = source.node_find_pin(parameter)
        entry.node_create_pin(1, EdGraphPinType(PinCategory=pin.category, PinSubCategory=pin.sub_category,
            PinSubCategoryObject=pin.sub_category_object), parameter)
    result = g.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="int"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = "-1"
    entry.node_find_pin("then").make_link_to(result.node_find_pin("execute"))

def insert_return_gate(g, parent, name):
    entry = one([n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionEntry"])
    original = one(entry.node_find_pin("then").get_linked_to())
    results = [n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionResult"]
    # Existing literal true/false terminators preserve the native signature;
    # no new editable return node or mutable per-Actor output property.
    true_result = next(n for n in results if n.node_find_pin("ReturnValue").default_value.lower() == "true")
    false_result = next(n for n in results if n.node_find_pin("ReturnValue").default_value.lower() == "false")
    call = g.graph_add_node_call_function(getattr(parent.GeneratedClass, name))
    equal = g.graph_add_node_call_function(ue.find_class("KismetMathLibrary").EqualEqual_IntInt)
    positive = g.graph_add_node_call_function(ue.find_class("KismetMathLibrary").Greater_IntInt)
    fallback = g.graph_add_node(K2Node_IfThenElse);outcome = g.graph_add_node(K2Node_IfThenElse)
    entry.node_find_pin("then").break_link_to(original)
    entry.node_find_pin("then").make_link_to(call.node_find_pin("execute"))
    call.node_find_pin("then").make_link_to(fallback.node_find_pin("execute"))
    call.node_find_pin("ReturnValue").make_link_to(equal.node_find_pin("A"));equal.node_find_pin("B").default_value = "-1"
    equal.node_find_pin("ReturnValue").make_link_to(fallback.node_find_pin("Condition"))
    fallback.node_find_pin("then").make_link_to(original)
    fallback.node_find_pin("else").make_link_to(outcome.node_find_pin("execute"))
    call.node_find_pin("ReturnValue").make_link_to(positive.node_find_pin("A"));positive.node_find_pin("B").default_value = "0"
    positive.node_find_pin("ReturnValue").make_link_to(outcome.node_find_pin("Condition"))
    outcome.node_find_pin("then").make_link_to(true_result.node_find_pin("execute"))
    outcome.node_find_pin("else").make_link_to(false_result.node_find_pin("execute"))
    for parameter in ("WeaponItemClass", "ReceivingPawn"):
        entry.node_find_pin(parameter).make_link_to(call.node_find_pin(parameter))
    for offset, node in enumerate((call, equal, fallback, positive, outcome), 1):
        node.NodePosX, node.NodePosY = entry.NodePosX+offset*240, entry.NodePosY+200

def reload_adapter(bp):
    source = one([n for n in function(bp, "GiveWeapon").Nodes if n.get_class().get_name() == "K2Node_Message"])
    g = ue.blueprint_add_function(bp, RELOAD);entry = g.Nodes[0]
    entry.node_create_pin(1, EdGraphPinType(PinCategory="object", PinSubCategoryObject=ue.find_class("Pawn")), "Pawn")
    message = g.graph_add_node(K2Node_Message)
    message.FunctionReference = source.FunctionReference
    # UK2Node_Message defines its interface expansion/impure behavior natively;
    # the corresponding C++ flags are not reflected writable properties.
    g.graph_reconstruct_node(message)
    tags = g.graph_add_node_call_function(ue.find_class("BlueprintGameplayTagLibrary").MakeGameplayTagContainerFromTag)
    tags.node_find_pin("SingleTag").default_value = '(TagName="Event.Movement.Reload")'
    result = g.graph_add_node(K2Node_FunctionResult)
    result.node_create_pin(0, EdGraphPinType(PinCategory="bool"), "ReturnValue")
    for a,ap,b,bp_ in ((entry,"then",message,"execute"),(entry,"Pawn",message,"self"),
        (tags,"ReturnValue",message,"TagContainer"),(message,"then",result,"execute"),(message,"ReturnValue",result,"ReturnValue")):
        a.node_find_pin(ap).make_link_to(b.node_find_pin(bp_))
    return len(g.Nodes)

def curve_data(bp):
    return [{"length": float(t.TimelineLength), "tracks": [{"name": str(track.TrackName),
        "samples": [float(track.CurveFloat.call_function("GetFloatValue", x)) for x in (0.0,.25,.5,.75,1.0)]}
        for track in t.FloatTracks]} for t in bp.Timelines]

def generate():
    stage = require_authoring_stage(arg("UEPSpawnerStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    hashes = {str(reference/"Plugins/GameFeatures/ShooterCore/Content/Blueprint"/(n+".uasset")):
        hashlib.sha256((reference/"Plugins/GameFeatures/ShooterCore/Content/Blueprint"/(n+".uasset")).read_bytes()).hexdigest() for n in NAMES}
    ue.unregister_all_mixins()
    bps = [ue.load_object(Blueprint, "/ShooterCore/Blueprint/"+n+"."+n) for n in NAMES];parent, child = bps
    expected = [bp.GeneratedClass.get_name() for bp in bps]
    signatures = [ue.describe_function(bp.GeneratedClass, "GiveWeapon") for bp in bps]
    rpc = ue.describe_function(parent.GeneratedClass, "Broadcast Failure Message");curves = curve_data(parent)
    event = parent.UbergraphPages[0];cs = function(parent, "UserConstructionScript")
    def native_event(name):
        return one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_Event" and str(n.EventReference.MemberName) == name])
    def parent_call(name):
        return one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_CallParentFunction" and str(n.FunctionReference.MemberName) == name])
    timeline = one([n for n in event.Nodes if n.get_class().get_name() == "K2Node_Timeline"])
    hooks = ((cs,cs.Nodes[0],"then","Construction",None,None),
        (event,native_event("ReceiveBeginPlay"),"then","Begin",None,None),
        (event,native_event("ReceiveTick"),"then","Tick",None,None),
        (event,parent_call("PlayPickupEffects"),"then","Pickup",None,None),
        (event,parent_call("PlayRespawnEffects"),"then","Respawn",None,None),
        (event,timeline,"Update","Update","Value","GunPad_Brightness"))
    groups = {}
    for bp in bps:
        for g in list(bp.FunctionGraphs)+list(bp.UbergraphPages):
            groups[(bp.get_path_name(),g.get_name())] = {"graph":g,"names":{n.get_name() for n in g.Nodes},"ignored":set()}
    for g,entry,output,suffix,parameter,source in hooks:
        key = next(k for k,v in groups.items() if v["graph"] == g);groups[key]["ignored"].add((entry.get_name(),output))
        make_gate(parent,PREFIX+suffix,parameter,entry.node_find_pin(source) if parameter else None)
    for bp,kind in zip(bps,("Weapon","Ability")):
        g = function(bp,"GiveWeapon");entry = one([n for n in g.Nodes if n.get_class().get_name() == "K2Node_FunctionEntry"])
        groups[(bp.get_path_name(),"GiveWeapon")]["ignored"].add((entry.get_name(),"then"))
        make_return_gate(parent,PREFIX+kind+"Give",entry)
    adapter_nodes = reload_adapter(parent)
    ue.compile_blueprint(parent)
    for row in groups.values():
        row["before"] = semantics(row["graph"],row["names"],row["ignored"])
    for g,entry,output,suffix,parameter,source in hooks:
        insert_gate(g,entry,output,getattr(parent.GeneratedClass,PREFIX+suffix),parameter,source)
    for bp,kind in zip(bps,("Weapon","Ability")):
        insert_return_gate(function(bp,"GiveWeapon"),parent,PREFIX+kind+"Give")
    set_path = "/Game/UEPMixins/DA_SpawnerMixin"
    if ue.find_asset(set_path+".DA_SpawnerMixin") is not None:
        raise RuntimeError("fresh spawner authoring required")
    factory = DataAssetFactory();factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_SpawnerMixin","/Game/UEPMixins",UEPPythonMixinSet,factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=p,PythonModule="uep_lyra_world.spawner_mixin",PythonClass="LyraSpawner"+p+"Profile") for p in ("Python","BlueprintFallback")]
    ue.unregister_all_mixins();ue.blueprint_configure_mixin(parent,mixin,"Python","PythonMixinProfile")
    for bp,name in zip(bps,expected):
        ue.unregister_all_mixins();ue.compile_blueprint(bp)
        if int(bp.Status) == 2 or bp.GeneratedClass.get_name() != name or bp.GeneratedClass.get_cdo().GetPythonMixinSet() != mixin:
            raise RuntimeError("spawner class/inherited interface compile failed")
    proofs = []
    for (asset,name),row in groups.items():
        bp = one([bp for bp in bps if bp.get_path_name() == asset])
        g = one([g for g in ue.blueprint_get_all_graphs(bp) if g.get_name() == name])
        if semantics(g,row["names"],row["ignored"]) != row["before"]:
            raise RuntimeError("spawner original business graph changed: "+asset+"/"+name)
        proofs.append({"asset":asset,"graph":name,"original_semantic_digest":row["before"]})
    if [ue.describe_function(bp.GeneratedClass,"GiveWeapon") for bp in bps] != signatures or ue.describe_function(parent.GeneratedClass,"Broadcast Failure Message") != rpc or curve_data(parent) != curves:
        raise RuntimeError("spawner GiveWeapon/RPC signature or native curve changed")
    for bp in bps+[mixin]:
        bp.save_package()
    for file,digest in hashes.items():
        if hashlib.sha256(Path(file).read_bytes()).hexdigest() != digest:
            raise RuntimeError("official spawner asset changed")
    return {"status":"passed","runtime_acceptance":False,"class_preserved":True,"single_parent_interface_set":True,
        "original_blocks_retained":True,"gate_count":8,"original_graphs":proofs,"native_curve_preserved":True,
        "reload_interface_adapter_nodes":adapter_nodes,"original_failure_rpc_transport_retained":True,"reference_hashes":hashes}

try:
    report = generate()
except Exception:
    report = {"status":"failed","error":traceback.format_exc()}
Path(arg("UEPGenerateSpawnerResult")).write_text(json.dumps(report,indent=2),encoding="utf-8")
ue.log("UEP_SPAWNER_ASSETS_"+report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
