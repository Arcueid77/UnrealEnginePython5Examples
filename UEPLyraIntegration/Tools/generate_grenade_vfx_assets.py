"""Configure only the retained Actor's original Setup VFX function."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot

PACKAGE="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade"
RELATIVE="Plugins/GameFeatures/ShooterCore/Content/Weapon/Grenade/B_Grenade.uasset"
MIXIN="/Game/UEPMixins/DA_GrenadeVFXMixin"
METHOD="Setup VFX"


def audit(bp):
    graph,=[value for value in ue.blueprint_get_all_graphs(bp) if value.get_name()==METHOD];nodes={value.get_name():value for value in graph.Nodes}
    if len(nodes)!=19: raise RuntimeError("original Grenade VFX footprint differs")
    def link(node,pin,source,output):
        target,=nodes[node].node_find_pin(pin).get_linked_to()
        if target.owning_node!=nodes[source] or target.name!=output: raise RuntimeError("original Grenade VFX link differs: "+node+"/"+pin)
    for args in (("K2Node_CallFunction_49","execute","K2Node_FunctionEntry_0","then"),("K2Node_CallFunction_49","AttachToComponent","K2Node_VariableGet_34","Mesh"),
        ("K2Node_MacroInstance_0","exec","K2Node_CallFunction_49","then"),("K2Node_MacroInstance_0","InputObject","K2Node_CallFunction_49","ReturnValue"),
        ("K2Node_VariableSet_3","execute","K2Node_MacroInstance_0","Is Valid"),("K2Node_CallFunction_0","execute","K2Node_VariableSet_3","then"),
        ("K2Node_CallFunction_0","TestActor","K2Node_VariableGet_0","Instigator"),("K2Node_PromotableOperator_0","A","K2Node_CallFunction_0","TeamId"),
        ("K2Node_IfThenElse_0","Condition","K2Node_PromotableOperator_0","ReturnValue"),("K2Node_VariableSet_0","execute","K2Node_IfThenElse_0","then"),
        ("K2Node_VariableSet_1","execute","K2Node_IfThenElse_0","else"),("K2Node_CallFunction_28","execute","K2Node_VariableGet_2","then"),
        ("K2Node_CallFunction_28","self","K2Node_VariableGet_2","NS_Trail"),("K2Node_CallFunction_28","InValue","K2Node_VariableGet_19","Team Color")):
        link(*args)
    spawn=nodes["K2Node_CallFunction_49"]
    if str(spawn.FunctionReference.MemberName)!="SpawnSystemAttached" or spawn.node_find_pin("SystemTemplate").default_object.get_path_name()!="/Game/Effects/Particles/Explosion/NS_Grenade_Trail.NS_Grenade_Trail": raise RuntimeError("original Niagara asset/call differs")
    for pin,value in (("AttachPointName","None"),("LocationType","KeepRelativeOffset"),("bAutoDestroy","false"),("bAutoActivate","true"),("PoolingMethod","None"),("bPreCullCheck","true")):
        if spawn.node_find_pin(pin).default_value!=value: raise RuntimeError("original Niagara option differs: "+pin)
    if nodes["K2Node_PromotableOperator_0"].node_find_pin("B").default_value!="1" or nodes["K2Node_CallFunction_28"].node_find_pin("InVariableName").default_value!="Team_Color": raise RuntimeError("original team branch/parameter differs")
    for node,color in (("K2Node_VariableSet_0","(R=1.000000,G=0.050000,B=0.010000,A=1.000000)"),("K2Node_VariableSet_1","(R=0.010000,G=0.150000,B=1.000000,A=1.000000)")):
        if nodes[node].node_find_pin("Team Color").default_value!=color: raise RuntimeError("original native VFX color differs")
    return dict(nodes=19,red_team_id=1,red=[1.,.05,.01,1.],blue=[.01,.15,1.,1.],parameter="Team_Color",native_spawn_attached=True,
        native_pre_cull=True,native_auto_activate=True,native_auto_destroy=False,invalid_spawn_preserves_old_fields=True,validated_trail_get=True)


def generate(stage):
    source=Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original=source/RELATIVE;digest=hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest: raise RuntimeError("fresh original Grenade Actor required")
    bp=ue.load_object(Blueprint,PACKAGE);ue.unregister_all_mixins();original_class=bp.GeneratedClass.get_path_name();before=snapshot(bp,"grenade-vfx-before")
    signature=ue.describe_function(bp.GeneratedClass,METHOD);graphs=[(value,{node.get_name() for node in value.Nodes}) for value in ue.blueprint_get_all_graphs(bp)]
    hashes={value.get_name():semantics(value,names,set()) for value,names in graphs};policy=audit(bp)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    if ue.find_asset(MIXIN+".DA_GrenadeVFXMixin") is not None: raise RuntimeError("fresh Grenade VFX Mixin Set required")
    mixin=ue.create_asset("DA_GrenadeVFXMixin","/Game/UEPMixins",UEPPythonMixinSet,factory);mixin.DefaultProfile="Python"
    mixin.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule="uep_lyra_weapons.grenade_vfx_mixin",PythonClass="LyraGrenadeVFX"+name+"Profile") for name in ("Python","BlueprintFallback")]
    ue.blueprint_configure_mixin(bp,mixin,"Python","PythonMixinProfile");ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.GeneratedClass.get_path_name()!=original_class or snapshot(bp,"grenade-vfx-after")!=before: raise RuntimeError("original Grenade Actor class/full CDO changed")
    if any(semantics(value,names,set())!=hashes[value.get_name()] for value,names in graphs) or ue.describe_function(bp.GeneratedClass,METHOD)!=signature: raise RuntimeError("original Grenade graphs/helper signature changed")
    bp.save_package();mixin.save_package()
    try:
        ue.register_declared_mixin(bp.GeneratedClass);binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==bp.GeneratedClass]
        counts={name:len(value["functions"]) for name,value in binding["profiles"].items()}
        if counts!=dict(Python=1,BlueprintFallback=1): raise RuntimeError("one original Grenade VFX helper per Profile required")
    finally: ue.unregister_all_mixins()
    if ue.describe_function(bp.GeneratedClass,METHOD)!=signature: raise RuntimeError("native VFX signature did not restore")
    bp.save_package();mixin.save_package()
    return dict(status="passed",kind="grenadevfx",runtime_acceptance=False,full_acceptance=False,native_end_adapter_nodes=0,
        original_class=original_class,original_class_defaults_signature_graphs_preserved=True,original_full_cdo_preserved=True,original_graphs_unmodified=True,
        original_graphs=hashes,original_vfx_policy=policy,extra_signatures={METHOD:signature},implemented_methods=[METHOD],new_business_nodes=0,
        native_register_restore_passed=True,actual_registered_profile_method_counts=counts,actor_collision_fuse_explosion_damage_migrated=False,
        assets=[RELATIVE,"Content/UEPMixins/DA_GrenadeVFXMixin.uasset"],reference_hashes={str(original):digest})
