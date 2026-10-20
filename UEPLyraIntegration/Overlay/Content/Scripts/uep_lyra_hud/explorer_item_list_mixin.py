"""Original item-acquired list order; native text/object/delegate transports."""
CLASS='/ShooterExplorer/UserInterface/W_ItemAcquiredList.W_ItemAcquiredList_C'
BOUND='BndEvt__W_ItemAcquiredList_ToastListWidget_K2Node_ComponentBoundEvent_0_OnListEntryInitializedDynamic__DelegateSignature'
LISTEN='UEPExplorerItemListBeginNativeListen'
FIND='UEPExplorerItemListFindNativeFragment'
CREATE='UEPExplorerItemListCreateNativeToast'
BIND='UEPExplorerItemListBindNativeExpiry'
MESSAGE='UEPExplorerItemListInventoryChanged'
CHANNEL='Lyra.Inventory.Message.StackChanged'
def evidence(w):
    if not hasattr(w,'_uep_explorer_item_list'):w._uep_explorer_item_list={p+'_'+m:0 for p in ('python','fallback') for m in ('construct','message','visible','remove','bind')};w._uep_explorer_item_list.update(native_finds=0,native_creates=0,ignored=0)
    return w._uep_explorer_item_list
def construct(w):evidence(w)['python_construct']+=1;w.call_function('UpdateDisplayVisibility');w.call_function(LISTEN)
def message(w,Instance,Delta:int):
    counts=evidence(w);counts['python_message']+=1;fragment=w.call_function(FIND,Instance);counts['native_finds']+=1
    if Delta>0:
        value=w.call_function(CREATE,fragment,Delta);counts['native_creates']+=1;w.get_property('ToastListWidget').call_function('AddItem',value);w.call_function('UpdateDisplayVisibility')
    else:counts['ignored']+=1
    return False
def visibility(w):evidence(w)['python_visible']+=1;w.get_property('DisplayVBox').call_function('SetVisibility',0 if w.get_property('ToastListWidget').call_function('GetNumItems')>0 else 1)
def remove(w,ItemPtr):evidence(w)['python_remove']+=1;w.get_property('ToastListWidget').call_function('RemoveItem',ItemPtr);w.call_function('UpdateDisplayVisibility')
def bind(w,Item,Widget):evidence(w)['python_bind']+=1;w.call_function(BIND,Widget)
class LyraExplorerItemListPythonProfile:
    def Construct(self):construct(self)
    def InventoryChanged(self,Instance,Delta:int):return message(self,Instance,Delta)
    InventoryChanged.override=MESSAGE
    def UpdateDisplayVisibility(self):visibility(self)
    def RemoveToast(self,ItemPtr):remove(self,ItemPtr)
    def EntryInitialized(self,Item,Widget):bind(self,Item,Widget)
    EntryInitialized.override=BOUND
class LyraExplorerItemListBlueprintFallbackProfile:
    def Construct(self):evidence(self)['fallback_construct']+=1;self.call_mixin_original('Construct')
    def InventoryChanged(self,Instance,Delta:int):evidence(self)['fallback_message']+=1;return True
    InventoryChanged.override=MESSAGE
    def UpdateDisplayVisibility(self):evidence(self)['fallback_visible']+=1;self.call_mixin_original('UpdateDisplayVisibility')
    def RemoveToast(self,ItemPtr):evidence(self)['fallback_remove']+=1;self.call_mixin_original('RemoveToast',ItemPtr)
    def EntryInitialized(self,Item,Widget):evidence(self)['fallback_bind']+=1;self.call_mixin_original(BOUND,Item,Widget)
    EntryInitialized.override=BOUND
