"""Arena grid decisions with native RNG/math/trace and original spawn-node backend."""
import unreal_engine as ue
from unreal_engine.enums import ETraceTypeQuery,EDrawDebugTrace
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid
CLASS='/TopDownArena/Game/MapsGenerator/B_LevelGeneration.B_LevelGeneration_C'
BLOCK='/TopDownArena/Game/Environment/B_DestructableBlock.B_DestructableBlock_C'
PICKUP='/TopDownArena/Game/Pickups/B_TopDownArena_Pickup.B_TopDownArena_Pickup_C'
SPAWN='UEPArenaLevelNativeSpawnBlock'
def lib(n):return ue.find_class(n).get_cdo()
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def actors(a,cls):return native_outputs('GameplayStatics','GetAllActorsOfClass',lib('GameplayStatics').call_function('GetAllActorsOfClass',a,cls))['OutActors']
def flat(v):return lib('KismetMathLibrary').call_function('Multiply_VectorVector',v,ue.FVector(1.,1.,0.))
def evidence(a):
    value=getattr(a,'_uep_arena_level',None)
    if value is None:
        value={p+k:0 for p in ('python_','fallback_') for k in ('generate','clear','blocking','distance')};value.update(random_draws=0,cells=0,traces=0,spawns=0,destroyed=0);a._uep_arena_level=value
    return value
def clear(a):
    value=evidence(a)
    for actor in actors(a,ue.load_class(BLOCK)):
        actor.call_function('K2_DestroyActor');value['destroyed']+=1
class LyraArenaLevelPythonProfile:
    def ClearWalls(self):evidence(self)['python_clear']+=1;clear(self)
    def BlockingPlayerSpawn(self):
        evidence(self)['python_blocking']+=1;areas=list(self.get_property('BlockingArea'))
        for cls in (ue.find_class('PlayerStart'),ue.load_class(PICKUP)):
            for actor in actors(self,cls):areas.append(flat(actor.call_function('K2_GetActorLocation')))
        self.set_property('BlockingArea',areas)
    def DistanceBlocking(self,A):
        evidence(self)['python_distance']+=1;math=lib('KismetMathLibrary');candidate=flat(A);radius=math.call_function('Multiply_DoubleDouble',self.get_property('GridSize'),.5)
        # IsBlocking is a function-local BP variable, initialized false each call.
        blocked=False
        for point in self.get_property('BlockingArea'):
            distance=math.call_function('Vector_Distance',point,candidate)
            if not math.call_function('Greater_DoubleDouble',distance,radius):blocked=True;break
        return {'CanSpawn':not blocked}
    DistanceBlocking.uep_named_outputs=True
    def GenerateLevel(self):
        value=evidence(self);value['python_generate']+=1;clear(self);self.call_function('BlockingPlayerSpawn');math=lib('KismetMathLibrary');width=int(self.get_property('MapWidth'));height=int(self.get_property('MapHeight'));grid=self.get_property('GridSize');origin=self.call_function('K2_GetActorLocation');cx=math.call_function('Divide_DoubleDouble',math.call_function('Multiply_DoubleDouble',math.call_function('Multiply_DoubleDouble',width,grid),-1.),2.);cy=math.call_function('Divide_DoubleDouble',math.call_function('Multiply_DoubleDouble',math.call_function('Multiply_DoubleDouble',grid,height),-1.),2.);center=ue.FVector(cx,cy,0.)
        for y in range(height+1):
            for x in range(width+1):
                value['cells']+=1;draw=math.call_function('RandomIntegerInRange',0,100);value['random_draws']+=1
                if not math.call_function('Greater_IntInt',self.get_property('WallPercentage'),draw):continue
                offset=ue.FVector(math.call_function('Multiply_DoubleDouble',x,100.),math.call_function('Multiply_DoubleDouble',y,100.),50.);position=math.call_function('Add_VectorVector',math.call_function('Add_VectorVector',origin,offset),center)
                if not bool(one(self.call_function('DistanceBlocking',position))):continue
                start=math.call_function('Add_VectorVector',position,ue.FVector(0.,0.,100.));result=lib('KismetSystemLibrary').call_function('LineTraceSingle',WorldContextObject=self,Start=start,End=position,TraceChannel=ETraceTypeQuery.TraceTypeQuery1,bTraceComplex=False,ActorsToIgnore=[],DrawDebugType=getattr(EDrawDebugTrace,'None'),bIgnoreSelf=True,TraceColor=ue.FLinearColor(1.,0.,0.,1.),TraceHitColor=ue.FLinearColor(0.,1.,0.,1.),DrawTime=5.);value['traces']+=1
                hit=native_outputs('KismetSystemLibrary','LineTraceSingle',result)['ReturnValue']
                if not hit:self.call_function(SPAWN,position);value['spawns']+=1
class LyraArenaLevelBlueprintFallbackProfile:
    def ClearWalls(self):evidence(self)['fallback_clear']+=1;self.call_mixin_original('ClearWalls')
    def BlockingPlayerSpawn(self):evidence(self)['fallback_blocking']+=1;self.call_mixin_original('BlockingPlayerSpawn')
    def DistanceBlocking(self,A):evidence(self)['fallback_distance']+=1;return {'CanSpawn':one(self.call_mixin_original('DistanceBlocking',A))}
    DistanceBlocking.uep_named_outputs=True
    def GenerateLevel(self):evidence(self)['fallback_generate']+=1;self.call_mixin_original('GenerateLevel')
