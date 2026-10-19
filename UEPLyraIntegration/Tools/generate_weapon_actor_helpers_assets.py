"""Configure the retained weapon parent and verify three unchanged children."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics
from generate_dash_selector_assets import snapshot

PACKAGE = "/Game/Weapons/B_Weapon.B_Weapon"
RELATIVE = "Content/Weapons/B_Weapon.uasset"
METHODS = ("Add Fake Projectile Data", "TriggerFireAudio", "UpdateCustomStencil", "UpdateTeamColors")
CHILDREN = tuple("/ShooterCore/Weapons/"+name+"/B_"+name+".B_"+name for name in ("Pistol", "Rifle", "Shotgun"))


def graph_hashes(bp):
    return [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]


def audit(bp):
    expected = {"Add Fake Projectile Data": 29, "TriggerFireAudio": 10, "UpdateCustomStencil": 10, "UpdateTeamColors": 7}
    graphs = {graph.get_name(): graph for graph in ue.blueprint_get_all_graphs(bp)}
    if any(len(graphs[name].Nodes) != count for name, count in expected.items()): raise RuntimeError("original helper graph footprint differs")
    def node(graph, name): return next(value for value in graphs[graph].Nodes if value.get_name() == name)
    def default(graph, name, pin, expected_value):
        if node(graph, name).node_find_pin(pin).default_value != expected_value: raise RuntimeError("original helper default differs: "+graph+"/"+pin)
    for args in ((METHODS[0], "K2Node_MacroInstance_0", "FirstIndex", "1"),
                 (METHODS[0], "K2Node_CommutativeAssociativeBinaryOperator_0", "B", "0"),
                 (METHODS[0], "K2Node_PromotableOperator_2", "B", "1000000.000000"),
                 (METHODS[0], "K2Node_CallFunction_0", "TraceChannel", "TraceTypeQuery1"),
                 (METHODS[0], "K2Node_CallFunction_46", "InSocketName", "Muzzle"),
                 (METHODS[0], "K2Node_CallFunction_46", "TransformSpace", "RTS_World"),
                 (METHODS[1], "K2Node_CallFunction_5", "AttachPointName", "hand_r"),
                 (METHODS[1], "K2Node_CallFunction_5", "bStopWhenAttachedToDestroyed", "false"),
                 (METHODS[1], "K2Node_CallFunction_5", "bAutoDestroy", "true"),
                 (METHODS[1], "K2Node_CallFunction_6", "InName", "Fire"),
                 (METHODS[2], "K2Node_Select_0", "Option 1", "0"),
                 (METHODS[2], "K2Node_CallFunction_1", "bIncludeChildActors", "true"),
                 (METHODS[3], "K2Node_CallFunction_3", "bIncludeChildActors", "true")): default(*args)
    stencil_calls = [str(value.FunctionReference.MemberName) for value in graphs[METHODS[2]].Nodes if value.get_class().get_name() == "K2Node_CallFunction"]
    if "IsPlayerControlled" in stencil_calls or "IsLocallyControlled" not in stencil_calls: raise RuntimeError("weapon local-control rule differs from audited BP")
    return dict(fake_count_clamped_nonnegative=True, fake_trace_distance=1000000., fake_socket="Muzzle",
        fake_trace_channel="TraceTypeQuery1", fake_append_order=["ImpactSurfaceTypes", "Impact Positions", "Impact Normals"],
        audio_socket="hand_r", audio_trigger="Fire", audio_reuses_existing_component=True,
        stencil_local_control_only=True, includes_child_actors=True, team_colors_require_valid_asset_and_opt_in=True)


def generate(stage):
    marker = json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))
    source = Path(marker["source"]).parent
    original = source/RELATIVE
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original weapon parent required")
    ue.unregister_all_mixins()
    bp = ue.load_object(Blueprint, PACKAGE)
    before, class_name = snapshot(bp, "weapon-helpers-before"), bp.GeneratedClass.get_path_name()
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in METHODS+("Fire", "ReceiveBeginPlay")}
    originals = graph_hashes(bp)
    hashes = {graph.get_name(): semantics(graph, names, set()) for graph, names in originals}
    policy = audit(bp)
    child_before = {}
    for index, package in enumerate(CHILDREN):
        child = ue.load_object(Blueprint, package)
        child_before[package] = dict(cdo=snapshot(child, "weapon-child-before-"+str(index)),
            signatures={name: ue.describe_function(child.GeneratedClass, name) for name in METHODS})
    path = "/Game/UEPMixins/DA_WeaponActorHelpersMixin"
    if ue.find_asset(path+".DA_WeaponActorHelpersMixin") is not None: raise RuntimeError("fresh weapon helper Mixin Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset("DA_WeaponActorHelpersMixin", "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=name, PythonModule="uep_lyra_weapons.weapon_actor_helpers_mixin",
        PythonClass="LyraWeaponActorHelpers"+name+"Profile") for name in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile")
    ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != class_name or snapshot(bp, "weapon-helpers-after") != before: raise RuntimeError("weapon parent class/full CDO changed")
    if any(ue.describe_function(bp.GeneratedClass, name) != value for name, value in signatures.items()): raise RuntimeError("weapon original signatures/flags changed")
    if any(semantics(graph, names, set()) != hashes[graph.get_name()] for graph, names in originals): raise RuntimeError("weapon original business graph changed")
    try:
        ue.register_declared_mixin(bp.GeneratedClass)
        binding, = [row for row in ue.get_registered_mixins() if row["target_class"] == bp.GeneratedClass]
        counts = {name: len(row["functions"]) for name, row in binding["profiles"].items()}
        if counts != dict(Python=4, BlueprintFallback=4): raise RuntimeError("four original helpers per profile required")
    finally: ue.unregister_all_mixins()
    children = []
    for index, package in enumerate(CHILDREN):
        child = ue.load_object(Blueprint, package)
        if snapshot(child, "weapon-child-after-"+str(index)) != child_before[package]["cdo"]: raise RuntimeError("original child CDO changed")
        if any(ue.describe_function(child.GeneratedClass, name) != value for name, value in child_before[package]["signatures"].items()): raise RuntimeError("original inherited helper signature changed")
        cdo = child.GeneratedClass.get_cdo()
        if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python": raise RuntimeError("child did not inherit parent declaration")
        # The child inherits this declaration and parent UFunctions. It does
        # not independently declare an Interface; the registry rightly rejects
        # treating it as a second binding. Actual child calls are tested later.
        owners = {name: ue.describe_function(child.GeneratedClass, name)["owner"] for name in METHODS}
        if any(value != class_name for value in owners.values()): raise RuntimeError("child has an unexpected helper override")
        children.append(dict(package=package, original_cdo_and_signatures_preserved=True,
            inherited_declaration_verified=True, original_helper_owners=owners, independent_child_registration=False))
    bp.save_package(); mixin.save_package()
    return dict(status="passed", kind="weaponactorhelpers", runtime_acceptance=False, full_acceptance=False,
        original_class=class_name, original_class_defaults_signature_graphs_preserved=True, original_full_cdo_preserved=True,
        original_graphs_unmodified=True, original_graphs=hashes, extra_signatures=signatures, original_helper_policy=policy,
        actual_registered_profile_method_counts=counts, native_register_restore_passed=True, inherited_children=children,
        implemented_methods=list(METHODS), new_business_nodes=0, native_end_adapter_nodes=0,
        fire_and_begin_play_migrated=False, assets=[RELATIVE, "Content/UEPMixins/DA_WeaponActorHelpersMixin.uasset"],
        reference_hashes={str(original): digest})
