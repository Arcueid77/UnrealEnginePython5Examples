"""Quickbar UI business; inventory/equipment/GAS/replication stay native.

The named-output query uses explicit dictionary-output opt-in. BP callers and
Python entries reach the same routed function without changing widget type.
"""
import copy
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LinearColor
from uep_runtime import SubscriptionScope
from .weapon_observer import valid
from . import pooled_widget_lifetime as pools

CLASS = "/ShooterCore/UserInterface/HUD/W_QuickBarSlot.W_QuickBarSlot_C"
RESUME = "UEPResumeQuickBarSlotObservation"
MOUSE = "On_SelectionBorder_MouseButtonDown_0"
ROWS = (("Lyra.QuickBar.Message.SlotsChanged", "LyraQuickBarSlotsChangedMessage", "ReadQuickBarSlots", "UEPOriginalSlotsProxy"),
        ("Lyra.QuickBar.Message.ActiveIndexChanged", "LyraQuickBarActiveIndexChangedMessage", "ReadQuickBarActiveIndex", "UEPOriginalActiveIndexProxy"))
_active = {}
_stats = {"scopes_created": 0, "scopes_closed": 0, "slot_messages": 0, "active_messages": 0, "foreign_messages": 0,
          "ticks": 0, "slot_updates": 0, "selection_updates": 0, "ammo_updates": 0, "mouse_calls": 0,
          "named_query_calls": 0, "errors": []}


def snapshot():
    return dict(copy.deepcopy(_stats), active_count=len(_active), active_widgets=list(_active.values()),
                external_named_query_migrated=True, pool_lifetime=pools.snapshot())


def native_active(widget):
    component = widget.QuickBarComponent
    return valid(component) and int(component.call_function("GetActiveSlotIndex")) == int(widget.SlotIndex)


def active_query(widget):
    values = widget.call_function("IsThisTheActiveQuickbarSlot")
    if type(values) is not tuple or len(values) != 1 or type(values[0]) is not bool:
        raise RuntimeError("quickbar named output shape differs")
    return values[0]


def payload(widget, proxy, reader):
    value, success = widget._uep_slot_reader.call_function(reader, proxy)
    if success is not True:
        raise RuntimeError("typed quickbar payload extraction failed: " + reader)
    return value


def receive(widget, value, slots):
    if value.Owner != widget.call_function("GetOwningPlayer"):
        widget._uep_slot_foreign += 1
        _stats["foreign_messages"] += 1
        return
    if slots:
        entries, index = list(value.Slots), int(widget.SlotIndex)
        if 0 <= index < len(entries):
            widget.call_function("UpdateSlot", entries[index])
        widget._uep_slot_messages += 1
        _stats["slot_messages"] += 1
    else:
        # The authored BP does not use payload.ActiveIndex for selection: it
        # queries its native component, including when a message is synthetic.
        widget.call_function("UpdateIsSelected")
        widget._uep_slot_active_messages += 1
        _stats["active_messages"] += 1


def start(widget):
    if widget._uep_slot_scope is not None:
        return
    pools.refresh()
    if not pools.may_activate(widget):
        return
    helper = ue.new_object(widget.PythonMessageAdapterClass)
    helper.add_to_root()
    scope = SubscriptionScope()
    widget._uep_slot_scope, widget._uep_slot_reader = scope, helper
    try:
        for channel, struct_name, reader, original in ROWS:
            scope.listen_gameplay_message(widget, channel, ue.find_struct(struct_name),
                lambda proxy, name=reader: payload(widget, proxy, name),
                lambda channel, value, slots=reader == "ReadQuickBarSlots": receive(widget, value, slots))
    except Exception:
        scope.close()
        helper.remove_from_root()
        widget._uep_slot_scope = widget._uep_slot_reader = None
        raise
    _active[id(widget)] = widget.get_path_name()
    _stats["scopes_created"] += 1
    try:
        pools.watch(widget, lambda value: close(value, keep_pool_watch=True), lambda value: value.call_function(RESUME))
    except Exception:
        close(widget)
        raise


