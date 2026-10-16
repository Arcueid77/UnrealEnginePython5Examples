"""Retained touch-menu click, preserving native lazy CommonUI push semantics."""

import unreal_engine as ue
from unreal_engine.structs import GameplayTag

from .weapon_observer import valid


CLICK_EVENT = "BndEvt__W_OpenMenuTouchButton_OpenButton_K2Node_ComponentBoundEvent_1_CommonButtonBaseClicked__DelegateSignature"
MENU_CLASS = "/Game/UI/Hud/W_LyraGameMenu.W_LyraGameMenu_C"


class LyraOpenMenuPythonProfile:
    def __init__(self):
        self._uep_open_menu_clicks = 0

    def Clicked(self, Button):
        controller = self.call_function("GetOwningPlayer")
        proxy = ue.find_class("AsyncAction_PushContentToLayerForPlayer").get_cdo().call_function(
            "PushContentToLayerForPlayer", controller, MENU_CLASS, GameplayTag(TagName="UI.Layer.Menu"), True)
        if valid(proxy):
            # The native action registers with GameInstance and owns streaming,
            # input suspension and layer insertion. Never preload the UClass.
            proxy.call_function("Activate")
            self._uep_open_menu_clicks += 1

    Clicked.override = CLICK_EVENT


class LyraOpenMenuBlueprintFallbackProfile:
    def Clicked(self, Button):
        self.call_mixin_original(CLICK_EVENT, Button)

    Clicked.override = CLICK_EVENT
