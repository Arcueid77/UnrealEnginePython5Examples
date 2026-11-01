"""Authority fixtures use native pickup/interface and inventory operations."""
import unreal_engine as ue
from unreal_engine.structs import InventoryPickup,PickupTemplate
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world.inventory_pad_network_state import services,path

DEFINITIONS=['/ShooterCore/Weapons/'+n+'/ID_'+n+'.ID_'+n+'_C' for n in ('Pistol','Rifle','Shotgun')]


def entries(inventory):
    return [dict(definition=path(e.Instance.ItemDef),count=int(e.StackCount)) for e in inventory.get_property('InventoryList').Entries]


def grant(controller,templates,null_inventory=False):
    inventory,_=services(controller);before=list(inventory.call_function('GetAllItems'))
    actor=controller.get_world().actor_spawn(ue.load_class('/ShooterExplorer/Items/B_InteractableRock.B_InteractableRock_C'),ue.FVector(500000.,500000.,5000.))
    try:
        actor.set_property('StaticInventory',InventoryPickup(Templates=[PickupTemplate(ItemDef=ue.load_class(d),StackCount=n) for d,n in templates]))
        ue.find_class('PickupableStatics').get_cdo().call_function('AddPickupToInventory',None if null_inventory else inventory,actor)
        return [i for i in inventory.call_function('GetAllItems') if i not in before]
    finally:
        actor.call_function('K2_DestroyActor')
        if valid(actor):raise RuntimeError('Native pickup fixture survived destroy')


def fingerprint(controller):
    inventory,quickbar=services(controller)
    return dict(items=[path(i) for i in inventory.call_function('GetAllItems')],slots=[path(i) for i in quickbar.call_function('GetSlots')],active=int(quickbar.call_function('GetActiveSlotIndex')),entries=entries(inventory))