def close(widget, keep_pool_watch=False):
    if not keep_pool_watch:
        pools.unwatch(widget)
    scope, helper = widget._uep_slot_scope, widget._uep_slot_reader
    widget._uep_slot_scope = widget._uep_slot_reader = None
    _active.pop(id(widget), None)
    try:
        if scope is not None:
            scope.close()
            _stats["scopes_closed"] += 1
    except Exception as error:
        _stats["errors"].append(str(error))
        raise
    finally:
        if valid(helper):
            helper.remove_from_root()


def close_original(widget):
    for channel, struct_name, reader, name in ROWS:
        proxy = getattr(widget, name)
        setattr(widget, name, None)
        if valid(proxy):
            proxy.call_function("Cancel")


class LyraQuickBarSlotPythonProfile:
    def __init__(self):
        self._uep_pool_owner = getattr(self, "_uep_pool_owner", None)
        self._uep_slot_scope = self._uep_slot_reader = None
        self._uep_slot_messages = self._uep_slot_active_messages = self._uep_slot_foreign = 0
        self._uep_slot_ticks = self._uep_slot_mouse_calls = 0
        self._uep_slot_named_queries = 0

    def OnInitialized(self):
        self.call_function("UpdateSlot", None)
        start(self)

    def Construct(self):
        start(self)  # Idempotent remount; never replay OnInitialized.

    def ResumeObservation(self):
        start(self)

    ResumeObservation.override = RESUME

    def Tick(self, MyGeometry, InDeltaTime):
        start(self)
        if self._uep_slot_scope is None:
            return
        controller = self.call_function("GetOwningPlayer")
        component = controller.get_component_by_type(ue.find_class("LyraQuickBarComponent")) if valid(controller) else None
        self.call_function("UpdateComponentRef", component)
        if valid(self.QuickBarComponent):
            self.call_function("UpdateTotalAmmoLeft", self.QuickBarComponent)
        self._uep_slot_ticks += 1
        _stats["ticks"] += 1

    def UpdateComponentRef(self, QuickBarComponent):
        if QuickBarComponent == self.QuickBarComponent:
            return
        self.QuickBarComponent = QuickBarComponent
        if not valid(QuickBarComponent):
            return  # Authored invalid component leaves old presentation intact.
        entries, index = list(QuickBarComponent.call_function("GetSlots")), int(self.SlotIndex)
        self.call_function("UpdateSlot", entries[index] if 0 <= index < len(entries) else None)
        self.call_function("UpdateIsSelected")

    def UpdateSlot(self, Item):
        _stats["slot_updates"] += 1
        fragment = Item.call_function("FindFragmentByClass", ue.find_class("InventoryFragment_QuickBarIcon")) if valid(Item) else None
        if not valid(fragment):
            if not self.IsEmpty:
                self.IsEmpty = True
                self.call_function("PlayAnimationForward", self.ToEmpty, 1.0, False)
            return
        # Failed casts stop the authored execution chain. Do not clear stale
        # icons or mark a slot populated to "improve" template behavior.
        texture = fragment.Brush.ResourceObject
        if not valid(texture) or not texture.is_a(ue.find_class("Texture")):
            return
        self.WeaponCard.call_function("GetDynamicMaterial").call_function("SetTextureParameterValue", "IconTexture", texture)
        ammo = fragment.AmmoBrush.ResourceObject
        if not valid(ammo) or not ammo.is_a(ue.find_class("Texture")):
            return
        self.AmmoIcon.call_function("GetDynamicMaterial").call_function("SetTextureParameterValue", "TextureMask", ammo)
        if self.IsEmpty:
            self.IsEmpty = False
            self.call_function("PlayAnimationReverse", self.ToEmpty, 1.0, False)
            if not active_query(self):
                self.call_function("PlayAnimationForward", self.ActiveToInactive, 1.0, False)

    def UpdateIsSelected(self):
        _stats["selection_updates"] += 1
        if self.IsEmpty:
            return
        if active_query(self):
            self.IsSelected = True
            self.call_function("PlayAnimationForward", self.InactiveToActive, 1.0, False)
        elif self.IsSelected:
            if self.call_function("IsAnimationPlaying", self.InactiveToActive):
                self.call_function("StopAnimation", self.InactiveToActive)
            self.IsSelected = False
            self.call_function("PlayAnimationForward", self.ActiveToInactive, 1.0, False)

    def IsThisTheActiveQuickbarSlot(self):
        self._uep_slot_named_queries += 1
        _stats["named_query_calls"] += 1
        return {"IsActive": bool(native_active(self))}

    IsThisTheActiveQuickbarSlot.uep_named_outputs = True

    def UpdateTotalAmmoLeft(self, QuickBarComponent):
        entries, index = list(QuickBarComponent.call_function("GetSlots")), int(self.SlotIndex)
        if self.IsEmpty or not (0 <= index < len(entries)):
            return
        item = entries[index]
        if not valid(item):
            return
        spare = item.call_function("GetStatTagStackCount", GameplayTag(TagName="Lyra.ShooterGame.Weapon.SpareAmmo"))
        magazine = item.call_function("GetStatTagStackCount", GameplayTag(TagName="Lyra.ShooterGame.Weapon.MagazineAmmo"))
        total = ue.find_class("KismetMathLibrary").get_cdo().call_function("Add_IntInt", spare, magazine)
        self.WeaponAmmoCount.call_function("SetCurrentValue", float(total))
        _stats["ammo_updates"] += 1

    def MouseDown(self, MyGeometry, MouseEvent):
        ue.find_class("KismetSystemLibrary").get_cdo().call_function("PrintString", self, "slot pushed boom", True, True,
            LinearColor(R=0.0, G=0.66, B=1.0, A=1.0), 2.0, "None")
        subsystem = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetLocalPlayerSubsystem", self,
            ue.find_class("EnhancedInputLocalPlayerSubsystem"))
        if valid(subsystem):
            helper = self._uep_slot_reader
            temporary = not valid(helper)
            if temporary:
                helper = ue.new_object(self.PythonMessageAdapterClass)
                helper.add_to_root()
            try:
                helper.call_function("InjectAxis1DForAction", subsystem, self.SlotInputAction, 1.0)
            finally:
                if temporary:
                    helper.remove_from_root()
        self._uep_slot_mouse_calls += 1
        _stats["mouse_calls"] += 1
        return ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("Handled")

    MouseDown.override = MOUSE

    def Destruct(self):
        close(self)

    def __uep_mixin_teardown__(self):
        close(self)


