"""Retain firing graphs; add exact weak task binding and typed message dispatch."""
import hashlib
import json
import struct
import zlib
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from mixin_graph_gates import semantics
from message_payload_graphs import connect,broadcast_graph
from generate_dash_selector_assets import snapshot
from uep_lyra_weapons.weapon_ability_fire_mixin import DIRECT_METHODS,FIRE_CALLBACKS,LISTEN,FAILURE,BIND

PACKAGE="/Game/Weapons/GA_Weapon_Fire.GA_Weapon_Fire"
RELATIVE="Content/Weapons/GA_Weapon_Fire.uasset"
CHILDREN=("/ShooterCore/Weapons/Pistol/GA_Weapon_Fire_Pistol.GA_Weapon_Fire_Pistol",
          "/ShooterCore/Weapons/Rifle/GA_Weapon_Fire_Rifle_Auto.GA_Weapon_Fire_Rifle_Auto",
          "/ShooterCore/Weapons/Shotgun/GA_Weapon_Fire_Shotgun.GA_Weapon_Fire_Shotgun")


def bind_graph(bp):
    graph=ue.blueprint_add_function(bp,BIND);entry=graph.Nodes[0];task_class=ue.find_class("AbilityTask_PlayMontageAndWait")
    entry.node_create_pin(1,EdGraphPinType(PinCategory="object",PinSubCategoryObject=task_class),"Task")
    owner=graph.graph_add_node(K2Node_Self);previous=entry
    for event,callback in FIRE_CALLBACKS.items():
        add=graph.graph_add_node(K2Node_AddDelegate);add.DelegateReference=MemberReference(MemberName=event,MemberParent=task_class,bSelfContext=False)
        graph.graph_reconstruct_node(add);delegate=graph.graph_add_node(K2Node_CreateDelegate)
        connect(entry,"Task",add,"self");connect(previous,"then",add,"execute")
        connect(owner,"self",delegate,"self");connect(delegate,"OutputDelegate",add,"Delegate");delegate.SelectedFunctionName=callback
        previous=add
    if len(graph.Nodes)!=8:raise RuntimeError("three exact native montage delegate bindings required")
    return graph


