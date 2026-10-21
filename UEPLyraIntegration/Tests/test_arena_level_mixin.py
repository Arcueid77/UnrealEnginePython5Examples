import importlib.util,sys,types,unittest,math
from pathlib import Path
from unittest.mock import patch
def load():
    unreal=types.ModuleType('unreal_engine');unreal.FVector=lambda x=0.,y=0.,z=0.:types.SimpleNamespace(x=x,y=y,z=z);unreal.FLinearColor=lambda *v:v;unreal.load_class=lambda p:p;unreal.find_class=lambda n:n;enums=types.ModuleType('unreal_engine.enums');enums.ETraceTypeQuery=types.SimpleNamespace(TraceTypeQuery1=0);enums.EDrawDebugTrace=types.SimpleNamespace(**{'None':0});native=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');native.native_outputs=lambda c,n,v:v;valid=types.ModuleType('uep_lyra_world.effect_pad_mixin');valid.valid=lambda o:o is not None
    spec=importlib.util.spec_from_file_location('uep_lyra_world.arena_level_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/arena_level_mixin.py');p=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':unreal,'unreal_engine.enums':enums,'uep_lyra_abilities.melee_trace_mixin':native,'uep_lyra_world.effect_pad_mixin':valid}):spec.loader.exec_module(p)
    return p
class ArenaLevelPolicyTests(unittest.TestCase):
    def test_distance_strict_boundary_and_function_local_reset(self):
        p=load();p.flat=lambda v:p.ue.FVector(v.x,v.y,0.)
        def call(n,a,b):
            if n=='Multiply_DoubleDouble':return a*b
            if n=='Vector_Distance':return math.dist((a.x,a.y,a.z),(b.x,b.y,b.z))
            if n=='Greater_DoubleDouble':return a>b
        p.lib=lambda n:types.SimpleNamespace(call_function=call);w=types.SimpleNamespace(get_property=lambda n:100 if n=='GridSize' else [p.ue.FVector()]);self.assertEqual(p.LyraArenaLevelPythonProfile.DistanceBlocking(w,p.ue.FVector(50,0,999)),{'CanSpawn':False});self.assertEqual(p.LyraArenaLevelPythonProfile.DistanceBlocking(w,p.ue.FVector(100,0,999)),{'CanSpawn':True})
    def test_only_candidate_z_is_flattened(self):
        p=load();p.flat=lambda v:p.ue.FVector(v.x,v.y,0.);p.lib=lambda n:types.SimpleNamespace(call_function=lambda name,a,b:a*b if name=='Multiply_DoubleDouble' else math.dist((a.x,a.y,a.z),(b.x,b.y,b.z)) if name=='Vector_Distance' else a>b);w=types.SimpleNamespace(get_property=lambda n:100 if n=='GridSize' else [p.ue.FVector(0,0,100)]);self.assertEqual(p.LyraArenaLevelPythonProfile.DistanceBlocking(w,p.ue.FVector()),{'CanSpawn':True})
    def test_blocking_appends_preserving_native_class_order_and_duplicates(self):
        p=load();calls=[];p.flat=lambda v:v;values=[object()];a,b=object(),object();p.actors=lambda w,cls:[types.SimpleNamespace(call_function=lambda n:a if cls=='PlayerStart' else b)];w=types.SimpleNamespace(get_property=lambda n:values,set_property=lambda n,v:calls.append(v));p.LyraArenaLevelPythonProfile.BlockingPlayerSpawn(w);self.assertEqual(calls,[[values[0],a,b]])
    def test_clear_destroys_every_world_block_without_area_filter(self):
        p=load();calls=[];p.actors=lambda *a:[types.SimpleNamespace(call_function=lambda name:calls.append(name)) for _ in range(3)];p.LyraArenaLevelPythonProfile.ClearWalls(types.SimpleNamespace());self.assertEqual(calls,['K2_DestroyActor']*3)
    def test_generate_inclusive_loop_and_one_native_random_draw_per_cell(self):
        p=load();calls=[];p.actors=lambda *a:[]
        def call(name,*a,**kw):
            calls.append((name,a))
            if name=='RandomIntegerInRange':return 100
            if name=='Greater_IntInt':return False
            if name=='Multiply_DoubleDouble':return a[0]*a[1]
            if name=='Divide_DoubleDouble':return a[0]/a[1]
        p.lib=lambda n:types.SimpleNamespace(call_function=call);values=dict(MapWidth=2,MapHeight=1,GridSize=200,WallPercentage=0);w=types.SimpleNamespace(get_property=lambda n:values[n],call_function=lambda n,*a:p.ue.FVector() if n=='K2_GetActorLocation' else None);p.LyraArenaLevelPythonProfile.GenerateLevel(w);self.assertEqual([a for n,a in calls if n=='RandomIntegerInRange'],[(0,100)]*6);self.assertEqual(p.evidence(w)['cells'],6)
    def test_named_bool_output_and_no_python_empty_events(self):
        p=load();self.assertTrue(p.LyraArenaLevelPythonProfile.DistanceBlocking.uep_named_outputs);self.assertEqual({n for n,v in vars(p.LyraArenaLevelPythonProfile).items() if callable(v)},{'GenerateLevel','ClearWalls','BlockingPlayerSpawn','DistanceBlocking'})
