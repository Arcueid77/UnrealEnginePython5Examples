import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Tools'))
import audit_reload_cleanup_acceptance as audit
from audit_migration_acceptance import attach_reload_cleanup_review


def closed():
    return dict(subscribed=3, unsubscribed=3, scope_created=1, scope_closed=1,
                active_count=0, active_scopes=0, ticker_active=False, active_widgets=[], errors=[])


def weapon():
    cases=[]
    for asset in audit.ASSETS:
        for scenario in ('initialized','ammo-5','ammo-4','ammo-3','ammo-2','ammo-1','ammo-0','ammo-30','weapon-switch'):
            cases.append(dict(asset=asset,scenario=scenario,baseline={'ammo':3},python={'ammo':3},python_calls={'Tick':1}))
        if asset == 'W_WeaponAmmoAndName':
            for scenario in ('empty-slot','slot-restored'):
                cases.append(dict(asset=asset,scenario=scenario,baseline={},python={},python_calls={'Tick':1}))
            cases.append(dict(asset=asset,scenario='reload-input-dispatch',native_input_intent_only=True,
                              python_calls={'Tick':1,'ReloadClicked':1}))
        else:
            cases.append(dict(asset=asset,scenario='brush-helper',resource_matches_argument=True,counter_style_preserved=True))
    return dict(status='passed', class_identity_preserved=True, persisted_declarations_used=True,
        restored_classes=4, cases=cases,
        subscription_scope=dict(status='passed',native_message_callbacks=1,cancel_verified=True,payload_access=False),
        profile_switches=[dict(asset=a,status='passed',without_reconstruct=True,observer_count_restored=4)
                          for a in audit.ASSETS],
        reload_cycles=[dict(status='passed',new_widget=True,native_gc_collected=True,
            python_housekeeper_gc_executed=True,before=dict(active_count=1,active_scopes=1),after=closed())
            for _ in range(3)], observer_cleanup=closed(),
        shutdown=dict(phase='python_atexit',owned_resources_closed_before_exit=True))


