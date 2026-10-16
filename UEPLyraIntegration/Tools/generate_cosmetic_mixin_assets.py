"""Retained component BP Interface/CDO authoring; no animation or native edits."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(value for value in sys.argv if Path(value).name == "generate_cosmetic_mixin_assets.py")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage
from mixin_graph_gates import semantics


def arg(name):
    return next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-"+name+"="))


def serial(value):
    if hasattr(value, "get_path_name"): return value.get_path_name()
    if isinstance(value, (tuple, list)): return [serial(item) for item in value]
    return value


def defaults(cdo):
    return {key: serial(cdo.get_property(key)) for key in ("AvailableCharacterParts", "bReplicates", "bAutoActivate") if key in cdo.properties()}


def generate():
    stage = require_authoring_stage(arg("UEPCosmeticStageRoot"), ue.convert_relative_path_to_full(ue.get_content_dir()))
    official = Path(json.loads((stage/".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    ue.unregister_all_mixins()
    rows, references, outputs = [], {}, []
    for name, label, prefix in (("B_CharacterSelection", "CharacterSelection", "LyraCharacterSelection"),
                                ("B_PickRandomCharacter", "RandomCharacter", "LyraRandomCharacter")):
        relative = "Content/Characters/Cosmetics/"+name+".uasset"
        original = official/relative; digest = hashlib.sha256(original.read_bytes()).hexdigest()
        if hashlib.sha256((stage/relative).read_bytes()).hexdigest() != digest: raise RuntimeError("Fresh original cosmetic component required")
        bp = ue.load_object(Blueprint, "/Game/Characters/Cosmetics/"+name+"."+name)
        original_class = bp.GeneratedClass.get_path_name()
        previous, signature = defaults(bp.GeneratedClass.get_cdo()), ue.describe_function(bp.GeneratedClass, "ReceiveBeginPlay")
        graphs = [(graph, {node.get_name() for node in graph.Nodes}) for graph in ue.blueprint_get_all_graphs(bp)]
        digests = {graph.get_name(): semantics(graph, names, set()) for graph, names in graphs}
        asset = "DA_"+label+"Mixin"; asset_path = "/Game/UEPMixins/"+asset
        if ue.find_asset(asset_path+"."+asset) is not None: raise RuntimeError("Fresh cosmetic Mixin Set required")
        factory = DataAssetFactory(); factory.DataAssetClass = UEPPythonMixinSet
        mixin = ue.create_asset(asset, "/Game/UEPMixins", UEPPythonMixinSet, factory)
        mixin.DefaultProfile = "Python"
        mixin.Profiles = [UEPPythonMixinProfile(ProfileName=profile, PythonModule="uep_lyra_characters.cosmetics_mixin",
            PythonClass=prefix+profile+"Profile") for profile in ("Python", "BlueprintFallback")]
        ue.unregister_all_mixins(); ue.blueprint_configure_mixin(bp, mixin, "Python", "PythonMixinProfile"); ue.compile_blueprint(bp)
        cdo = bp.GeneratedClass.get_cdo()
        if int(bp.Status) == 2 or bp.GeneratedClass.get_path_name() != original_class or defaults(cdo) != previous or ue.describe_function(bp.GeneratedClass, "ReceiveBeginPlay") != signature:
            raise RuntimeError("Cosmetic class/default/signature/compile changed")
        if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python": raise RuntimeError("Cosmetic Interface/CDO not configured")
        for graph, names in graphs:
            if semantics(graph, names, set()) != digests[graph.get_name()]: raise RuntimeError("Original cosmetic business graph changed")
        bp.save_package(); mixin.save_package()
        if hashlib.sha256(original.read_bytes()).hexdigest() != digest: raise RuntimeError("Official cosmetic asset changed")
        references[str(original)] = digest
        outputs.extend((relative, "Content/UEPMixins/"+asset+".uasset"))
        rows.append(dict(path=original_class, defaults=previous, signature=signature, original_graphs=digests))
    return dict(status="passed", schema_version=1, runtime_acceptance=False, full_acceptance=False,
        original_classes_defaults_signatures_graphs_preserved=True, components=rows, assets=outputs, reference_hashes=references)


try: report = generate()
except Exception:
    report = dict(status="failed", error=traceback.format_exc()); ue.log_error(report["error"])
Path(arg("UEPCosmeticAssetsResult")).write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed": raise RuntimeError(report["error"])
ue.log("UEP_COSMETIC_ASSETS_PASSED")
