"""Retained equipment-instance Interface/CDO authoring, no animation edits."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from mixin_graph_gates import semantics

RELATIVE = "Plugins/GameFeatures/ShooterCore/Content/Weapons/B_WeaponInstance_Base.uasset"
PACKAGE = "/ShooterCore/Weapons/B_WeaponInstance_Base.B_WeaponInstance_Base"
METHODS = ("K2_OnEquipped", "K2_OnUnequipped", "DetermineCosmeticTags")


def cdo_text(bp, label):
    directory = Path(next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPHeroAbilityAssetsResult="))).parent
    path = directory/("weapon-instance-"+label+"-cdo.t3d")
    exporter = ue.new_object(ue.find_class("ObjectExporterT3D"))
    if not exporter.export_to_file(bp.GeneratedClass.get_cdo(), str(path)): raise RuntimeError("native weapon CDO export failed")
    raw = path.read_bytes()
    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
    # Only the explicitly introduced selector/Set are allowed to differ.
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith(("PythonMixinProfile=", "PythonMixinSet=")))


def generate(stage):
    source = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    original = source/RELATIVE; digest = hashlib.sha256(original.read_bytes()).hexdigest()
    if hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest() != digest: raise RuntimeError("fresh original weapon instance required")
    bp = ue.load_object(Blueprint, PACKAGE); ue.unregister_all_mixins()
    original_class, previous = bp.GeneratedClass.get_path_name(), cdo_text(bp, "before")
    signatures = {name: ue.describe_function(bp.GeneratedClass, name) for name in METHODS}
    graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
    digests = {graph.get_name(): semantics(graph, names, set()) for graph, names in graphs}
    name = "DA_WeaponInstanceMixin"
    if ue.find_asset("/Game/UEPMixins/"+name+"."+name) is not None: raise RuntimeError("fresh weapon instance Mixin Set required")
    factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
    mixin = ue.create_asset(name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
    mixin.DefaultProfile = "Python"
    mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_weapons.weapon_instance_mixin",
        PythonClass="LyraWeaponInstance"+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
    ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp); ue.unregister_all_mixins()
    if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or cdo_text(bp, "after") != previous:
        raise RuntimeError("original weapon class/defaults/compilation changed")
    for method, description in signatures.items():
        if ue.describe_function(bp.GeneratedClass, method) != description: raise RuntimeError("original weapon public signature changed: "+method)
    for graph, names in graphs:
        if semantics(graph, names, set()) != digests[graph.get_name()]: raise RuntimeError("original weapon business graph changed")
    cdo = bp.GeneratedClass.get_cdo()
    if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python": raise RuntimeError("weapon Interface/CDO mismatch")
    bp.save_package(); mixin.save_package()
    if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("official weapon instance changed")
    return dict(status="passed", kind="weaponinstance", schema_version=1, runtime_acceptance=False, full_acceptance=False,
        original_class=original_class, original_signature=signatures[METHODS[0]], extra_signatures=signatures,
        original_graphs=digests, original_class_defaults_signature_graphs_preserved=True, native_end_adapter_nodes=0,
        default_cdo_snapshot_sha256=hashlib.sha256(previous.encode()).hexdigest(), cdo_snapshot_allowed_new_fields=["PythonMixinProfile", "PythonMixinSet"],
        assets=[RELATIVE, "Content/UEPMixins/"+name+".uasset"], reference_hashes={str(original): digest})
