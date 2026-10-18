"""Native Hit event policy; native team/timer/RPC/audio envelopes retained."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .grenade_begin_mixin import LyraGrenadeBeginPythonProfile as BeginPython,LyraGrenadeBeginBlueprintFallbackProfile as BeginBlueprint

SOUND="/Game/Audio/MetaSounds/sfx_Weapon_GrenadeImpact_nl_meta.sfx_Weapon_GrenadeImpact_nl_meta"
ATTENUATION="/Game/Audio/AttenuationPresets/ATT_Projectile.ATT_Projectile"


def evidence(actor):
    row=getattr(actor,"_uep_grenade_hit",None)
    if row is None:
        row=dict(python_hits=0,fallback_hits=0,team_queries=0,invalid_team_subsystem_defaults=0,different_team_hits=0,
            other_team_hits=0,native_timer_clears=0,handle_writes=0,native_detonate_requests=0,native_sound_requests=0)
        actor._uep_grenade_hit=row
    return row


def hit(actor,other,location):
    counts=evidence(actor);counts["python_hits"]+=1
    # Cache only the native world/primitive libraries before Detonate: the
    # original RPC can synchronously destroy this Actor in no-render cases.
    # Its native WorldContext resolves to the same world as this cached value.
    world=actor.get_world();system=ue.find_class("KismetSystemLibrary").get_cdo();statics=ue.find_class("GameplayStatics").get_cdo()
    teams=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",world,ue.find_class("LyraTeamSubsystem"))
    if valid(teams):
        result=teams.call_function("CompareTeams",other,actor.get_property("Instigator"));counts["team_queries"]+=1
        if not isinstance(result,tuple) or len(result)!=3: raise RuntimeError("native CompareTeams output ABI differs")
        comparison=int(result[0])
    else: comparison=0;counts["invalid_team_subsystem_defaults"]+=1
    if comparison==1: # Original ELyraTeamComparison.DifferentTeams exec.
        counts["different_team_hits"]+=1
        output=system.call_function("K2_ClearAndInvalidateTimerHandle",world,actor.get_property("Timer"));counts["native_timer_clears"]+=1
        if not isinstance(output,tuple) or len(output)!=1: raise RuntimeError("native clear/invalidate Timer handle output ABI differs")
        actor.set_property("Timer",output[0]);counts["handle_writes"]+=1
        counts["native_detonate_requests"]+=1;actor.call_function("Detonate")
    else: counts["other_team_hits"]+=1
    counts["native_sound_requests"]+=1
    statics.call_function("SpawnSoundAtLocation",WorldContextObject=world,Sound=ue.load_object(ue.find_class("SoundBase"),SOUND),Location=location,
        Rotation=ue.FRotator(),VolumeMultiplier=1.,PitchMultiplier=1.,StartTime=0.,
        AttenuationSettings=ue.load_object(ue.find_class("SoundAttenuation"),ATTENUATION),ConcurrencySettings=None,bAutoDestroy=True)


class LyraGrenadeHitPythonProfile:
    SetupVFX=BeginPython.SetupVFX
    PostLaunchCleanup=BeginPython.PostLaunchCleanup
    TeleportGrenade=BeginPython.TeleportGrenade
    DestroyGrenade=BeginPython.DestroyGrenade
    ReceiveBeginPlay=BeginPython.ReceiveBeginPlay
    def ReceiveHit(self,MyComp,Other,OtherComp,bSelfMoved,HitLocation,HitNormal,NormalImpulse,Hit): hit(self,Other,HitLocation)


class LyraGrenadeHitBlueprintFallbackProfile:
    SetupVFX=BeginBlueprint.SetupVFX
    PostLaunchCleanup=BeginBlueprint.PostLaunchCleanup
    TeleportGrenade=BeginBlueprint.TeleportGrenade
    DestroyGrenade=BeginBlueprint.DestroyGrenade
    ReceiveBeginPlay=BeginBlueprint.ReceiveBeginPlay
    def ReceiveHit(self,MyComp,Other,OtherComp,bSelfMoved,HitLocation,HitNormal,NormalImpulse,Hit):
        evidence(self)["fallback_hits"]+=1
        return self.call_mixin_original("ReceiveHit",MyComp,Other,OtherComp,bSelfMoved,HitLocation,HitNormal,NormalImpulse,Hit)
