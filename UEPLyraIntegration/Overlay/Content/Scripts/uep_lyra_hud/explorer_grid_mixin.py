"""Original inventory grid order and exact-channel message decisions."""
import unreal_engine as ue

CLASS='/ShooterExplorer/UserInterface/W_InventoryGrid.W_InventoryGrid_C'
LISTEN='UEPExplorerGridBeginNativeListen'
MESSAGE='UEPExplorerGridInventoryChanged'
CHANNEL='Lyra.Inventory.Message.StackChanged'

def evidence(widget):
    if not hasattr(widget,'_uep_explorer_grid'):widget._uep_explorer_grid=dict(python_construct=0,fallback_construct=0,python_messages=0,fallback_messages=0,native_listens=0,added=0,removed=0,ignored=0,payloads=[])
    return widget._uep_explorer_grid

def construct(widget):
    counts=evidence(widget);counts['python_construct']+=1;controller=widget.call_function('GetOwningPlayer');inventory=controller.call_function('GetComponentByClass',ue.find_class('LyraInventoryManagerComponent'));widget.set_property('NewVar_0',inventory);tiles=widget.get_property('TileViewWidget');tiles.call_function('ClearListItems')
    for item in inventory.call_function('GetAllItems'):tiles.call_function('AddItem',item)
    widget.call_function(LISTEN);counts['native_listens']+=1

def message(widget,Instance,NewCount:int,Delta:int):
    counts=evidence(widget);counts['python_messages']+=1;counts['payloads'].append([int(NewCount),int(Delta)]);tiles=widget.get_property('TileViewWidget')
    if NewCount==Delta:tiles.call_function('AddItem',Instance);counts['added']+=1
    elif NewCount==0:tiles.call_function('RemoveItem',Instance);counts['removed']+=1
    else:counts['ignored']+=1
    return False

class LyraExplorerGridPythonProfile:
    def Construct(self):construct(self)
    def InventoryChanged(self,Instance,NewCount:int,Delta:int):return message(self,Instance,NewCount,Delta)
    InventoryChanged.override=MESSAGE

class LyraExplorerGridBlueprintFallbackProfile:
    def Construct(self):evidence(self)['fallback_construct']+=1;self.call_mixin_original('Construct')
    def InventoryChanged(self,Instance,NewCount:int,Delta:int):
        counts=evidence(self);counts['fallback_messages']+=1;counts['payloads'].append([int(NewCount),int(Delta)]);return True
    InventoryChanged.override=MESSAGE
