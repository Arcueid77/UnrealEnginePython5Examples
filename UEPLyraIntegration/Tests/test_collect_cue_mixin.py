"""Source colliding/noncolliding bounds, socket branch and absolute scale order."""
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
def vec(x=0.,y=0.,z=0.):return types.SimpleNamespace(x=float(x),y=float(y),z=float(z))
life=types.ModuleType('uep_lyra_weapons.collect_cue_lifecycle_mixin');life.CLASS='Cue';life.GATE='Schedule'
for name in ('Python','BlueprintFallback'):setattr(life,'LyraCollectCueLifecycle'+name+'Profile',type('Parent',(),{k:lambda self:None for k in ('OnExecute','Schedule','Deadline')}))
helper=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin')
def math(name,*args):
    if name=='EqualEqual_NameName':return str(args[0]) in ('','None')
    if name=='Divide_DoubleDouble':return args[0]/args[1] if args[1] else 0.
    if name=='Lerp':return args[0]+(args[1]-args[0])*args[2]
    raise AssertionError(name)
helper.lib=lambda name:types.SimpleNamespace(call_function=math);world=types.ModuleType('uep_lyra_world.effect_pad_mixin');world.valid=lambda value:value is not None
spec=importlib.util.spec_from_file_location('uep_lyra_weapons._collect_cue_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/collect_cue_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':types.SimpleNamespace(find_class=lambda n:n,FVector=vec),'uep_lyra_weapons.hero_burst_cue_mixin':helper,'uep_lyra_weapons.collect_cue_lifecycle_mixin':life,'uep_lyra_world.effect_pad_mixin':world}):spec.loader.exec_module(policy)
def fixture(socket='None',valid_pawn=True):
    calls=[];props={'In Socket Name':socket,'SuckUpAnimTime':.5};root=types.SimpleNamespace(call_function=lambda name,*args,**kwargs:calls.append(('root',name,args,kwargs)));mesh=types.SimpleNamespace(call_function=lambda name,*args:vec(4,5,6));timeline=types.SimpleNamespace(call_function=lambda name,*args:calls.append(('timeline',name,*args)))
    def pawn_call(name,*args,**kwargs):
        calls.append(('pawn',name,args,kwargs));return (vec(10,20,30),vec(3,4,50)) if name=='GetActorBounds' else vec(1,2,3) if name=='K2_GetActorLocation' else mesh
    pawn=types.SimpleNamespace(is_a=lambda cls:valid_pawn,call_function=pawn_call)
    def target_call(name,*args,**kwargs):calls.append(('target',name,args,kwargs));return (vec(),vec(1,2,10)) if name=='GetActorBounds' else vec(100,200,300)
    target=types.SimpleNamespace(call_function=target_call,get_property=lambda name:root);spline=types.SimpleNamespace(call_function=lambda name,*args:calls.append(('spline',name,*args)) or (100. if name=='GetSplineLength' else vec(50,60,70) if name=='GetLocationAtDistanceAlongSpline' else None));props['ItemSuckUp']=timeline;props['ActorToPickup']=target;props['Spline_PickedUpAnim']=spline
    a=types.SimpleNamespace(get_property=props.get,set_property=lambda n,v:props.__setitem__(n,v),call_function=lambda name,*args:calls.append(('cue',name,*args)) or (spline if name==policy.CREATE else None),call_mixin_original=lambda name,*args:calls.append(('original',name,*args)));data=types.SimpleNamespace(Instigator=pawn,EffectCauser=target);return a,data,calls,props
class CollectCuePolicyTests(unittest.TestCase):
    def test_source_midpoint_bounds_and_no_socket_endpoint(self):
        a,data,calls,_=fixture();policy.play(a,'unused',data);self.assertEqual(policy.evidence(a)['points'],[[100.,200.,300.],[10.,20.,86.],[1.,2.,3.]]);self.assertTrue(any(c[0:2]==('pawn','GetActorBounds') and c[3]['bOnlyCollidingComponents'] for c in calls));self.assertTrue(any(c[0:2]==('target','GetActorBounds') and not c[3]['bOnlyCollidingComponents'] for c in calls));self.assertEqual(calls[-2:], [('timeline','SetPlayRate',2.),('cue',policy.START)])
    def test_socket_endpoint_does_not_change_attachment_socket(self):
        a,data,calls,_=fixture('pelvis');policy.play(a,None,data);self.assertEqual(policy.evidence(a)['points'][-1],[4.,5.,6.]);attach=next(c for c in calls if c[0:2]==('spline','K2_AttachToComponent'));self.assertEqual(attach[3:],('None',1,1,1,True))
    def test_invalid_pawn_prepares_target_then_clears_self_lifespan_and_prints(self):
        a,data,calls,_=fixture(valid_pawn=False);policy.play(a,None,data);self.assertEqual([c[1] for c in calls], [policy.TARGET,life.GATE,'SetLifeSpan',policy.ERROR]);self.assertEqual(calls[1][-1],0.)
    def test_native_distance_move_then_absolute_uniform_scale(self):
        a,_,calls,_=fixture();self.assertFalse(policy.update(a,.5,.25));move,scale=[c for c in calls if c[0]=='root'];self.assertEqual(move[1],'K2_SetWorldLocation');self.assertEqual(scale[1],'SetWorldScale3D');self.assertEqual([scale[2][0].x,scale[2][0].y,scale[2][0].z],[.25]*3);self.assertTrue(any(c[0:2]==('spline','GetLocationAtDistanceAlongSpline') and c[2]==50. and c[3]==1 for c in calls))
    def test_finish_hides_before_original_scheduled_lifespan(self):
        a,_,calls,_=fixture();self.assertFalse(policy.finish(a));self.assertEqual(calls,[('cue','SetActorHiddenInGame',True),('cue',life.GATE,3.),('cue','SetLifeSpan',3.)])
    def test_missing_spline_keeps_original_native_diagnostic_path(self):
        a,_,_,props=fixture();props['Spline_PickedUpAnim']=None;self.assertTrue(policy.update(a,.1,.2))
    def test_expired_property_wrapper_keeps_original_native_diagnostic_path(self):
        a,_,_,_=fixture()
        def expired(name):raise RuntimeError('PyUObject is in invalid state')
        a.get_property=expired;self.assertTrue(policy.update(a,.1,.2))
    def test_six_own_methods_preserve_lifecycle_family(self):
        for name in ('Python','BlueprintFallback'):self.assertEqual(sum(callable(v) for k,v in vars(getattr(policy,'LyraCollectCue'+name+'Profile')).items() if not k.startswith('__')),6)
