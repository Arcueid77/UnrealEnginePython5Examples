"""Actual map plus owned native editor-function calls, obstacles and spawned blocks."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from .effect_pad_mixin import valid
from . import arena_level_mixin as policy
from .arena_level_contract import validate
PROBE='/Game/UEPValidation/BP_ArenaLevelProbe.BP_ArenaLevelProbe_C'
def arg(n):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+n+'='))
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def xyz(a):return vec(a.call_function('K2_GetActorLocation'))
class Validation:
    def __init__(self,result):
        self.path=Path(result);self.mode=arg('UEPArenaLevelMode');self.started=time.monotonic();self.finished=False;self.roots=[];self.actors=[];self.selector=None;self.report=dict(status='running',error=None,mode=self.mode,distance_cases=[],generation_cases=[])
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','global_rng_replaced','native_trace_replaced','actor_assets_saved_by_runtime'):self.report[k]=False
        self.cls=ue.load_class(policy.CLASS);self.probe_cls=ue.load_class(PROBE);self.block_cls=ue.load_class(policy.BLOCK);self.pickup_cls=ue.load_class(policy.PICKUP)
        for cls in (self.cls,self.probe_cls,self.block_cls,self.pickup_cls):
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
        self.probe=self.probe_cls.get_cdo()
        if self.mode!='Baseline':self.selector=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.mode);ue.register_declared_mixin(self.cls)
    def write(self):atomic_write(self.path,self.report)
    def blocks(self):return policy.actors(self.generator,self.block_cls)
    def setup(self,world):
        self.world=world;self.generator=world.actor_spawn(self.cls,ue.FVector(400000.,400000.,3000.));self.actors.append(self.generator)
        cases=[([],ue.FVector(),100),([ue.FVector()],ue.FVector(49.99,0.,500.),100),([ue.FVector()],ue.FVector(50.,0.,100.),100),([ue.FVector()],ue.FVector(50.001,0.,100.),100),([ue.FVector()],ue.FVector(),100),([ue.FVector()],ue.FVector(100.,0.,0.),100),([ue.FVector(0.,0.,100.)],ue.FVector(),100),([ue.FVector()],ue.FVector(),-100)]
        for area,point,size in cases:
            self.generator.set_property('GridSize',size);self.generator.set_property('BlockingArea',area);result=bool(policy.one(self.probe.call_function('DistanceBlocking',self.generator,point)));self.report['distance_cases'].append(dict(point=vec(point),grid_size=size,allowed=result))
        self.generator.set_property('GridSize',100);self.generator.set_property('BlockingArea',[ue.FVector(999.,888.,777.)]);self.start=world.actor_spawn(ue.find_class('PlayerStart'),ue.FVector(420000.,400000.,5000.));self.actors.append(self.start);self.pickup=world.actor_spawn(self.pickup_cls,ue.FVector(430000.,400000.,5000.));self.actors.append(self.pickup);existing=[vec(v) for v in self.generator.get_property('BlockingArea')];extra=[vec(policy.flat(a.call_function('K2_GetActorLocation'))) for cls in (ue.find_class('PlayerStart'),self.pickup_cls) for a in policy.actors(self.generator,cls)];self.probe.call_function('BlockingPlayerSpawn',self.generator);first=[vec(v) for v in self.generator.get_property('BlockingArea')];self.probe.call_function('BlockingPlayerSpawn',self.generator);second=[vec(v) for v in self.generator.get_property('BlockingArea')];self.report['blocking_append']=dict(first_matches_native_order=first==existing+extra,second_duplicates_preserved=second==existing+extra+extra,all_z_zero=all(v[2]==0. for v in first[len(existing):]))
        self.retained_blocks=len(second);self.plan=[('inclusive-full',2,2,100,101,False),('trace-obstacle',2,2,100,101,True),('grid-size-not-spacing',2,1,200,101,False),('zero-percent',2,2,100,0,False),('negative-width',-1,2,100,101,False),('zero-size',0,0,100,101,False),('native-default-percent',2,2,100,50,False)];self.index=0;self.obstacle=None
    def generate(self):
        name,width,height,grid,percentage,obstacle=self.plan[self.index]
        if valid(self.obstacle):self.obstacle.actor_destroy();self.obstacle=None
        if obstacle:
            self.obstacle=self.world.actor_spawn(ue.find_class('StaticMeshActor'),ue.FVector(400000.,400000.,3100.));self.actors.append(self.obstacle);mesh=self.obstacle.get_component_by_type(ue.find_class('StaticMeshComponent'));mesh.call_function('SetMobility',2);mesh.call_function('SetStaticMesh',ue.load_object(ue.find_class('StaticMesh'),'/Engine/BasicShapes/Cube.Cube'));mesh.call_function('SetCollisionProfileName','BlockAll',True)
        previous=self.blocks();self.generator.set_property('MapWidth',width);self.generator.set_property('MapHeight',height);self.generator.set_property('GridSize',grid);self.generator.set_property('WallPercentage',percentage);self.probe.call_function('GenerateLevel',self.generator);blocks=self.blocks();positions=sorted(xyz(a) for a in blocks);expected=[[400000.+x*100.-width*grid/2.,400000.+y*100.-height*grid/2.,3050.] for y in range(height+1) for x in range(width+1)];source_expected=sorted(expected);allowed=[v for v in source_expected if not (obstacle and v==[400000.,400000.,3050.])]
        self.report['generation_cases'].append(dict(name=name,positions=positions,grid_size=grid,spacing=100.,only_original_block_class=all(a.is_a(self.block_cls) for a in blocks),locations_match_expected_grid=all(v in allowed for v in positions),previous_world_blocks_removed=all(not valid(a) or a.call_function('IsActorBeingDestroyed') for a in previous),obstacle_cell_absent=[400000.,400000.,3050.] not in positions));self.index+=1
        if self.index==len(self.plan):
            self.report['blocking_survives_regeneration']=len(self.generator.get_property('BlockingArea'))>=self.retained_blocks;self.probe.call_function('ClearWalls',self.generator);self.report['clear_walls_empty']=not self.blocks();self.report['counts']=copy.deepcopy(policy.evidence(self.generator));self.finish()
    def cleanup(self):
        if hasattr(self,'generator') and valid(self.generator):self.probe.call_function('ClearWalls',self.generator)
        for a in reversed(self.actors):
            if valid(a):a.actor_destroy()
        if self.selector is not None:self.cls.get_cdo().set_property('PythonMixinProfile',self.selector)
        self.report['selector_restored']=self.selector is None or self.cls.get_cdo().get_property('PythonMixinProfile')==self.selector
        for cls in reversed(self.roots):cls.remove_from_root()
        self.report['owned_roots_removed']=all(not cls.is_rooted() for cls in self.roots);self.report['cleanup_complete']=self.report['selector_restored'] and self.report['owned_roots_removed']
    def tick(self,delta):
        if self.finished:return False
        try:
            if time.monotonic()-self.started>150.:raise RuntimeError('Arena grid native timeout')
            if not hasattr(self,'generator'):
                for world in ue.all_worlds():
                    if world.get_world_type() in (1,3) and 'TopDown' in world.get_name() and valid(policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)):self.setup(world);break
            else:self.generate()
            self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ARENA_LEVEL_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_LEVEL_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaLevelResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
