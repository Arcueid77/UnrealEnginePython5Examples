"""Run the production spawn helper against null and valid native-result models."""
import ast,sys,types,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'Overlay/Content/Scripts'))
from uep_lyra_weapons.spawning_null_effect_contract import FALSE,validate

class Actor:
    def __init__(self):self.values=dict(TemplateToUse=object(),SpawnedEffectMap={},SpawnedEffects=[],SpawningDuration=.35,TeamColor=(1,0,0,1))
    def get_property(self,key):return self.values[key]
    def set_property(self,key,value):self.values[key]=value
    def call_mixin_original(self,*args):raise AssertionError('Unexpected BP fallthrough')
class Effect:
    def __init__(self):self.calls=[]
    def call_function(self,*args):self.calls.append(args)

def load_spawn(null):
    tree=ast.parse((BASE/'Overlay/Content/Scripts/uep_lyra_weapons/spawning_cue_mixin.py').read_text(encoding='utf-8-sig'))
    body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('spawn','mark','evidence')]
    calls=[];results=[]
    class Library:
        def __init__(self,name):self.name=name
        def call_function(self,name,*args,**kwargs):
            if self.name=='NiagaraFunctionLibrary':
                calls.append((name,kwargs));value=None if null else Effect();results.append(value);return value
            return (1,0,0)
    ns=dict(valid=lambda x:x is not None,components=lambda *a:('main','ignored','child'),mesh_target=lambda a:None,ignore_tag=lambda x:x=='ignored',lib=Library,
        ue=types.SimpleNamespace(FVector=lambda:(),FRotator=lambda:()),EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0),ENCPoolMethod=types.SimpleNamespace(**{'None':0}))
    exec(compile(ast.Module(body=body,type_ignores=[]),'production-spawn-helper','exec'),ns)
    return ns['spawn'],calls,results

def report():
    state=dict(array_count=2,map_count=2,array_all_null=True,map_all_null=True,expected_mesh_keys=True,ignored_mesh_absent=True)
    result=dict(status='passed',error=None,native_mode='Standalone',null_rhi=True,mixin_profile_method_counts=dict(BlueprintFallback=8,Python=8),cases=[])
    result.update(dict.fromkeys(FALSE,False))
    for key in ('owned_actors_destroyed','owned_effects_removed','owned_watchers_cancelled','original_health_unchanged','production_profiles_restored'):result[key]=True
    for profile in ('BlueprintFallback','Python'):result['cases'].append(dict(profile=profile,selected_spawn_entries=2,other_spawn_entries=0,initial=dict(state),repeat=dict(state),removal_cleared_caches=True,spawn_attempts=2,existing_meshes=2,diagnostic_fallbacks=0))
    return result

class SpawningSpawnResultTests(unittest.TestCase):
    def test_null_native_result_keeps_cache_and_does_not_retry(self):
        spawn,calls,results=load_spawn(True);actor=Actor();spawn(actor)
        self.assertEqual(actor.values['SpawnedEffects'],[None,None]);self.assertEqual(actor.values['SpawnedEffectMap'],dict(main=None,child=None))
        spawn(actor);self.assertEqual(len(calls),2);self.assertEqual(actor._uep_spawning_cue['existing_meshes'],2)
        self.assertEqual(actor._uep_spawning_cue['diagnostic_fallbacks'],0)
    def test_valid_native_results_keep_both_original_parameter_calls(self):
        spawn,calls,results=load_spawn(False);actor=Actor();spawn(actor)
        self.assertEqual(len(calls),2)
        for effect in results:self.assertEqual(effect.calls,[('SetVariableFloat','SpawnTImeLength',.35),('SetVariableVec3','BodyColor',(1,0,0))])
        self.assertEqual(actor.values['SpawnedEffects'],results)
    def test_native_null_contract_rejects_cache_retry_and_missing_cleanup(self):
        self.assertEqual(validate(report())['native_null_results'],4)
        for key,value in (('spawn_attempts',4),('existing_meshes',0),('diagnostic_fallbacks',1),('removal_cleared_caches',False)):
            r=report();r['cases'][1][key]=value
            with self.assertRaises(RuntimeError):validate(r)
    def test_injected_return_or_missing_declared_profile_is_not_native_proof(self):
        for key in FALSE:
            r=report();r[key]=True
            with self.assertRaises(RuntimeError):validate(r)
        r=report();r['mixin_profile_method_counts']['Python']=9
        with self.assertRaises(RuntimeError):validate(r)
