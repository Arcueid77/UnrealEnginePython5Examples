"""Explorer helper policies; empty loadouts retain their native unarmed layer."""
from .quickbar_input_mixin import LyraCharacterQuickbarPythonProfile as SharedPython,LyraCharacterQuickbarBlueprintFallbackProfile as SharedFallback
from .inventory_clear_mixin import components,valid

CLASSES={key:'/ShooterExplorer/Blueprint/'+name+'.'+name+'_C' for key,name in (('hero','B_Hero_Explorer'),('pawn','B_Pawn_Explorer'))}
METHODS=('ClearInventory','GetEmoteAudioComponent','SetEmoteAudioComponent','ChangeQuickbarSlot','AddInitialInventory')
UNARMED='UEPExplorerNativeUnarmedLayer'

def evidence(actor):
    if not hasattr(actor,'_uep_explorer_helpers'):actor._uep_explorer_helpers=dict(python_grants=0,fallback_grants=0,authority_noops=0,controller_noops=0,inventory_noops=0,null_quickbar_native_fallbacks=0,definitions_added=0,slot_add_attempts=0,slot_zero_requests=0,unarmed_requests=0)
    return actor._uep_explorer_helpers

class LyraExplorerHelpersPythonProfile:
    ClearInventory=SharedPython.ClearInventory
    GetEmoteAudioComponent=SharedPython.GetEmoteAudioComponent
    SetEmoteAudioComponent=SharedPython.SetEmoteAudioComponent
    ChangeQuickbarSlot=SharedPython.ChangeQuickbarSlot
    def AddInitialInventory(self):
        counts=evidence(self);counts['python_grants']+=1
        if not self.call_function('HasAuthority'):counts['authority_noops']+=1;return
        controller=self.call_function('GetController')
        if not valid(controller):counts['controller_noops']+=1;return
        quickbar,inventory=components(controller)
        if not valid(inventory):counts['inventory_noops']+=1;return
        if not valid(quickbar):
            # Original only guards InventoryManager. Preserve its null-receiver diagnostics.
            counts['null_quickbar_native_fallbacks']+=1;self.call_mixin_original('AddInitialInventory');return
        definitions=list(self.get_property('InitialInventoryItems'))
        for index,definition in enumerate(definitions):
            item=inventory.call_function('AddItemDefinition',definition,1);counts['definitions_added']+=1
            quickbar.call_function('AddItemToSlot',index,item);counts['slot_add_attempts']+=1
        if definitions:quickbar.call_function('SetActiveSlotIndex',0);counts['slot_zero_requests']+=1
        else:self.call_function(UNARMED);counts['unarmed_requests']+=1

class LyraExplorerHelpersBlueprintFallbackProfile:
    ClearInventory=SharedFallback.ClearInventory
    GetEmoteAudioComponent=SharedFallback.GetEmoteAudioComponent
    SetEmoteAudioComponent=SharedFallback.SetEmoteAudioComponent
    ChangeQuickbarSlot=SharedFallback.ChangeQuickbarSlot
    def AddInitialInventory(self):evidence(self)['fallback_grants']+=1;self.call_mixin_original('AddInitialInventory')