class LyraQuickBarSlotBlueprintFallbackProfile:
    def OnInitialized(self):
        self.call_mixin_original("OnInitialized")

    def ResumeObservation(self):
        if not all(valid(getattr(self, row[3])) and getattr(self, row[3]).call_function("IsActive") for row in ROWS):
            close_original(self)
            self.call_mixin_original(RESUME)

    ResumeObservation.override = RESUME

    def Construct(self):
        self.call_mixin_original("Construct")
        self.call_function(RESUME)

    def Tick(self, MyGeometry, InDeltaTime):
        self.call_mixin_original("Tick", MyGeometry, InDeltaTime)

    def UpdateSlot(self, Item):
        self.call_mixin_original("UpdateSlot", Item)

    def UpdateComponentRef(self, QuickBarComponent):
        self.call_mixin_original("UpdateComponentRef", QuickBarComponent)

    def UpdateIsSelected(self):
        self.call_mixin_original("UpdateIsSelected")

    def UpdateTotalAmmoLeft(self, QuickBarComponent):
        self.call_mixin_original("UpdateTotalAmmoLeft", QuickBarComponent)

    def MouseDown(self, MyGeometry, MouseEvent):
        return self.call_mixin_original(MOUSE, MyGeometry, MouseEvent)

    MouseDown.override = MOUSE

    def Destruct(self):
        close_original(self)

    def __uep_mixin_teardown__(self):
        close_original(self)
