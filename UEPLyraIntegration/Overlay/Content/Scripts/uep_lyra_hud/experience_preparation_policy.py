"""Original pure UserWidget-class cast, setter and completed continuation."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
AFTER='UEPUIExperienceNativePrepared'
KEY='preparation_loaded'
def finish(widget,loaded_class,continuation=AFTER):
    # Original pure cast has no failure execution branch:invalid class still
    # clears the loading widget and continues after the native async load.
    selected=loaded_class if valid(loaded_class) and loaded_class.is_child_of(ue.find_class('UserWidget')) else None
    subsystem=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',widget,ue.find_class('LyraLoadingScreenSubsystem'))
    subsystem.call_function('SetLoadingScreenContentWidget',selected)
    widget.call_function(continuation)
