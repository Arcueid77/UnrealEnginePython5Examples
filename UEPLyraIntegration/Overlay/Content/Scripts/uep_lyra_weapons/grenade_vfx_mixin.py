"""Retained B_Grenade helper decisions; Niagara/team systems remain native."""
import unreal_engine as ue
from unreal_engine.enums import EAttachLocation,ENCPoolMethod
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/ShooterCore/Weapon/Grenade/B_Grenade.B_Grenade_C"
TRAIL="/Game/Effects/Particles/Explosion/NS_Grenade_Trail.NS_Grenade_Trail"
METHOD="Setup VFX"


def evidence(actor):
    row=getattr(actor,"_uep_grenade_vfx",None)
    if row is None:
        row=dict(python_calls=0,fallback_calls=0,native_spawns=0,invalid_spawn_noops=0,trail_writes=0,team_queries=0,
            missing_team_subsystem_defaults=0,red_choices=0,blue_choices=0,color_writes=0,parameter_writes=0,invalid_trail_noops=0,last=None)
        actor._uep_grenade_vfx=row
    return row
def note(actor,name): evidence(actor)[name]+=1


def setup(actor):
    note(actor,"python_calls")
    component=ue.find_class("NiagaraFunctionLibrary").get_cdo().call_function("SpawnSystemAttached",
        SystemTemplate=ue.load_object(ue.find_class("NiagaraSystem"),TRAIL),AttachToComponent=actor.get_property("Mesh"),AttachPointName="None",
        Location=ue.FVector(),Rotation=ue.FRotator(),LocationType=EAttachLocation.KeepRelativeOffset,bAutoDestroy=False,bAutoActivate=True,
        PoolingMethod=getattr(ENCPoolMethod,"None"),bPreCullCheck=True)
    note(actor,"native_spawns")
    if not valid(component): note(actor,"invalid_spawn_noops");return
    actor.set_property("NS_Trail",component);note(actor,"trail_writes")
    subsystem=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",actor,ue.find_class("LyraTeamSubsystem"))
    if valid(subsystem):
        result=subsystem.call_function("FindTeamFromActor",actor.get_property("Instigator"));note(actor,"team_queries")
        if not isinstance(result,tuple) or len(result)!=2 or type(result[0]) is not bool or type(result[1]) is not int:
            raise RuntimeError("native FindTeamFromActor out-parameter ABI differs")
        _,team=result # Original uses TeamId only,not bIsPartOfTeam.
    else:
        team=0;note(actor,"missing_team_subsystem_defaults") # Native VM invalid-context output default.
    red=team==1;color=ue.FLinearColor(*( (1.,.05,.01,1.) if red else (.01,.15,1.,1.) ))
    note(actor,"red_choices" if red else "blue_choices");actor.set_property("Team Color",color);note(actor,"color_writes")
    evidence(actor)["last"]=dict(team_id=team,red=red)
    trail=actor.get_property("NS_Trail") # Preserve the original validated variable get.
    if valid(trail): trail.call_function("SetVariableLinearColor","Team_Color",actor.get_property("Team Color"));note(actor,"parameter_writes")
    else: note(actor,"invalid_trail_noops")


class LyraGrenadeVFXPythonProfile:
    def SetupVFX(self): setup(self)
    SetupVFX.override=METHOD


class LyraGrenadeVFXBlueprintFallbackProfile:
    def SetupVFX(self):
        note(self,"fallback_calls");return self.call_mixin_original(METHOD)
    SetupVFX.override=METHOD