def probe(stage):
    relative="Content/UEPValidation/BP_WeaponAbilityFireProbe.uasset"
    if (stage/relative).exists():raise RuntimeError("fresh stage-only fire probe required")
    bp=ue.create_blueprint(ue.find_class("Object"),"/Game/UEPValidation/BP_WeaponAbilityFireProbe")
    graph=broadcast_graph(bp,"MontageFailure",ue.find_struct("LyraAbilityMontageFailureMessage"),ue.find_class("GameplayMessageSubsystem"))
    ue.compile_blueprint(bp)
    if int(bp.Status)==2 or len(graph.Nodes)!=2:raise RuntimeError("typed native montage-failure broadcast transport failed")
    bp.save_package();path=stage/relative
    return dict(stage_only=True,gameplay_business=False,typed_native_payload=True,asset=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def generate(stage):
    marker=json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"));official=Path(marker["source"]).parent
    digest=hashlib.sha256((official/RELATIVE).read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError("fresh original shared fire ability required")
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();before=snapshot(bp,"weapon-ability-fire-before")
    class_name=bp.GeneratedClass.get_path_name();originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
    if {g.get_name():len(keys) for g,keys in originals}!={"Slelect Hit Montage":31,"EventGraph":75}:raise RuntimeError("original shared fire graph footprint differs")
    graph,=[g for g,_ in originals if g.get_name()=="EventGraph"];nodes={n.get_name():n for n in graph.Nodes}
    task=nodes["K2Node_LatentAbilityCall_0"];parts=[int(task.NodeGuid.get_field(key))&0xffffffff for key in ("A","B","C","D")]
    suffix="".join(format(value,"08X") for value in parts[:3])+format(zlib.crc32(struct.pack("<4I",*parts)),"08X")
    if FIRE_CALLBACKS!={event:event+"_"+suffix for event in FIRE_CALLBACKS}:raise RuntimeError("original native montage callback identities differ")
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in DIRECT_METHODS+tuple(FIRE_CALLBACKS.values())}
    action=nodes["K2Node_AsyncAction_ListenForGameplayMessages_0"];branch=nodes["K2Node_IfThenElse_2"]
    if "Ability.PlayMontageOnActivateFail.Message" not in action.node_find_pin("Channel").default_value or action.node_find_pin("MatchType").default_value!="ExactMatch":raise RuntimeError("original exact native failure listener differs")
    link,=action.node_find_pin("OnMessageReceived").get_linked_to()
    if link.owning_node!=branch:raise RuntimeError("original failure callback entry differs")
    payload_pins=("Payload_AvatarActor","Payload_FailureMontage")
    payload_links={pin:{(p.owning_node.get_name(),p.name) for p in action.node_find_pin(pin).get_linked_to()} for pin in payload_pins}
    ignored={(action.get_name(),"execute"),(action.get_name(),"OnMessageReceived"),(branch.get_name(),"execute")}
    ignored.update((action.get_name(),pin) for pin in payload_pins)
    hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
    start=graph.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=LISTEN;graph.graph_reconstruct_node(start);connect(start,"then",action,"execute")
    callback=graph.graph_add_node(K2Node_CustomEvent);callback.CustomFunctionName=FAILURE;graph.graph_reconstruct_node(callback)
    for name,cls in (("AvatarActor","Actor"),("FailureMontage","AnimMontage")):
        callback.node_create_pin(1,EdGraphPinType(PinCategory="object",PinSubCategoryObject=ue.find_class(cls)),name)
    connect(callback,"then",branch,"execute")
    binding=bind_graph(bp)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixin=ue.create_asset("DA_WeaponAbilityFireMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.weapon_ability_fire_mixin",PythonClass="LyraWeaponAbilityFire"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,FAILURE))
    action.node_find_pin("OnMessageReceived").break_link_to(branch.node_find_pin("execute"));connect(action,"OnMessageReceived",call,"execute")
    connect(action,"Payload_AvatarActor",call,"AvatarActor");connect(action,"Payload_FailureMontage",call,"FailureMontage")
    # The original fallback continues in the same native callback frame, keeping
    # its original compiler-owned payload temporaries and business nodes intact.
    for pin,original_links in payload_links.items():
        current={(p.owning_node.get_name(),p.name) for p in action.node_find_pin(pin).get_linked_to() if p.owning_node!=call}
        if current!=original_links:raise RuntimeError("original failure payload consumer disconnected")
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=class_name or snapshot(bp,"weapon-ability-fire-after")!=before:raise RuntimeError("original shared fire class/full CDO changed")
    if len(graph.Nodes)!=78 or len(binding.Nodes)!=8 or any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError("original fire graph changed outside native transport endpoints")
    if any(ue.describe_function(bp.GeneratedClass,name)!=signature for name,signature in signatures.items()):raise RuntimeError("original shared fire signatures changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in row["profiles"].items()}
        if counts!=dict(Python=10,BlueprintFallback=10):raise RuntimeError("six methods/three original task callbacks/one failure continuation must register")
    finally:ue.unregister_all_mixins()
    bp.save_package();mixin.save_package();children=[]
    for path in CHILDREN:
        relative="Plugins/GameFeatures/ShooterCore/Content/"+path.split("/ShooterCore/",1)[1].split(".")[0]+".uasset"
        original_hash=hashlib.sha256((official/relative).read_bytes()).hexdigest()
        if hashlib.sha256((stage/relative).read_bytes()).hexdigest()!=original_hash:raise RuntimeError("original child weapon ability bytes changed")
        child=ue.load_object(Blueprint,path)
        if child.ParentClass!=bp.GeneratedClass:raise RuntimeError("original child fire inheritance changed")
        children.append(dict(path=path,sha256=original_hash,stage=str(stage/relative),original=str(official/relative)))
    return dict(status="passed",kind="weaponabilityfire",runtime_acceptance=False,full_acceptance=False,original_class=class_name,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_graphs_unmodified=False,
        original_business_graphs_preserved_with_dispatch=True,original_graphs=hashes,original_graph_nodes=106,extra_signatures=signatures,
        native_end_adapter_nodes=0,transport_nodes=11,new_business_nodes=0,actual_registered_profile_method_counts=counts,native_register_restore_passed=True,
        original_native_task_callback_names=FIRE_CALLBACKS,native_weak_named_task_binding=True,native_function_name_timers=True,
        original_native_message_factory_and_exact_payload_preserved=True,python_callback_roots_or_scopes_added=False,
        inherited_children=children,caller_probe=probe(stage),assets=[RELATIVE,"Content/UEPMixins/DA_WeaponAbilityFireMixin.uasset"],reference_hashes={str(official/RELATIVE):digest})
