"""Project startup hook for the UEP 0.7 Blueprint Mixin demo."""

import sys

sys.dont_write_bytecode = True

import unreal_engine as ue


ue.log("UEP_MIXIN_THIRD_PERSON_SCRIPT_LOADED")

from uep_third_person_mixin import bootstrap  # noqa: E402,F401
