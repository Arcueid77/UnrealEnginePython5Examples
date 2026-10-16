"""Read native GameplayEvent/Cue values without retaining their parameter frame."""
import unreal_engine as ue
from uep_lyra_hud.weapon_observer import valid

CUE = "/ShooterCore/GameplayCues/GCNL_Death.GCNL_Death_C"


def source_owner(death, respawn, dedicated_server=False):
    # AutoRespawn's BP Avatar event binds its health listener even when the
    # remote authority's LocalPredicted ability is inactive. AbilityTask events
    # require an active owner at dispatch, so use Death itself on authority.
    return death if dedicated_server else respawn


def path(value):
    return value.get_path_name() if valid(value) else None


def tags(container):
    values, = ue.find_class("BlueprintGameplayTagLibrary").get_cdo().call_function("BreakGameplayTagContainer", container)
    return sorted(str(value.TagName) for value in values)


def context(handle):
    native = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo()
    return {name: path(native.call_function(method, handle)) for name, method in (
        ("instigator", "EffectContextGetInstigatorActor"), ("causer", "EffectContextGetEffectCauser"),
        ("source", "EffectContextGetSourceObject"))}


def event(value):
    return dict(magnitude=float(value.EventMagnitude), tag=str(value.EventTag.TagName),
        target=path(value.Target), instigator=path(value.Instigator), context=context(value.ContextHandle),
        source_tags=tags(value.InstigatorTags), target_tags=tags(value.TargetTags))


def cue(target, params):
    values = ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("BreakGameplayCueParameters", params)
    normalized, raw, handle, matched, original, source, targets, location, normal, instigator, causer, obj, material, level, ability_level, attach, replicate = values
    return dict(target=path(target), normalized=float(normalized), raw=float(raw), context=context(handle),
        matched=str(matched.TagName), original=str(original.TagName), source_tags=tags(source), target_tags=tags(targets),
        location=[float(getattr(location, key)) for key in ("x", "y", "z")], normal=[float(getattr(normal, key)) for key in ("x", "y", "z")],
        instigator=path(instigator), causer=path(causer), source=path(obj), material=path(material),
        effect_level=int(level), ability_level=int(ability_level), attach=path(attach), replicate_location=bool(replicate))
