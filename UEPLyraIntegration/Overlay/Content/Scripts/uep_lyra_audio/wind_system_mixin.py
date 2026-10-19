"""Native five-stage scheduler and array write; Python wind/trace/audio business."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import trace_outputs,break_hit

CLASS="/Game/Audio/Blueprints/B_WindSystem.B_WindSystem_C"
PLAYER_ENTRY="UEPWindNativePlayerArray"
SCHEDULE_ENTRY="UEPWindNativeSchedule"
AFTER_PLAYER="UEPWindAfterPlayerArrayGate"
STAGE="UEPWindStageGate"
DIRECTIONS=((0.,0.,1.),(0.,-1.,0.),(0.,1.,0.),(1.,0.,0.),(-1.,0.,0.))


def lib(name):return ue.find_class(name).get_cdo()
def evidence(actor):
    value=getattr(actor,"_uep_wind",None)
    if value is None:value=dict(tick_python=0,tick_fallback=0,after_python=0,after_fallback=0,stage_python=0,stage_fallback=0,queries=0,stages=[]);actor._uep_wind=value
    return value
def f32(value):return float(lib("KismetMathLibrary").call_function("Conv_DoubleToFloat",value))
def audio(actor):return actor.get_property("sfx_Amb_Wind_lp_meta")
def note_stage(stats,index):stats["stages"].append(int(index));stats["stages"][:]=stats["stages"][-320:]
def tick(actor,delta):
    evidence(actor)["tick_python"]+=1
    if not valid(audio(actor)):return actor.call_mixin_original("ReceiveTick",delta)
    pawn=lib("GameplayStatics").call_function("GetPlayerPawn",actor,0)
    if not valid(pawn):return
    actor.set_property("PawnLoc",pawn.call_function("K2_GetActorLocation"));actor.call_function(PLAYER_ENTRY)
def after_player(actor):
    evidence(actor)["after_python"]+=1
    if not valid(audio(actor)):return True
    pawn=lib("GameplayStatics").call_function("GetPlayerPawn",actor,0);math=lib("KismetMathLibrary")
    speed=f32(math.call_function("MapRangeClamped",math.call_function("VSize",pawn.call_function("GetVelocity")),600.,2500.,0.,1.))
    actor.set_property("Speed",speed);audio(actor).call_function("SetFloatParameter","PawnSpeed",speed)
    if actor.get_property("IsExterior"):actor.call_function(SCHEDULE_ENTRY)
    else:audio(actor).call_function("SetFloatParameter","Wind",speed)
    return False
def stage(actor,index):
    stats=evidence(actor);stats["stage_python"]+=1;note_stage(stats,index)
    if not valid(audio(actor)):return True
    math=lib("KismetMathLibrary");distance=float(actor.get_property("TraceDistance"));origin=actor.get_property("PawnLoc")
    if index==0:
        wind=f32(1.-float(actor.get_property("Hits"))*.2);actor.set_property("Wind",wind);audio(actor).call_function("SetFloatParameter","Wind",wind);actor.set_property("Hits",0)
    direction=math.call_function("MakeVector",*DIRECTIONS[index]);end=math.call_function("Add_VectorVector",origin,math.call_function("Multiply_VectorVector",direction,math.call_function("Conv_DoubleToVector",distance)))
    stats["queries"]+=1;raw=lib("KismetSystemLibrary").call_function("LineTraceSingle",WorldContextObject=actor,Start=origin,End=end,TraceChannel=0,bTraceComplex=False,
        ActorsToIgnore=list(actor.get_property("Player")),DrawDebugType=0,bIgnoreSelf=True,TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=5.)
    hit,result=trace_outputs("LineTraceSingle",raw)
    if hit:actor.set_property("Hits",int(actor.get_property("Hits"))+1)
    selected=f32(break_hit(result)["Distance"] if hit else distance)
    if index in (1,2):audio(actor).call_function("SetFloatParameter","Pan.L" if index==1 else "Pan.R",math.call_function("SafeDivide",selected,distance))
    return False


class LyraWindPythonProfile:
    def ReceiveTick(self,DeltaSeconds):return tick(self,DeltaSeconds)
    def AfterPlayer(self):return after_player(self)
    AfterPlayer.override=AFTER_PLAYER
    def Stage(self,Stage):return stage(self,int(Stage))
    Stage.override=STAGE
class LyraWindBlueprintFallbackProfile:
    def ReceiveTick(self,DeltaSeconds):evidence(self)["tick_fallback"]+=1;return self.call_mixin_original("ReceiveTick",DeltaSeconds)
    def AfterPlayer(self):evidence(self)["after_fallback"]+=1;return True
    AfterPlayer.override=AFTER_PLAYER
    def Stage(self,Stage):
        stats=evidence(self);stats["stage_fallback"]+=1;note_stage(stats,Stage);return True
    Stage.override=STAGE
