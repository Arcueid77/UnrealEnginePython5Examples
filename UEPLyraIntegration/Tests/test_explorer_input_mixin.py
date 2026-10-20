"""Compiler-owned receiver names resolve per actor; fallback retains native frames."""
import importlib.util
from pathlib import Path
import sys,types,unittest
from unittest.mock import patch
native=types.ModuleType('unreal_engine');helpers=types.ModuleType('uep_lyra_characters.explorer_helpers_mixin');helpers.CLASSES={'hero':'Hero','pawn':'Pawn'};beginning=types.ModuleType('uep_lyra_characters.explorer_beginplay_mixin')
for kind in helpers.CLASSES:
    for profile in ('Python','BlueprintFallback'):setattr(beginning,'LyraExplorerBeginPlay'+kind.title()+profile+'Profile',type('Parent',(),{'Existing'+str(i):lambda self:None for i in range(20)}))
contract=types.ModuleType('uep_lyra_characters.enhanced_input_contract');contract.ACTIONS={k:(n,'old',i,t) for k,n,i,t in (('slot-0','IA_QuickSlot1',0,'select'),('slot-1','IA_QuickSlot2',1,'select'),('slot-2','IA_QuickSlot3',2,'select'),('back','IA_QuickSlot_CycleBackward',0,'back'),('forward','IA_QuickSlot_CycleForward',0,'forward'))}
shared=types.ModuleType('uep_lyra_characters.enhanced_input_mixin');shared.dispatch=lambda actor,action:actor.append(action)
classes={name:object() for name in helpers.CLASSES.values()};native.find_class=lambda name:classes.get(name,name)
spec=importlib.util.spec_from_file_location('uep_lyra_characters._explorer_input_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_characters/explorer_input_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'uep_lyra_characters.explorer_helpers_mixin':helpers,'uep_lyra_characters.explorer_beginplay_mixin':beginning,'uep_lyra_characters.enhanced_input_contract':contract,'uep_lyra_characters.enhanced_input_mixin':shared}):spec.loader.exec_module(policy)

def binding(cls,suffix,trigger=1):
    return types.SimpleNamespace(get_outer=lambda:cls,get_property=lambda n:[types.SimpleNamespace(InputAction=types.SimpleNamespace(get_path_name=lambda asset=asset:'/ShooterCore/Input/Actions/'+asset+'.'+asset),TriggerEvent=trigger,FunctionNameToBind='Receiver_'+key+'_'+suffix) for key,(asset,_,_,_) in contract.ACTIONS.items()])
class ExplorerInputPolicyTests(unittest.TestCase):
    def setUp(self):policy.ue=native;native.find_class=lambda name:classes.get(name,name);native.tobject_iterator=lambda cls:[binding(classes['Hero'],'H'),binding(classes['Pawn'],'P')]
    def test_each_actor_uses_its_own_native_binding_names(self):
        self.assertEqual(policy.bindings(classes['Hero'])['slot-0'],'Receiver_slot-0_H');self.assertEqual(policy.bindings(classes['Pawn'])['slot-0'],'Receiver_slot-0_P')
    def test_compiler_suffix_is_resolved_fresh_each_registration(self):
        receiver=policy.receiver('hero','back');self.assertEqual(receiver.override,'Receiver_back_H');native.tobject_iterator=lambda cls:[binding(classes['Hero'],'New')];self.assertEqual(receiver.override,'Receiver_back_New')
    def test_duplicate_or_non_triggered_bindings_rejected(self):
        for values in ([binding(classes['Hero'],'a'),binding(classes['Hero'],'b')],[binding(classes['Hero'],'a',2)]):
            native.tobject_iterator=lambda cls:values
            with self.assertRaises(RuntimeError):policy.bindings(classes['Hero'])
    def test_missing_actor_binding_family_rejected(self):
        native.tobject_iterator=lambda cls:[]
        with self.assertRaises(RuntimeError):policy.bindings(classes['Hero'])
    def test_input_body_dispatches_only_original_action_policy(self):
        actor=[];policy.receiver('hero','forward')(actor,False,99.,88.,None);self.assertEqual(actor,['forward'])
    def test_fallback_omits_all_five_input_overrides(self):
        for kind in helpers.CLASSES:
            py=getattr(policy,'LyraExplorerInput'+kind.title()+'PythonProfile');bp=getattr(policy,'LyraExplorerInput'+kind.title()+'BlueprintFallbackProfile');self.assertEqual(sum(callable(f) for n,f in vars(py).items() if not n.startswith('__')),25);self.assertEqual(sum(callable(f) for n,f in vars(bp).items() if not n.startswith('__')),20)
    def test_prior_twenty_methods_are_unchanged(self):
        for name,fn in vars(beginning.LyraExplorerBeginPlayHeroPythonProfile).items():
            if not name.startswith('__'):self.assertIs(vars(policy.LyraExplorerInputHeroPythonProfile)[name],fn)
