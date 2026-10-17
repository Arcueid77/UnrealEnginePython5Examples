"""Configure two original native events; do not edit any Grenade business graph."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot

PACKAGE="/ShooterCore/Input/Abilities/GA_Grenade.GA_Grenade"
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/Input/Abilities/GA_Grenade.uasset"
WIDGET="/ShooterCore/Weapons/Grenade/W_GrenadeCooldown.W_GrenadeCooldown_C"
METHODS=("K2_OnPawnAvatarSet","K2_OnAbilityRemoved")


def audit(bp):
    graph,=[value for value in ue.blueprint_get_all_graphs(bp) if value.get_name()=="EventGraph"]
    nodes={node.get_name():node for node in graph.Nodes}
    if len(nodes)!=46: raise RuntimeError("original Grenade EventGraph footprint differs")
    def link(node,pin,source,output):
        actual,=nodes[node].node_find_pin(pin).get_linked_to()
        if actual.owning_node!=nodes[source] or actual.name!=output: raise RuntimeError("original Grenade UI link differs: "+node+"/"+pin)
    for args in (("K2Node_CallFunction_14","execute","K2Node_Event_0","then"),
        ("K2Node_CallFunction_14","Handle","K2Node_VariableGet_5","Extension"),
        ("K2Node_IfThenElse_1","execute","K2Node_CallFunction_14","then"),
        ("K2Node_IfThenElse_1","Condition","K2Node_CallFunction_14","ReturnValue"),
        ("K2Node_CallFunction_8","execute","K2Node_IfThenElse_1","else"),
        ("K2Node_MacroInstance_1","exec","K2Node_CallFunction_8","True"),
        ("K2Node_MacroInstance_1","InputObject","K2Node_GetSubsystem_0","ReturnValue"),
        ("K2Node_CallFunction_5","execute","K2Node_MacroInstance_1","Is Valid"),
        ("K2Node_CallFunction_5","ContextObject","K2Node_CallFunction_11","ReturnValue"),
        ("K2Node_VariableSet_2","Extension","K2Node_CallFunction_5","ReturnValue"),
        ("K2Node_CallFunction_3","execute","K2Node_Event_3","then"),
        ("K2Node_CallFunction_3","Handle","K2Node_VariableGet_1","Extension"),
        ("K2Node_VariableSet_0","execute","K2Node_CallFunction_3","then")): link(*args)
    for node,pin in (("K2Node_IfThenElse_1","then"),("K2Node_CallFunction_8","False"),("K2Node_MacroInstance_1","Is Not Valid"),("K2Node_VariableSet_0","Extension")):
        if nodes[node].node_find_pin(pin).get_linked_to(): raise RuntimeError("original Grenade UI no-op/reset path differs")
    for node,method in (("K2Node_CallFunction_14","IsValid"),("K2Node_CallFunction_8","IsLocallyControlled"),
        ("K2Node_CallFunction_11","GetOwningActorFromActorInfo"),("K2Node_CallFunction_5","K2_RegisterExtensionAsWidgetForContext"),("K2Node_CallFunction_3","Unregister")):
        if str(nodes[node].FunctionReference.MemberName)!=method: raise RuntimeError("original Grenade native UI call differs")
    call=nodes["K2Node_CallFunction_5"]
    if call.node_find_pin("WidgetClass").default_object.get_path_name()!=WIDGET or call.node_find_pin("Priority").default_value!="-1" or call.node_find_pin("ExtensionPointTag").default_value!='(TagName="HUD.Slot.ExtraEquipment")':
        raise RuntimeError("original Grenade UI class/tag/priority differs")
    return dict(context="GetOwningActorFromActorInfo",widget=WIDGET,tag="HUD.Slot.ExtraEquipment",priority=-1,
        valid_handle_noop=True,nonlocal_noop=True,missing_subsystem_noop=True,removal_unconditional=True)


def generate(stage):
    source=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original=source/RELATIVE;digest=hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest: raise RuntimeError("fresh original Grenade required")
    bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins()
    original_class=bp.GeneratedClass.get_path_name();before=snapshot(bp,"grenade-ui-before")
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in (*METHODS,"K2_ActivateAbility")}
    originals=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes={value.get_name():semantics(value,names,set()) for value,names in originals};policy=audit(bp)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    if ue.find_asset("/Game/UEPMixins/DA_GrenadeWidgetMixin.DA_GrenadeWidgetMixin") is not None: raise RuntimeError("fresh Grenade UI Mixin Set required")
    mixin=ue.create_asset("DA_GrenadeWidgetMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_abilities.grenade_widget_mixin",PythonClass="LyraGrenadeWidget"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-ui-after")!=before: raise RuntimeError("original Grenade class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in originals): raise RuntimeError("original Grenade graphs changed")
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Grenade signatures changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=2,BlueprintFallback=2): raise RuntimeError("two original Grenade events per Profile required")
    finally: ue.unregister_all_mixins()
    if any(ue.describe_function(bp.GeneratedClass,name)!=value for name,value in signatures.items()): raise RuntimeError("original Grenade signatures did not restore")
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadewidget",runtime_acceptance=False,full_acceptance=False,native_end_adapter_nodes=0,
        original_class=original_class,original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,
        original_graphs_unmodified=True,original_graphs=hashes,original_ui_policy=policy,extra_signatures=signatures,
        implemented_methods=METHODS,new_business_nodes=0,native_register_restore_passed=True,actual_registered_profile_method_counts=counts,
        whole_grenade_activation_projectile_damage_migrated=False,assets=[RELATIVE,"Content/UEPMixins/DA_GrenadeWidgetMixin.uasset"],reference_hashes={str(original):digest})
