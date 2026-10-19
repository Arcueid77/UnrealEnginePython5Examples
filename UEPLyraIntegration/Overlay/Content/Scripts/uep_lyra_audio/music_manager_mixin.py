"""Base music receiver/control/Tick policy; native BeginPlay listeners remain."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid

CLASS="/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C"
METHODS=("SetIsMenu","Receive Player Death","Receive Weapon Fire","Fire Stinger","ReceiveTick")


def lib(name):return ue.find_class(name).get_cdo()
def evidence(component):
    value=getattr(component,"_uep_music_manager",None)
    if value is None:value={method+"_"+profile:0 for method in METHODS for profile in ("python","fallback")};component._uep_music_manager=value
    return value
def locally_viewed(player):return valid(player) and player.is_a(ue.find_class("Pawn")) and bool(player.call_function("IsLocallyViewed"))
def music(component):return component.get_property("Music System")


def set_menu(component,value):
    sound=music(component)
    if valid(sound) and sound.call_function("IsPlaying"):sound.call_function("SetBoolParameter","bIsMenu",bool(value))
    # The source function does not write the component's bIsMenu variable.
def death(component,player):
    if locally_viewed(player):component.set_property("Alpha_Intensity",1.)
def fire(component,player,strength):
    if locally_viewed(player):component.set_property("Alpha_Intensity",lib("KismetMathLibrary").call_function("FClamp",float(component.get_property("Alpha_Intensity"))+float(strength),0.,1.))
def stinger(component,positive):
    component.set_property("Alpha_Intensity",0.)
    if not positive:return
    sound=music(component)
    if not valid(sound):
        lib("KismetSystemLibrary").call_function("PrintString",component,"mx system not valid",True,False,ue.FLinearColor(0.,.66,1.,1.),10.,"None")
    elif sound.call_function("IsPlaying"):sound.call_function("SetTriggerParameter","OnStingerPositive")
def tick(component,delta_seconds):
    sound=music(component)
    if not valid(sound):return
    if not sound.call_function("IsPlaying"):sound.call_function("Play",0.)
    statics=lib("GameplayStatics");math=lib("KismetMathLibrary")
    if not component.get_property("bIsMenu"):
        pawn=statics.call_function("GetPlayerPawn",component,0)
        if valid(pawn):
            look=math.call_function("Dot_VectorVector",pawn.call_function("GetActorForwardVector"),math.call_function("MakeVector",1.,0.,0.))
            sound.call_function("SetFloatParameter","LookDir",look)
            movement=math.call_function("MapRangeClamped",math.call_function("VSize",pawn.call_function("GetVelocity")),300.,600.,0.,1.)
            component.set_property("Alpha_Mvmt",movement)
    value=math.call_function("FInterpTo",float(component.get_property("Alpha_Intensity")),0.,statics.call_function("GetWorldDeltaSeconds",component),.05)
    component.set_property("Alpha_Intensity",value);sound.call_function("SetFloatParameter","Intensity",value)


class LyraMusicManagerPythonProfile:
    def SetIsMenu(self,InBool):evidence(self)["SetIsMenu_python"]+=1;set_menu(self,InBool)
    def Death(self,Player):evidence(self)["Receive Player Death_python"]+=1;death(self,Player)
    Death.override="Receive Player Death"
    def Fire(self,Player,Strength):evidence(self)["Receive Weapon Fire_python"]+=1;fire(self,Player,Strength)
    Fire.override="Receive Weapon Fire"
    def Stinger(self,Positive):evidence(self)["Fire Stinger_python"]+=1;stinger(self,Positive)
    Stinger.override="Fire Stinger"
    def ReceiveTick(self,DeltaSeconds):evidence(self)["ReceiveTick_python"]+=1;tick(self,DeltaSeconds)


def original(method):
    def call(self,*args):evidence(self)[method+"_fallback"]+=1;return self.call_mixin_original(method,*args)
    call.override=method;return call
class LyraMusicManagerBlueprintFallbackProfile:
    SetIsMenu=original("SetIsMenu")
    Death=original("Receive Player Death")
    Fire=original("Receive Weapon Fire")
    Stinger=original("Fire Stinger")
    ReceiveTick=original("ReceiveTick")