class ReloadCleanupAcceptanceTests(unittest.TestCase):
    @staticmethod
    def network():
        result={}
        for peer in ('server','A','B0','B1'):
            value=closed();count=0 if peer=='server' else (1 if peer=='B1' else 3)
            value.update(subscribed=count,unsubscribed=count,scope_created=count,scope_closed=count,
                         native_signals=int(peer in ('A','B0')))
            hud=dict(errors=[],active_widget_count=0,live_widget_reference_count=0,
                construct_count=count,destruct_count=count,controller_bind_count=count,
                controller_unbind_count=count,health_bind_count=count,health_unbind_count=count)
            result[peer]=dict(status='passed',shutdown=dict(status='passed',weapon_observer=value,hud=hud))
        return result

    def test_travel_and_rejoin_need_exercised_scopes_and_native_signals(self):
        audit.network_cleanup(self.network())
        for change in ('missing_rejoin','idle_travel','no_native_signals'):
            reports=self.network()
            if change=='missing_rejoin':reports.pop('B1')
            elif change=='idle_travel':reports['A']['shutdown']['weapon_observer'].update(scope_created=1,scope_closed=1)
            else:
                for report in reports.values():report['shutdown']['weapon_observer']['native_signals']=0
            with self.subTest(change=change),self.assertRaises(ValueError):audit.network_cleanup(reports)

    def test_hud_native_bindings_must_close_in_each_client(self):
        for key,value in [('health_unbind_count',0),('controller_unbind_count',0),('destruct_count',0),
                          ('active_widget_count',1),('live_widget_reference_count',1)]:
            reports=self.network();reports['B0']['shutdown']['hud'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):audit.network_cleanup(reports)

    def test_counter_balance_cannot_hide_live_callbacks_or_errors(self):
        audit.cleanup(closed(), exercised=True)
        for key, value in [('unsubscribed',2),('scope_closed',0),('active_count',1),
                           ('active_scopes',1),('ticker_active',True),('active_widgets',['old']),('errors',['bad'])]:
            report=closed();report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):audit.cleanup(report,exercised=True)

    def test_idle_dedicated_server_cannot_substitute_for_exercised_client(self):
        report=closed();report.update(subscribed=0,unsubscribed=0,scope_created=0,scope_closed=0)
        audit.cleanup(report,exercised=False)
        with self.assertRaises(ValueError):audit.cleanup(report,exercised=True)

    def test_every_reload_requires_new_widget_native_gc_and_no_duplicate_observer(self):
        audit.weapon_gate(weapon())
        for key in ('new_widget','native_gc_collected','python_housekeeper_gc_executed'):
            report=weapon();report['reload_cycles'][1][key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):audit.weapon_gate(report)
        report=weapon();report['reload_cycles'].pop()
        with self.assertRaises(ValueError):audit.weapon_gate(report)

    def test_passed_status_does_not_replace_state_router_or_cancellation_proof(self):
        changes=[lambda r:r.update(restored_classes=3),
            lambda r:r['cases'][0]['python'].update(ammo=999),
            lambda r:r['cases'][0]['python_calls'].update(Tick=0),
            lambda r:r['subscription_scope'].update(cancel_verified=False),
            lambda r:r['profile_switches'][0].update(without_reconstruct=False),
            lambda r:r['shutdown'].update(owned_resources_closed_before_exit=False)]
        for change in changes:
            report=weapon();change(report)
            with self.assertRaises(ValueError):audit.weapon_gate(report)

    def test_completed_process_requires_ordered_native_shutdown(self):
        text='DONE\nGoodbye Python\nCLEAN\nLog file closed'
        audit.log_gate(text,'DONE','CLEAN')
        audit.log_gate('Goodbye Python\nCLEAN\nLog file closed','Goodbye Python','CLEAN')
        for broken in (text.replace('Log file closed',''),text.replace('CLEAN','')+'\nCLEAN',
                       text+'\nLogPython: Error: unrelated',text+'\nTraceback'):
            with self.assertRaises(ValueError):audit.log_gate(broken,'DONE','CLEAN')

    def test_stale_sdk_or_source_cannot_reuse_a_passing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'UnrealEditor-UnrealEnginePython.dll'
            summary=dict(input_hashes=[dict(path=str(path),sha256=audit.SDK)])
            self.assertEqual(audit.frozen(summary,lambda p:audit.SDK),1)
            with self.assertRaises(ValueError):audit.frozen(summary,lambda p:'0'*64)
            with self.assertRaises(ValueError):audit.frozen({},lambda p:audit.SDK)

    def test_attachment_accepts_only_exact_original_criterion(self):
        report=dict(requirements=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.9.0',text='Other',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}',encoding='utf-8')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):
                attach_reload_cleanup_review(report,{}, {},directory,path)
            self.assertTrue(report['requirements'][0]['completion_proven'])
            self.assertFalse(report['requirements'][1]['completion_proven'])
            report['requirements'][0]['version']='0.10.0'
            with patch.object(audit,'verify_documentation',return_value={}),self.assertRaises(ValueError):
                attach_reload_cleanup_review(report,{}, {},directory,path)

    def test_recorded_proof_cannot_be_replaced_with_unchecked_counts(self):
        expected=dict(status='passed',criterion=audit.REQUIREMENT,controlled_new_widget_reload_cycles=3,
            live_profile_round_trips=4,same_editor_pie_sessions=3,real_network_phases=19,server_travels=2)
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=expected)
        with patch.object(audit,'inspect',return_value=expected):
            audit.verify_documentation(document,{}, {},'.')
            changed=copy.deepcopy(document);changed['review']['server_travels']=0
            with self.assertRaises(ValueError):audit.verify_documentation(changed,{}, {},'.')


if __name__ == '__main__':unittest.main()
