"""Retained DebugWeaponSpread Tick; native weapon calculation/text formatting."""

import unreal_engine as ue


CLASS = "/ShooterCore/UserInterface/HUD/W_DebugWeaponSpreadWidget.W_DebugWeaponSpreadWidget_C"


def format_angle(value):
    # Exact authored Conv_DoubleToText defaults, including culture/rounding.
    return ue.find_class("KismetTextLibrary").get_cdo().call_function(
        "Conv_DoubleToText", float(value), 0, False, True, 1, 324, 0, 3)


class LyraDebugSpreadPythonProfile:
    def __init__(self):
        self._uep_debug_spread_ticks = 0
        self._uep_debug_spread_last = None

    def Tick(self, MyGeometry, InDeltaTime):
        angle = float(self.call_function("ComputeSpreadAngle"))
        self.CommonTextBlock_52.call_function("SetText", format_angle(angle))
        self._uep_debug_spread_last = angle
        self._uep_debug_spread_ticks += 1


class LyraDebugSpreadBlueprintFallbackProfile:
    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)
