"""UI registration belongs to the native granted ability, not its Profile."""
import unreal_engine as ue
from uep_lyra_hud.weapon_observer import valid


def subsystem(ability):
    return ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
        "GetWorldSubsystem", ability, ue.find_class("UIExtensionSubsystem"))


def register(ability, native, widget, tag):
    owner = ability.call_function("GetOwningActorFromActorInfo")
    return native.call_function("K2_RegisterExtensionAsWidgetForContext", tag, widget, owner, -1)


def unregister(handle):
    ue.find_class("UIExtensionHandleFunctions").get_cdo().call_function("Unregister", handle)


def add_single(ability):
    widget = ability.WidgetClass
    if not ue.find_class("KismetSystemLibrary").get_cdo().call_function("IsValidClass", widget):
        return False
    native = subsystem(ability)
    if not valid(native):
        return False
    ability.set_property("WidgetExtensionHandle", register(ability, native, widget, ability.WidgetExtensionPointTag))
    return True


def remove_single(ability):
    # Match the original native handle function and retained reflected slot.
    # Profile teardown deliberately preserves this ability-lifetime ownership:
    # the next profile/original OnAbilityRemoved can unregister the same handle.
    unregister(ability.WidgetExtensionHandle)


def add_many(ability):
    native = subsystem(ability)
    if not valid(native):
        return 0
    handles = list(ability.WidgetExtensionHandles)
    tags = ability.WidgetExtensionPointTags
    for index, widget in enumerate(ability.WidgetClasses):
        handles.append(register(ability, native, widget, tags[index]))
        ability.set_property("WidgetExtensionHandles", handles)
    return len(ability.WidgetClasses)


def remove_many(ability):
    for handle in list(ability.WidgetExtensionHandles):
        unregister(handle)
    ability.set_property("WidgetExtensionHandles", [])


class LyraAbilityWidgetPythonProfile:
    def K2_OnAbilityAdded(self):
        add_many(self)

    def K2_OnAbilityRemoved(self):
        remove_many(self)


class LyraAbilityWidgetBlueprintFallbackProfile:
    def K2_OnAbilityAdded(self):
        self.call_mixin_original("K2_OnAbilityAdded")

    def K2_OnAbilityRemoved(self):
        self.call_mixin_original("K2_OnAbilityRemoved")
