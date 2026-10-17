"""Private Object BP hierarchy: own provider vs inheritance and ancestor original."""
import hashlib
import unreal_engine as ue
from unreal_engine.classes import DataAssetFactory, UEPPythonMixinSet, K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType, MemberReference, UEPPythonMixinProfile
from message_payload_graphs import connect

ROOT = "/Game/UEPValidation/"
NAMES = ("BP_DashMixinAncestorProbe", "BP_DashMixinChildProbe", "BP_DashMixinSiblingProbe", "DA_DashMixinAncestorProbe", "DA_DashMixinChildProbe", "BP_DashMixinInheritedFunctionProbe")


def constant(bp, name, value, inherited_signature=False):
    graph = ue.blueprint_add_function(bp, name); entry = graph.Nodes[0]
    if inherited_signature:
        # An override retains its reflected parent signature. Adding a new
        # user-defined output here is discarded by native signature conformance.
        entry.FunctionReference = MemberReference(MemberName=name, MemberParent=bp.ParentClass, bSelfContext=False)
        graph.graph_reconstruct_node(entry)
    result = graph.graph_add_node(K2Node_FunctionResult)
    if inherited_signature:
        result.FunctionReference = entry.FunctionReference
        graph.graph_reconstruct_node(result)
    else:
        result.node_create_pin(0, EdGraphPinType(PinCategory="int"), "ReturnValue")
    result.node_find_pin("ReturnValue").default_value = str(value)
    connect(entry, "then", result, "execute")


def configure(bp, name, prefix):
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, ROOT.rstrip("/"), UEPPythonMixinSet, factory); mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_abilities.dash_selector_probe_policy",
        PythonClass=prefix+profile) for profile in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp)
    if int(bp.Status) == 2: raise RuntimeError("private Mixin inheritance control compilation failed")
    bp.save_package(); mixin.save_package()
    return mixin


