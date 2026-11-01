"""Selection/grant policy; RPC, equip, inventory replication remain native."""
QUICK='/ShooterCore/Game/B_QuickBarComponent.B_QuickBarComponent_C'
INVENTORY='/Game/UEPNative/BP_InventoryManager.BP_InventoryManager_C'


def metrics(component):
    if not hasattr(component,'_uep_native_inventory_metrics'):
        component._uep_native_inventory_metrics={p+k:0 for p in ('python_','native_') for k in ('forward','backward','free','grant')}
    return component._uep_native_inventory_metrics


def cycle(component,direction):
    key='forward' if direction==1 else 'backward';metrics(component)['python_'+key]+=1
    slots=component.call_function('GetSlots');count=len(slots)
    if count<2:return
    active=int(component.call_function('GetActiveSlotIndex'));old=count-1 if active<0 else active;index=active
    while True:
        index=(index+1)%count if direction==1 else (index-1+count)%count
        if slots[index] is not None:
            component.call_function('SetActiveSlotIndex',index);return
        if index==old:return


class QuickPythonProfile:
    def CycleActiveSlotForward(self):return cycle(self,1)
    def CycleActiveSlotBackward(self):return cycle(self,-1)
    def GetNextFreeItemSlot(self):
        metrics(self)['python_free']+=1
        return next((i for i,item in enumerate(self.call_function('GetSlots')) if item is None),-1)


class QuickNativeFallbackProfile:
    def CycleActiveSlotForward(self):
        metrics(self)['native_forward']+=1;return self.call_mixin_original('CycleActiveSlotForward')
    def CycleActiveSlotBackward(self):
        metrics(self)['native_backward']+=1;return self.call_mixin_original('CycleActiveSlotBackward')
    def GetNextFreeItemSlot(self):
        metrics(self)['native_free']+=1;return self.call_mixin_original('GetNextFreeItemSlot')


class InventoryPythonProfile:
    def UEPGrantPickup(self,PickupInventory):
        metrics(self)['python_grant']+=1
        for template in PickupInventory.Templates:self.call_function('AddItemDefinition',template.ItemDef,int(template.StackCount))
        for instance in PickupInventory.Instances:self.call_function('AddItemInstance',instance.Item)


class InventoryNativeFallbackProfile:
    def UEPGrantPickup(self,PickupInventory):
        metrics(self)['native_grant']+=1;return self.call_mixin_original('UEPGrantPickup',PickupInventory)
