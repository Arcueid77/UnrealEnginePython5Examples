"""Author the effect-pad parent only inside a marked disposable stage.

Related parent/child routers remain rejected by the production runtime.
Do not configure a child as though the existing inheritance guard were lifted.
"""

import hashlib
import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import Blueprint, DataAssetFactory, UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile

script = globals().get("__file__") or next(
    (value for value in sys.argv if Path(value).name == "generate_effect_pad_mixin_assets.py"), None)
if script is None:
    raise RuntimeError("pass the generator to the Py commandlet")
sys.path.insert(0, str(Path(script).resolve().parent))
from stage_safety import require_authoring_stage


def argument(name):
    prefix = "-" + name + "="
    return next((value[len(prefix):] for value in sys.argv if value.startswith(prefix)), None)


def generate():
    stage = require_authoring_stage(argument("UEPEffectPadStageRoot"),
                                    ue.convert_relative_path_to_full(ue.get_content_dir()))
    reference = Path(json.loads((stage / ".uep-lyra-full-stage.json").read_text(encoding="utf-8-sig"))["source"]).parent
    names = ("BP_GameplayEffectPad",)
    references = [(reference / "Content/Environments/Gameplay" / (name + ".uasset")) for name in names]
    hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in references}
    ue.unregister_all_mixins()
    blueprints = {name: ue.load_object(Blueprint, "/Game/Environments/Gameplay/" + name + "." + name)
                  for name in names}
    game_defaults = {name: {field: (getattr(bp.GeneratedClass.get_cdo(), field).get_path_name()
                                    if getattr(bp.GeneratedClass.get_cdo(), field) else None)
                            for field in ("GameplayEffectToApply", "GE_Damage", "GE_Heal",
                                          "MAT_DamagePad", "MAT_HealPad", "MAT_SpecialPad")}
                     for name, bp in blueprints.items()}
    rows = []
    for name in names:
        path = "/Game/Environments/Gameplay/" + name
        mixin_name = "DA_" + name + "Mixin"
        mixin_path = "/Game/UEPMixins/" + mixin_name
        mixin = ue.find_asset(mixin_path + "." + mixin_name)
        if mixin is None:
            factory = DataAssetFactory()
            factory.DataAssetClass = UEPPythonMixinSet
            mixin = ue.create_asset(mixin_name, "/Game/UEPMixins", UEPPythonMixinSet, factory)
        mixin.DefaultProfile = "Python"
        mixin.Profiles = [
            UEPPythonMixinProfile(ProfileName="Python", PythonModule="uep_lyra_world.effect_pad_mixin", PythonClass="LyraEffectPadPythonProfile"),
            UEPPythonMixinProfile(ProfileName="BlueprintFallback", PythonModule="uep_lyra_world.effect_pad_mixin", PythonClass="LyraEffectPadBlueprintFallbackProfile"),
        ]
        blueprint = blueprints[name]
        helpers = [graph for graph in ue.blueprint_get_all_graphs(blueprint)
                   if graph.get_name() == "UEPConstructEffectPad"]
        if not helpers:
            ue.blueprint_extract_construction_helper(blueprint, "UEPConstructEffectPad")
            ue.compile_blueprint(blueprint)
        construction = next(graph for graph in ue.blueprint_get_all_graphs(blueprint)
                            if graph.get_name() == "UserConstructionScript")
        if len(construction.Nodes) != 2:
            raise RuntimeError("Construction must contain only entry and virtual helper call")
        # Parent compilation can rediscover its declaration immediately.
        # Restore all routers again before touching the next child Blueprint.
        ue.unregister_all_mixins()
        ue.blueprint_configure_mixin(blueprint, mixin, "Python", "PythonMixinProfile")
        ue.compile_blueprint(blueprint)
        cdo = blueprint.GeneratedClass.get_cdo()
        if cdo.GetPythonMixinSet() != mixin or str(cdo.GetPythonMixinProfile()) != "Python":
            raise RuntimeError("Effect pad Interface/CDO postcondition differs: " + name)
        for field, expected in game_defaults[name].items():
            actual = getattr(cdo, field)
            if (actual.get_path_name() if actual else None) != expected:
                raise RuntimeError("Game default changed while configuring child: " + name + "." + field)
        mixin.save_package()
        blueprint.save_package()
        rows.append({"asset": path, "mixin_set": mixin_path,
                     "class_preserved": blueprint.GeneratedClass.get_name() == name + "_C",
                     "construction_forwarder_nodes": len(construction.Nodes),
                     "construction_helper": "UEPConstructEffectPad",
                     "effect": cdo.GameplayEffectToApply.get_path_name() if cdo.GameplayEffectToApply else None})
    for path, digest in hashes.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Official reference asset changed")
    return {"status": "passed", "assets": rows, "reference_hashes": hashes,
            "runtime_acceptance": False}


result = argument("UEPGenerateEffectPadResult")
if result is None:
    raise RuntimeError("UEPGenerateEffectPadResult required")
try:
    report = generate()
except Exception:
    report = {"status": "failed", "error": traceback.format_exc()}
Path(result).write_text(json.dumps(report, indent=2), encoding="utf-8")
ue.log("UEP_EFFECT_PAD_ASSETS_" + report["status"].upper())
if report["status"] != "passed":
    raise RuntimeError(report["error"])
