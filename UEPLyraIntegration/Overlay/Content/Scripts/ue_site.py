"""Project startup hook for the staged UEP Lyra validation project."""

import sys

sys.dont_write_bytecode = True

import unreal_engine as ue


ue.log("UEP_LYRA_SCRIPT_LOADED")

is_commandlet = any(argument.lower().startswith("-run=") for argument in sys.argv)

if is_commandlet:
    ue.log("UEP_LYRA_COMMANDLET_BOOTSTRAP_SKIPPED")
else:
    from uep_lyra_hud import bootstrap  # noqa: E402,F401
    import uep_lyra_probe  # noqa: E402,F401
