"""Forensic classification must not turn name matches/retries into a fix."""
import copy,importlib.util,unittest
from pathlib import Path
from uep_lyra_hud.startup import validation_module
from uep_lyra_abilities.melee_cue_observation import ExistingCueObservation
spec=importlib.util.spec_from_file_location('pawn_asc_capture',Path(__file__).resolve().parents[1]/'Tools/analyze_pawn_asc_takeovers.py')
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)

class PawnAscTakeoverAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.actor='/Map.World:PersistentLevel.Hero_2';self.state='/Map.World:PersistentLevel.PlayerState_3'
        self.row=dict(actor=self.actor,role=1,health=0,player_state=self.state,player_state_pawn=self.actor,health_set=None,extension_asc=None,actor_asc=None,
            player_state_asc=dict(health_attributes=[dict(health=100.)]),init_features=[dict(state='InitState.GameplayReady')])
        self.log='Setting up ASC [AbilitySystemComponent] on pawn [Hero_5] owner [PlayerState_3], existing [Hero_2]'
    def run_capture(self,row=None,log=None,extra=()):
        before=copy.deepcopy(self.row);before.update(health=100,health_set='native-set',extension_asc='native-asc',actor_asc={})
        events=[dict(file='healthy.json',kind='native-binding-change',elapsed=1.,data=before),dict(file='gap.json',kind='native-binding-change',elapsed=2.,data=row or self.row),*extra]
        return analysis.analyze('B0',events,self.log if log is None else log)
    def test_native_takeover_and_prior_healthy_binding_linked_locally(self):
        r=self.run_capture();g,=r['canonical_gameplayready_empty_binding_rows'];self.assertEqual(g['previous_component_health'],100)
        self.assertEqual(g['native_takeovers'][0]['native_log']['new'],'Hero_5');self.assertFalse(r['cause_or_fix_proven']);self.assertFalse(r['cross_peer_identity_claimed'])
    def test_uninitialized_noncanonical_or_actually_dead_actor_is_not_gap(self):
        for key,value in (('player_state_pawn','another'),('init_features',[]),('health_set','still-bound'),('player_state_asc',dict(health_attributes=[dict(health=0.)]))):
            row=copy.deepcopy(self.row);row[key]=value;self.assertEqual(self.run_capture(row)['canonical_gameplayready_empty_binding_rows'],[])
    def test_takeover_requires_same_local_player_state(self):
        r=self.run_capture(log=self.log.replace('PlayerState_3','PlayerState_8'));self.assertEqual(r['canonical_gameplayready_empty_binding_rows'][0]['native_takeovers'],[])
    def test_same_actor_or_initial_binding_is_not_takeover(self):
        for old in ('None','Hero_5'):
            self.assertEqual(self.run_capture(log=self.log.replace('existing [Hero_2]','existing ['+old+']'))['local_native_takeovers'],[])
    def test_replacement_destruction_keeps_the_captured_python_stack(self):
        event=dict(file='destroyed.json',kind='native-destroyed-before-end-play',elapsed=1.8,data=dict(actor='/Map.World:PersistentLevel.Hero_5',python_stack=['actual-stack']))
        r=self.run_capture(extra=[event]);self.assertEqual(r['canonical_gameplayready_empty_binding_rows'][0]['native_takeovers'][0]['lifecycle'][0]['python_stack'],['actual-stack'])
    def test_diagnostic_requires_explicit_native_result_and_ignores_commandlets(self):
        flag='-UEPMeleeReadinessDiagnostic';result='-UEPMeleeTraceNetworkResult=x'
        self.assertIsNone(validation_module([flag]));self.assertIsNone(validation_module(['-run=Py',flag,result]));self.assertIsNone(validation_module([]))
        self.assertEqual(validation_module([flag,result]),'uep_lyra_abilities.melee_readiness_diagnostic_validation')
    def test_current_cue_handlers_return_once_and_restore_exact_profile_classes(self):
        calls=[];result=object()
        class Python:
            def OnBurst(self,target,parameters,spawn):calls.append(('Python',target,parameters,spawn));return result
        class Original:
            def OnBurst(self,target,parameters,spawn):calls.append(('Original',target,parameters,spawn));return result
        cls=object();binding=dict(target_class=cls,profiles={name:dict(python_class=base) for name,base in (('Python',Python),('BlueprintFallback',Original))})
        class API:
            def register_mixin_profile(self,cls,name,base):binding['profiles'][name]['python_class']=base
            def get_registered_mixins(self):return [binding]
        observed=[];watch=ExistingCueObservation(API(),cls,binding,lambda t,p:observed.append((t,p)))
        for name in ('Python','BlueprintFallback'):
            actor=binding['profiles'][name]['python_class']();self.assertIs(actor.OnBurst('target','parameters','spawn'),result)
        self.assertEqual([c[0] for c in calls],['Python','Original']);self.assertEqual(len(observed),2)
        self.assertTrue(watch.restore());self.assertIs(binding['profiles']['Python']['python_class'],Python)

if __name__=='__main__':unittest.main()
