"""Escape menu request policy; CommonUI input and asynchronous push stay native."""
CLASSES=(
    '/Game/UI/FrontEnd/W_FrontEndHUDLayout.W_FrontEndHUDLayout_C',
    '/Game/UI/Hud/W_DefaultHUDLayout.W_DefaultHUDLayout_C',
    '/ShooterCore/UserInterface/W_ShooterHUDLayout.W_ShooterHUDLayout_C',
    '/TopDownArena/UserInterface/W_TopDownArenaHUDLayout.W_TopDownArenaHUDLayout_C',
)


def metrics(widget):
    if not hasattr(widget,'_uep_native_escape'):widget._uep_native_escape=dict(python_escape=0,native_escape=0,requested_paths=[])
    return widget._uep_native_escape


class EscapeMenuPythonProfile:
    def HandleEscapeAction(self):
        values=metrics(self);values['python_escape']+=1;path=self.call_function('UEPGetEscapeMenuPath')
        if path:values['requested_paths'].append(path);self.call_function('UEPPushEscapeMenu',path)


class EscapeMenuNativeFallbackProfile:
    def HandleEscapeAction(self):metrics(self)['native_escape']+=1;self.call_mixin_original('HandleEscapeAction')
