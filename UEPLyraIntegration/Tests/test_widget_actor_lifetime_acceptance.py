import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_widget_actor_lifetime_acceptance as audit
from audit_migration_acceptance import attach_widget_actor_lifetime_review


def counters():
    return dict(active_count=0, errors=[], scopes_created=1, scopes_closed=1)


def reports():
    value = {name:counters() for name in ('weapon_reticle_observers', 'reticle_host_observers',
        'ability_progress_observers', 'ability_failure_observers', 'dash_cooldown_observers',
        'respawn_timer_observers', 'quickbar_slot_observers')}
    value['status'] = 'passed'
    value['weapon_observer'] = dict(counters(), scope_created=1, scope_closed=1,
        subscribed=2, unsubscribed=2, active_scopes=0, ticker_active=False)
    value['nameplate_observers'] = {name:dict(counters(), helpers_rooted=1, helpers_unrooted=1)
        for name in ('sources', 'managers')}
    value['nameplate_observers']['widgets'] = dict(counters(), team_proxies_created=1,
        team_proxies_cancelled=1, init_bound=1, init_unbound=1, init_owner_released=0)
    return {'A':dict(shutdown=value)}


class WidgetActorLifetimeAcceptanceTests(unittest.TestCase):
    def test_no_owned_scope_declaration_cannot_hide_a_new_subscription(self):
        sources = {m:'SubscriptionScope()' for m in audit.OWNED}
        sources.update({m:'def Tick():\n    return 0\n' for m in audit.NO_PYTHON_SUBSCRIPTIONS})
        self.assertEqual(sum(r['owns_python_subscriptions'] for r in audit.ownership(sources)), 13)
        sources[audit.HUD+'open_menu_mixin'] += '\nSubscriptionScope()\n'
        with self.assertRaises(ValueError):audit.ownership(sources)

    def test_missing_original_policy_family_fails_before_acceptance(self):
        sources = {m:'SubscriptionScope()' for m in audit.OWNED}
        sources.update({m:'pass' for m in audit.NO_PYTHON_SUBSCRIPTIONS})
        sources.pop(audit.HUD+'action_touch_mixin')
        with self.assertRaises(ValueError):audit.ownership(sources)

    def test_zero_totals_do_not_prove_exercised_client_cleanup(self):
        value = counters(); audit.balanced(value, exercised=True)
        value.update(scopes_created=0, scopes_closed=0)
        with self.assertRaises(ValueError):audit.balanced(value, exercised=True)

    def test_balanced_counts_cannot_hide_a_live_owner_or_error(self):
        for delta in (dict(active_count=1), dict(scopes_closed=0), dict(errors=['late callback']),
                      dict(active_sources=['old-world']), dict(scopes_created=True, scopes_closed=True)):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                audit.balanced(dict(counters(), **delta), exercised=True)

    def test_pool_sampler_and_native_nameplate_leases_must_close(self):
        self.assertEqual(audit.combined_cleanup(reports())[0]['active_owned_subscriptions'], 0)
        value = reports(); value['A']['shutdown']['quickbar_slot_observers']['pool_lifetime'] = dict(
            counters(), registered=1, unregistered=1, ticker_active=True)
        with self.assertRaises(ValueError):audit.combined_cleanup(value)
        value = reports();value['A']['shutdown']['nameplate_observers']['widgets']['init_unbound'] = 0
        with self.assertRaises(ValueError):audit.combined_cleanup(value)
        value = reports();value['A']['shutdown']['nameplate_observers']['sources']['helpers_unrooted'] = 0
        with self.assertRaises(ValueError):audit.combined_cleanup(value)

    def test_all_original_candidates_and_order_are_required(self):
        initial = dict(assets=[dict(path=str(i), version='0.10.0') for i in range(32)])
        current = copy.deepcopy(initial);current['assets'].reverse()
        with self.assertRaises(ValueError):audit.inspect('.', current, initial)
        initial['assets'].pop()
        with self.assertRaises(ValueError):audit.inspect('.', initial, initial)
        with self.assertRaises(ValueError):audit.owned_assets(Path('.'), [], {'assets':[]}, {}, [])

    def test_only_the_exact_original_lifetime_requirement_is_promoted(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'review.json';path.write_text('{}', encoding='utf-8')
            rows = [dict(version='0.10.0', text=audit.REQUIREMENT, completion_proven=False),
                    dict(version='0.10.0', text='Each small batch behavior', completion_proven=False)]
            report = dict(requirements=rows, inputs=[])
            with patch.object(audit, 'verify_documentation', return_value=dict(status='passed')):
                attach_widget_actor_lifetime_review(report, {}, {}, temporary, path)
            self.assertTrue(rows[0]['completion_proven']);self.assertFalse(rows[1]['completion_proven'])
            rows[0]['version'] = '0.11.0'
            with patch.object(audit, 'verify_documentation', return_value=dict(status='passed')), self.assertRaises(ValueError):
                attach_widget_actor_lifetime_review(report, {}, {}, temporary, path)

    def test_metadata_flag_cannot_replace_reproduced_native_evidence(self):
        for document in (dict(criterion='partial', completion_proven=True),
                         dict(criterion=audit.REQUIREMENT, completion_proven=False)):
            with self.assertRaises(ValueError):audit.verify_documentation(document, {}, {}, '.')
        document = dict(criterion=audit.REQUIREMENT, completion_proven=True, review=dict(referenced_lifetime_processes=1))
        with patch.object(audit, 'inspect', return_value=dict(referenced_lifetime_processes=8)), self.assertRaises(ValueError):
            audit.verify_documentation(document, {}, {}, '.')
