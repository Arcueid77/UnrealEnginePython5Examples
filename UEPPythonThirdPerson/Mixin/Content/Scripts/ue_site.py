"""Project startup hook for the UEP 0.7 Blueprint Mixin demo."""

import sys

sys.dont_write_bytecode = True

import unreal_engine as ue


ue.log("UEP_MIXIN_THIRD_PERSON_SCRIPT_LOADED")

is_asset_generation = any(
    argument.startswith("-UEPGenerateMixinAssetsResult=")
    for argument in sys.argv
)
is_commandlet = any(
    argument.lower().startswith("-run=")
    for argument in sys.argv
)

if is_asset_generation:
    ue.log("UEP_MIXIN_ASSET_GENERATION_BOOTSTRAP_SKIPPED")
elif is_commandlet:
    ue.log("UEP_MIXIN_COMMANDLET_BOOTSTRAP_SKIPPED")
else:
    from uep_third_person_mixin import bootstrap  # noqa: E402,F401
