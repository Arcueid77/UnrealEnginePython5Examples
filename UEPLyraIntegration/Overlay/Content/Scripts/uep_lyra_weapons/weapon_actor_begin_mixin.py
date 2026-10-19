"""Original owner-cast/factory/named delegate/current-team decisions."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .weapon_actor_fire_mixin import LyraWeaponActorFirePythonProfile as FirePython, LyraWeaponActorFireBlueprintFallbackProfile as FireBlueprint

CALLBACK = "OnTeamChanged_7B7D4F5F4F2DBFE78C0EBEB2388D25CB"
BIND = "UEPBindWeaponTeamObserver"


def evidence(actor):
    value=getattr(actor,"_uep_weapon_actor_begin",None)
    if value is None:
        value=dict(python_begins=0,fallback_begins=0,invalid_owner_noops=0,owner_writes=0,factories=0,null_factories=0,
            native_binds=0,activations=0,python_callbacks=0,fallback_callbacks=0,no_team_noops=0,stencil_calls=0,color_calls=0)
        actor._uep_weapon_actor_begin=value
    return value


def begin(actor):
    counts=evidence(actor);counts["python_begins"]+=1
    owner=actor.call_function("GetOwner")
    if not valid(owner) or not owner.is_a(ue.find_class("Pawn")):
        counts["invalid_owner_noops"]+=1;return
    actor.set_property("OwnerAsPawn",owner);counts["owner_writes"]+=1
    proxy=ue.find_class("AsyncAction_ObserveTeamColors").get_cdo().call_function("ObserveTeamColors",owner)
    if not valid(proxy):counts["null_factories"]+=1;return
    counts["factories"]+=1
    # A native (Actor,UFunction) weak delegate matches the original async node.
    # No Python closure, retained proxy, cancellation or deduplication is added.
    actor.call_function(BIND,proxy);counts["native_binds"]+=1
    proxy.call_function("Activate");counts["activations"]+=1


def changed(actor,assigned,team,display):
    counts=evidence(actor);counts["python_callbacks"]+=1
    if assigned:
        actor.call_function("UpdateCustomStencil",team);counts["stencil_calls"]+=1
        actor.call_function("UpdateTeamColors",display);counts["color_calls"]+=1
    else:counts["no_team_noops"]+=1


class LyraWeaponActorBeginPythonProfile:
    AddFakeProjectileData=FirePython.AddFakeProjectileData
    TriggerFireAudio=FirePython.TriggerFireAudio
    UpdateCustomStencil=FirePython.UpdateCustomStencil
    UpdateTeamColors=FirePython.UpdateTeamColors
    Fire=FirePython.Fire
    def ReceiveBeginPlay(self):begin(self)
    def ObservedTeamChanged(self,bTeamSet,TeamId,DisplayAsset):changed(self,bTeamSet,TeamId,DisplayAsset)
    ObservedTeamChanged.override=CALLBACK


class LyraWeaponActorBeginBlueprintFallbackProfile:
    AddFakeProjectileData=FireBlueprint.AddFakeProjectileData
    TriggerFireAudio=FireBlueprint.TriggerFireAudio
    UpdateCustomStencil=FireBlueprint.UpdateCustomStencil
    UpdateTeamColors=FireBlueprint.UpdateTeamColors
    Fire=FireBlueprint.Fire
    def ReceiveBeginPlay(self):
        evidence(self)["fallback_begins"]+=1
        return self.call_mixin_original("ReceiveBeginPlay")
    def ObservedTeamChanged(self,bTeamSet,TeamId,DisplayAsset):
        evidence(self)["fallback_callbacks"]+=1
        return self.call_mixin_original(CALLBACK,bTeamSet,TeamId,DisplayAsset)
    ObservedTeamChanged.override=CALLBACK