def generate(stage):
    for name in NAMES:
        if (stage/("Content/UEPValidation/"+name+".uasset")).exists(): raise RuntimeError("fresh private inheritance control required")
    ue.unregister_all_mixins()
    parent = ue.create_blueprint(ue.find_class("Object"), ROOT+NAMES[0]); constant(parent, "AncestorValue", 17); constant(parent, "SharedValue", 23)
    configure(parent, NAMES[3], "Ancestor")
    child = ue.create_blueprint(parent.GeneratedClass, ROOT+NAMES[1]); constant(child, "ChildValue", 11); constant(child, "SharedValue", 37, inherited_signature=True)
    child_set = configure(child, NAMES[4], "Child")
    sibling = ue.create_blueprint(parent.GeneratedClass, ROOT+NAMES[2]); ue.compile_blueprint(sibling); sibling.save_package()
    inherited = ue.create_blueprint(parent.GeneratedClass, ROOT+NAMES[5])
    ue.blueprint_configure_mixin(inherited, child_set, "Python", "PythonMixinProfile"); ue.compile_blueprint(inherited)
    if int(inherited.Status) == 2: raise RuntimeError("inherited shared-function control failed to compile")
    inherited.save_package()
    ue.unregister_all_mixins()
    signatures = [(parent.GeneratedClass, "AncestorValue"), (parent.GeneratedClass, "SharedValue"), (child.GeneratedClass, "ChildValue"),
        (child.GeneratedClass, "AncestorValue"), (child.GeneratedClass, "SharedValue"), (inherited.GeneratedClass, "SharedValue")]
    before = [ue.describe_function(cls, method) for cls, method in signatures]
    observed = {}; rejected = False; reverse_values = None; unregister_values = None
    try:
        ue.register_declared_mixin(parent.GeneratedClass); ue.register_declared_mixin(child.GeneratedClass)
        ue.register_declared_mixin(inherited.GeneratedClass)
        try: ue.register_declared_mixin(sibling.GeneratedClass)
        except TypeError: rejected = True
        if not rejected: raise RuntimeError("ordinary inherited Interface unexpectedly added a sibling router")
        registered = {entry["target_class"]: entry for entry in ue.get_registered_mixins()}
        if parent.GeneratedClass not in registered or child.GeneratedClass not in registered or sibling.GeneratedClass in registered:
            raise RuntimeError("private ancestor/explicit-child/ordinary-sibling router identity differs")
        instance = child.GeneratedClass.get_cdo()
        observed.update(parent_on_child=instance.call_function("AncestorValue"), child_on_child=instance.call_function("ChildValue"),
            ancestor_original=instance.call_mixin_original("AncestorValue"), child_original=instance.call_mixin_original("ChildValue"),
            parent_on_sibling=sibling.GeneratedClass.get_cdo().call_function("AncestorValue"))
        observed.update(owned_shared=instance.call_function("SharedValue"),
            qualified_parent_shared=ue.call_function_by_class(instance, parent.GeneratedClass, "SharedValue", {})["ReturnValue"],
            parent_initializer_original=instance._uep_probe_parent_init, child_initializer_original=instance._uep_probe_child_init,
            inherited_shared=inherited.GeneratedClass.get_cdo().call_function("SharedValue"))
        ue.set_mixin_profile(instance, "BlueprintFallback")
        observed["child_fallback"] = instance.call_function("ChildValue")
        observed["ancestor_after_child_switch"] = instance.call_function("AncestorValue")
        observed["shared_child_fallback"] = instance.call_function("SharedValue")
        observed["child_teardown_original"] = instance._uep_probe_child_teardown
        if observed != dict(parent_on_child=117, child_on_child=211, ancestor_original=17, child_original=11,
                parent_on_sibling=117, child_fallback=11, ancestor_after_child_switch=117, owned_shared=3097,
                qualified_parent_shared=1023, parent_initializer_original=23, child_initializer_original=37,
                inherited_shared=3069, shared_child_fallback=37, child_teardown_original=37):
            raise RuntimeError("native hierarchy original-call/default/Profile control differs: "+str(observed))
        ue.unregister_mixin(parent.GeneratedClass)
        observed["parent_teardown_original"] = instance._uep_probe_parent_teardown
        if observed["parent_teardown_original"] != 23: raise RuntimeError("ancestor teardown used child's same-name original")
    finally: ue.unregister_all_mixins()
    try:
        ue.register_declared_mixin(child.GeneratedClass); ue.register_declared_mixin(inherited.GeneratedClass); ue.register_declared_mixin(parent.GeneratedClass)
        instance = child.GeneratedClass.get_cdo()
        reverse_values = [instance.call_function("AncestorValue"), instance.call_function("ChildValue"), instance.call_function("SharedValue"), inherited.GeneratedClass.get_cdo().call_function("SharedValue")]
        if reverse_values != [117, 211, 3097, 3069]: raise RuntimeError("reverse-order hierarchy registration changed dispatch")
        ue.unregister_mixin(child.GeneratedClass)
        parent_survives = ue.call_function_by_class(instance, parent.GeneratedClass, "SharedValue", {})["ReturnValue"]
        ue.register_declared_mixin(child.GeneratedClass); ue.unregister_mixin(parent.GeneratedClass)
        unregister_values = [parent_survives, instance.call_function("SharedValue"), inherited.GeneratedClass.get_cdo().call_function("SharedValue")]
        if unregister_values != [1023, 2097, 2069]: raise RuntimeError("unregister order invalidated another router's preserved original")
    finally: ue.unregister_all_mixins()
    if [ue.describe_function(cls, method) for cls, method in signatures] != before:
        raise RuntimeError("native hierarchy router did not restore original signatures")
    files = [stage/("Content/UEPValidation/"+name+".uasset") for name in NAMES]
    return dict(stage_only=True, gameplay_business=False, parent_and_explicit_child_registered=True,
        ordinary_inherited_sibling_rejected=rejected, ancestor_original_through_child_router=True,
        owned_shared_function_verified=True, inherited_original_unwrapped=True, lexical_init_teardown_verified=True,
        reverse_order_values=reverse_values, unregister_order_values=unregister_values,
        child_direct_interfaces=len(child.get_property("ImplementedInterfaces")),
        child_owned_provider=ue.describe_function(child.GeneratedClass, "GetPythonMixinSet")["owner"] == child.GeneratedClass.get_path_name(),
        restored=True, observed=observed, assets=[dict(path=str(file), sha256=hashlib.sha256(file.read_bytes()).hexdigest()) for file in files])
