"""Arena PlayerState data registration; native UIExtension owns both handles."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag

CLASS='/TopDownArena/UserInterface/Player/B_PlayerUIComponent.B_PlayerUIComponent_C'
TAG='TopDownArena.ExtensionPoint.Players'

def evidence(component):
    value=getattr(component,'_uep_arena_player_ui',None)
    if value is None:
        value=dict(python_begin=0,python_end=0,fallback_begin=0,fallback_end=0,registrations=0,unregistrations=0)
        component._uep_arena_player_ui=value
    return value

class LyraArenaPlayerUIPythonProfile:
    def ReceiveBeginPlay(self):
        value=evidence(self);value['python_begin']+=1
        owner=self.call_function('GetOwner')
        # The original pure cast supplies null on a non-PlayerState owner.
        data=owner if owner is not None and owner.is_a(ue.find_class('LyraPlayerState')) else None
        subsystem=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self,ue.find_class('UIExtensionSubsystem'))
        self.set_property('ExtensionHandle',subsystem.call_function('K2_RegisterExtensionAsData',GameplayTag(TagName=TAG),data,-1));value['registrations']+=1

    def ReceiveEndPlay(self,EndPlayReason):
        value=evidence(self);value['python_end']+=1
        ue.find_class('UIExtensionHandleFunctions').get_cdo().call_function('Unregister',self.get_property('ExtensionHandle'));value['unregistrations']+=1

class LyraArenaPlayerUIBlueprintFallbackProfile:
    def ReceiveBeginPlay(self):
        evidence(self)['fallback_begin']+=1;self.call_mixin_original('ReceiveBeginPlay')
    def ReceiveEndPlay(self,EndPlayReason):
        evidence(self)['fallback_end']+=1;self.call_mixin_original('ReceiveEndPlay',EndPlayReason)
