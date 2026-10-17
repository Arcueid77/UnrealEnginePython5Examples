"""Test-only native event witnesses; selected production handler runs once."""
import copy
import traceback
import unreal_engine as ue
from . import grenade_widget_mixin as policy
from .auto_respawn_lifecycle_validation import ui_probe

PROFILES=(("Python",policy.LyraGrenadeWidgetPythonProfile),("BlueprintFallback",policy.LyraGrenadeWidgetBlueprintFallbackProfile))
METHODS=("K2_OnPawnAvatarSet","K2_OnAbilityRemoved")


def install(observer):
    cls=ue.load_class(policy.CLASS)
    for name,base in PROFILES:
        def around(handler,event,profile):
            def invoke(instance):
                row=None
                # Keep the target as POD after ClearAbility marks its instance
                # garbage; otherwise a quiet-period late call would be hidden.
                if instance.get_path_name()==observer.target_path:
                    try:
                        row=dict(method=event,profile=profile,before=ui_probe(instance),
                            owner=instance.call_function("GetOwningActorFromActorInfo").get_path_name(),
                            cls=instance.get_class().get_path_name(),native_callback=True)
                    except Exception: observer.observation_errors.append(traceback.format_exc())
                handler(instance)
                if row is not None:
                    try:
                        row.update(after=ui_probe(instance),counts=copy.deepcopy(policy.evidence(instance)))
                        observer.native_events.append(row)
                    except Exception: observer.observation_errors.append(traceback.format_exc())
            invoke.override=event
            return invoke
        ue.register_mixin_profile(cls,name,type("ObservedGrenadeWidget"+name,(),{event:around(base.__dict__[event],event,name) for event in METHODS}))


def restore():
    cls=ue.load_class(policy.CLASS)
    for name,base in PROFILES: ue.register_mixin_profile(cls,name,base)
    binding,=[value for value in ue.get_registered_mixins() if value["target_class"]==cls]
    return all(binding["profiles"][name]["python_class"] is base for name,base in PROFILES)
