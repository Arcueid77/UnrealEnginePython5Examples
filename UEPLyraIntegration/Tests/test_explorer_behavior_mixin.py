"""Exact label/parent order and latest Controller after three readiness checkpoints."""
import importlib.util
from pathlib import Path
import sys,types,unittest
from unittest.mock import patch

inputs=types.ModuleType('uep_lyra_characters.explorer_input_mixin');inputs.CLASSES={'hero':'Hero','pawn':'Pawn'}
for kind in inputs.CLASSES:
    for profile,n in (('Python',25),('BlueprintFallback',20)):
        methods={key:lambda self,*a:None for key in ('ReceivePossessed','PythonExperienceReady','PythonInventoryWaitResume')};methods.update({'Existing'+str(i):lambda self:None for i in range(n-3)});setattr(inputs,'LyraExplorerInput'+kind.title()+profile+'Profile',type('Parent',(),methods))
initialization=types.ModuleType('uep_lyra_characters.explorer_init_mixin');initialization.valid=lambda o:o is not None;initialization.ue=types.SimpleNamespace(find_class=lambda n:n);initialization.possessed=lambda a,c:a.calls.append(('factory-possession',c));initialization.OriginalCallback=lambda k,c,fn:fn
waiting=types.ModuleType('uep_lyra_characters.inventory_wait_mixin');waiting.CLASSES=(None,'Inventory','Quickbar');waiting.REASONS=('missing_controller','missing_inventory','missing_quickbar');waiting.RESUME='Resume';waiting.defer=lambda a,s:a.calls.append(('defer',s));waiting.trace=lambda a,e,s:a.calls.append(('trace',e,s));waiting.evidence=lambda a:a.wait
ready=types.ModuleType('uep_lyra_characters.inventory_ready_mixin');ready.evidence=lambda a:a.ready
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_behavior_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_behavior_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_characters.explorer_input_mixin':inputs,'uep_lyra_characters.explorer_init_mixin':initialization,'uep_lyra_characters.inventory_wait_mixin':waiting,'uep_lyra_characters.inventory_ready_mixin':ready}):spec.loader.exec_module(policy)

class ExplorerBehaviorPolicyTests(unittest.TestCase):
    def actor(self,choice=False):
        props={'UseBhvTree':choice,policy.CONTROLLER:'latest-payload'};calls=[];controller=types.SimpleNamespace(call_function=lambda f,c:'valid-'+c)
        actor=types.SimpleNamespace(calls=calls,get_property=props.get,set_property=lambda n,v:props.__setitem__(n,v),call_function=lambda f,*a:calls.append((f,*a)) or (controller if f=='GetController' else None),call_mixin_original=lambda f,*a:calls.append(('original',f,*a)),wait=dict(grant_forwards=0,pending=[True]*3,resumes=0,stage_resumes=[0]*3),ready=dict(python_calls=0,immediate_grants=0,missing_controller=0,missing_inventory=0,missing_quickbar=0));return actor,props
    def test_false_label_then_parent(self):
        actor,_=self.actor();policy.construction(actor);self.assertEqual(actor.calls,[(policy.ST_TEXT,),(policy.PARENT,)])
    def test_true_label_then_parent(self):
        actor,_=self.actor(True);policy.construction(actor);self.assertEqual(actor.calls,[(policy.BT_TEXT,),(policy.PARENT,)])
    def test_behavior_false_is_noop(self):
        actor,_=self.actor();policy.behavior(actor,None);self.assertEqual(actor.calls,[])
    def test_behavior_true_calls_exact_native_ordered_backend(self):
        actor,_=self.actor(True);controller=types.SimpleNamespace(get_path_name=lambda:'input-controller');policy.behavior(actor,controller);self.assertEqual(actor.calls,[(policy.BEHAVIOR,controller)])
    def test_possession_stores_newest_payload_before_factory(self):
        actor,props=self.actor();policy.possessed(actor,'new-controller');self.assertEqual(props[policy.CONTROLLER],'new-controller');self.assertEqual(actor.calls,[('factory-possession','new-controller')])
    def test_ready_grants_then_uses_event_controller_payload(self):
        actor,_=self.actor();policy.advance(actor,0);names=[c[0] for c in actor.calls];self.assertLess(names.index('AddInitialInventory'),names.index('UseBehaviorTree'));self.assertEqual(next(c for c in actor.calls if c[0]=='UseBehaviorTree'),('UseBehaviorTree','latest-payload'))
    def test_missing_checkpoint_defers_without_grant_or_behavior(self):
        actor,_=self.actor();actor.call_function=lambda f,*a:actor.calls.append((f,*a));self.assertEqual(policy.advance(actor,0),'missing_controller');self.assertFalse(any(c[0] in ('AddInitialInventory','UseBehaviorTree') for c in actor.calls))
    def test_resume_rechecks_from_native_linkage(self):
        actor,_=self.actor();policy.resume(actor,2);self.assertEqual(actor.wait['stage_resumes'],[0,0,1]);self.assertEqual(actor.calls[-1],('UseBehaviorTree','latest-payload'))
    def test_invalid_resume_linkage_rejected(self):
        actor,_=self.actor()
        with self.assertRaises(ValueError):policy.resume(actor,3)
    def test_fallback_uses_original_functions(self):
        actor,_=self.actor();policy.construction_fallback(actor);policy.behavior_fallback(actor,None);self.assertEqual(actor.calls,[('original','UserConstructionScript'),('original','UseBehaviorTree',None)])
    def test_per_character_complete_method_families(self):
        for kind,expected in (('hero',(25,20)),('pawn',(27,22))):
            for profile,n in zip(('Python','BlueprintFallback'),expected):self.assertEqual(sum(callable(f) for name,f in vars(getattr(policy,'LyraExplorerBehavior'+kind.title()+profile+'Profile')).items() if not name.startswith('__')),n)
