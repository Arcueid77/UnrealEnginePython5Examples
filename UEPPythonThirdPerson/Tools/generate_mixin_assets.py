"""Generate the playable and regression Blueprint Mixin assets."""

import json
from pathlib import Path
import sys
import traceback

import unreal_engine as ue
from unreal_engine.classes import (
    Blueprint,
    DataAssetFactory,
    InstancedStaticMeshComponent,
    UEPPythonMixinSet,
)
from unreal_engine.structs import UEPPythonMixinProfile


RESULT_PREFIX = "-UEPGenerateMixinAssetsResult="

TEST_ASSET_ROOT = "/Game/UEPTests"
MIXIN_SET_ASSET = f"{TEST_ASSET_ROOT}/DA_MixinInterfaceProbe"
PROBE_BLUEPRINT = f"{TEST_ASSET_ROOT}/BP_MixinInterfaceProbe"
CHILD_BLUEPRINT = f"{TEST_ASSET_ROOT}/BP_MixinInterfaceProbeChild"

CHARACTER_MIXIN_ROOT = "/Game/UEPMixins"
CHARACTER_MIXIN_SET = f"{CHARACTER_MIXIN_ROOT}/DA_ThirdPersonCharacterMixin"
CHARACTER_BLUEPRINT = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
CHARACTER_PROFILE_VARIABLE = "PythonMixinProfile"
PYTHON_PROFILE = "Python"
BLUEPRINT_FALLBACK_PROFILE = "BlueprintFallback"


def object_path(package_path):
    return f"{package_path}.{package_path.rsplit('/', 1)[-1]}"


def command_line_value(prefix):
    for argument in sys.argv:
        if argument.startswith(prefix):
            return argument[len(prefix):].strip('"')
    return None


def create_mixin_set(name, root):
    factory = DataAssetFactory()
    factory.DataAssetClass = UEPPythonMixinSet
    return ue.create_asset(name, root, UEPPythonMixinSet, factory)


def load_or_create_mixin_set(name, root):
    package_path = f"{root}/{name}"
    existing = ue.find_asset(object_path(package_path))
    if existing is not None and existing.is_valid():
        return existing
    return create_mixin_set(name, root)


def load_or_create_blueprint(parent_class, asset_path):
    existing = ue.find_asset(object_path(asset_path))
    if existing is not None and existing.is_valid():
        return existing
    return ue.create_blueprint(parent_class, asset_path)


def generate():
    mixin_set = load_or_create_mixin_set(
        "DA_MixinInterfaceProbe",
        TEST_ASSET_ROOT,
    )
    mixin_set.DefaultProfile = "BlueprintFallback"
    mixin_set.Profiles = [
        UEPPythonMixinProfile(
            ProfileName="ArrayRoute",
            PythonModule="uep_third_person_mixin.interface_probe",
            PythonClass="ArrayRouteProfile",
        ),
        UEPPythonMixinProfile(
            ProfileName="BlueprintFallback",
            PythonModule="uep_third_person_mixin.interface_probe",
            PythonClass="BlueprintFallbackProfile",
        ),
    ]

    probe = load_or_create_blueprint(
        InstancedStaticMeshComponent,
        PROBE_BLUEPRINT,
    )
    # Loading an existing direct Interface owner can immediately trigger the
    # package-completion discovery hook. Restore it before editing/compiling.
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(
        probe,
        mixin_set,
        "BlueprintFallback",
    )
    ue.compile_blueprint(probe)

    child = load_or_create_blueprint(probe.GeneratedClass, CHILD_BLUEPRINT)
    ue.compile_blueprint(child)

    character_mixin_set = load_or_create_mixin_set(
        "DA_ThirdPersonCharacterMixin",
        CHARACTER_MIXIN_ROOT,
    )
    character_mixin_set.DefaultProfile = PYTHON_PROFILE
    character_mixin_set.Profiles = [
        UEPPythonMixinProfile(
            ProfileName=PYTHON_PROFILE,
            PythonModule="uep_third_person_mixin.character_mixin",
            PythonClass="ThirdPersonPythonProfile",
        ),
        UEPPythonMixinProfile(
            ProfileName=BLUEPRINT_FALLBACK_PROFILE,
            PythonModule="uep_third_person_mixin.character_mixin",
            PythonClass="ThirdPersonBlueprintFallbackProfile",
        ),
    ]

    character = ue.load_object(Blueprint, CHARACTER_BLUEPRINT)
    if character is None or not character.is_valid():
        raise RuntimeError("unable to load the staged Third Person character Blueprint")
    ue.unregister_all_mixins()
    ue.blueprint_configure_mixin(
        character,
        character_mixin_set,
        PYTHON_PROFILE,
        CHARACTER_PROFILE_VARIABLE,
    )
    ue.compile_blueprint(character)

    character_cdo = character.GeneratedClass.get_cdo()
    if CHARACTER_PROFILE_VARIABLE not in character_cdo.properties():
        raise RuntimeError("character profile selector is not reflected on the CDO")
    selected_set = character_cdo.GetPythonMixinSet()
    selected_profile = str(character_cdo.GetPythonMixinProfile())
    if selected_set != character_mixin_set:
        raise RuntimeError("character Interface did not return its Mixin Set")
    if selected_profile != PYTHON_PROFILE:
        raise RuntimeError("character Interface did not return its profile variable")

    # Save explicitly: FEditorFileUtils::SaveDirtyPackages is intentionally
    # conservative in unattended commandlets and may leave new content packages
    # dirty without writing them to disk.
    character_mixin_set.save_package()
    character.save_package()
    mixin_set.save_package()
    probe.save_package()
    child.save_package()

    return {
        "schema_version": 2,
        "status": "passed",
        "assets": [
            CHARACTER_MIXIN_SET,
            CHARACTER_BLUEPRINT,
            MIXIN_SET_ASSET,
            PROBE_BLUEPRINT,
            CHILD_BLUEPRINT,
        ],
        "direct_interface_owner": probe.GeneratedClass.get_name(),
        "inherited_child": child.GeneratedClass.get_name(),
        "default_profile": mixin_set.DefaultProfile,
        "profile_count": len(mixin_set.Profiles),
        "character": {
            "blueprint": CHARACTER_BLUEPRINT,
            "generated_class": character.GeneratedClass.get_name(),
            "mixin_set": character_mixin_set.get_name(),
            "default_profile": character_mixin_set.DefaultProfile,
            "profile_count": len(character_mixin_set.Profiles),
            "profile_variable": CHARACTER_PROFILE_VARIABLE,
            "profile_value": selected_profile,
        },
    }


result_path = command_line_value(RESULT_PREFIX)
if not result_path:
    raise RuntimeError(f"missing {RESULT_PREFIX}<path>")

try:
    report = generate()
    ue.log("UEP_MIXIN_ASSET_GENERATION_PASSED")
except Exception:
    report = {
        "status": "failed",
        "error": traceback.format_exc(),
    }
    ue.log_error("UEP_MIXIN_ASSET_GENERATION_FAILED")

path = Path(result_path)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["status"] != "passed":
    raise RuntimeError(report["error"])
