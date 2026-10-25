"""Forensic classification must not turn name matches/retries into a fix."""
import copy,importlib.util,tempfile,unittest
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
    def test_phase_offsets_compare_native_timestamps_without_actor_identity_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'server.log').write_text("[2026.10.17-18.03.06:700][651] Beginning Phase 'ShooterGame.GamePhase.Playing'\n",encoding='utf-8')
            (root/'B0.log').write_text('[2026.10.17-18.03.08:389][56] '+self.log+'\n[2026.10.17-18.03.08:672][62] OnExperienceLoadComplete(Client)\n',encoding='utf-8')
            result=analysis.phase_timing(root);rows=result['events']['B0']
            self.assertEqual([r['seconds_from_authority_playing'] for r in rows],[1.689,1.972])
            self.assertFalse(result['cross_peer_actor_identity_claimed']);self.assertFalse(result['cause_or_fix_proven'])
    def test_missing_authority_phase_is_not_invented_from_client_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'B0.log').write_text('[2026.10.17-18.03.08:389] '+self.log,encoding='utf-8')
            result=analysis.phase_timing(root);self.assertFalse(result['authority_playing_observed'])
            self.assertIsNone(result['events']['B0'][0]['seconds_from_authority_playing'])
    def test_timestamps_not_wrapping_frame_numbers_determine_phase_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'server.log').write_text("[2026.10.17-18.03.06:700][999] Beginning Phase 'ShooterGame.GamePhase.Playing'",encoding='utf-8')
            (root/'A.log').write_text('[2026.10.17-18.03.07:700][2] OnExperienceLoadComplete(Client)',encoding='utf-8')
            self.assertEqual(analysis.phase_timing(root)['events']['A'][0]['seconds_from_authority_playing'],1.)
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

class RetiredPawnWireIdentityTests(unittest.TestCase):
    def fixture(self):
        def row(actor,guid,avatar,pawn,health=100.):
            return dict(actor=actor,role=1,health=health,player_state_pawn=pawn,health_set='set' if health else None,
                actor_asc='asc' if health else None,extension_asc='asc' if health else None,
                network_identity=dict(valid=True,transport='Legacy',wire_id=guid),
                player_state_network_identity=dict(valid=True,transport='Legacy',wire_id='9'),
                player_state_asc=dict(avatar=avatar,health_attributes=[dict(health=100.)]))
        def event(kind,t,data,file):return dict(kind=kind,elapsed=t,data=data,file=file,run_id='same-run')
        reset=row('server-old','10','server-old','server-old');reset['role']=3
        current=row('server-current','20','server-current','server-current');current['role']=3
        return dict(server=[event('native-reset',1.,reset,'reset'),event('native-end-play',2.,dict(actor='server-old'),'retired'),event('native-binding-change',2.5,current,'authority-current')],
            B0=[event('native-binding-change',1.,row('current','20','current','current'),'healthy'),
                event('native-begin-play',2.,row('late-old','10','late-old','current'),'late-birth'),
                event('native-end-play',3.,dict(actor='late-old'),'late-end'),
                event('native-binding-change',4.,row('current','20',None,'current',0.),'gap')])
    def test_old_authority_guid_reappears_after_live_pawn_and_steals_binding(self):
        join,=analysis.correlate_retired_pawns(self.fixture())
        self.assertEqual(join['stale_pawn_wire'],['Legacy','10']);self.assertEqual(join['current_pawn_wire'],['Legacy','20'])
        self.assertFalse(join['cross_peer_actor_names_used_for_identity']);self.assertFalse(join['gameplay_repair_proven'])
    def test_cross_peer_names_do_not_replace_actor_or_state_guid(self):
        for key in ('network_identity','player_state_network_identity'):
            data=self.fixture();data['B0'][1]['data'][key]['wire_id']='other'
            self.assertEqual(analysis.correlate_retired_pawns(data),[])
    def test_mixed_native_runs_are_rejected(self):
        data=self.fixture();data['B0'][1]['run_id']='foreign'
        with self.assertRaises(ValueError):analysis.correlate_retired_pawns(data)
    def test_retirement_and_subsequent_real_empty_binding_are_both_required(self):
        data=self.fixture();data['server']=[e for e in data['server'] if e['kind']!='native-end-play'];self.assertEqual(analysis.correlate_retired_pawns(data),[])
        data=self.fixture();data['B0'][-1]['data']['health']=100.;self.assertEqual(analysis.correlate_retired_pawns(data),[])
    def test_live_current_pawn_guid_must_also_be_confirmed_by_authority(self):
        data=self.fixture();data['server'].pop();self.assertEqual(analysis.correlate_retired_pawns(data),[])
    def test_same_clock_tick_uses_numeric_publication_order_for_immediate_destruction(self):
        data=self.fixture()
        for index,event in enumerate(data['B0']):
            event['file']='B0-early-readiness-'+str(index+7)+'.json'
            if index:event['elapsed']=2.
        self.assertEqual(len(analysis.correlate_retired_pawns(data)),1)
        data['B0'][1]['file']='B0-early-readiness-9.json';data['B0'][2]['file']='B0-early-readiness-8.json'
        self.assertEqual(analysis.correlate_retired_pawns(data),[])

if __name__=='__main__':unittest.main()
