"""Touch fire intent from Python; Enhanced Input and weapon abilities stay native."""

import unreal_engine as ue

from .weapon_observer import valid


CLICK_EVENT = "BndEvt__W_FireButton_ActionTouchButton_K2Node_ComponentBoundEvent_0_CommonButtonBaseClicked__DelegateSignature"


class LyraFireButtonPythonProfile:
    def __init__(self):
        self._uep_fire_button_clicks = 0

    def Clicked(self, Button):
        subsystem = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
            "GetLocalPlayerSubsystem", self, ue.find_class("EnhancedInputLocalPlayerSubsystem"))
        if not valid(subsystem):
            return
        # Preserve the two authored actions and FVector(1,1,1) exactly.
        # No native ammo, inventory, authority or GAS state is written here.
        for name in ("Associated Action", "Hold Action"):
            action = self.get_property(name)
            subsystem.call_function("InjectInputVectorForAction", action, ue.FVector(1.0, 1.0, 1.0))
        self._uep_fire_button_clicks += 1

    Clicked.override = CLICK_EVENT


class LyraFireButtonBlueprintFallbackProfile:
    def Clicked(self, Button):
        self.call_mixin_original(CLICK_EVENT, Button)

    Clicked.override = CLICK_EVENT
