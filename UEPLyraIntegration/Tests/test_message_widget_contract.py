"""Require full style state, actual native messages/GC and real Cue children."""
import copy
import unittest
from uep_lyra_hud.message_widget_contract import validate


def report():
    value=dict(status='passed',error=None,native_mode='Standalone',style_pairs=[],result_pairs=[],waiting_cases=[],localized_text_pairs=[],manager_cases=[])
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','native_invalid_material_index_tested','native_no_team_initialization_tested','callbacks_replayed','python_subscription_roots_added','native_proxies_cancelled_by_probe','health_properties_written'):value[key]=False
    for key in ('all_owned_widgets_removed','health_unchanged','profiles_and_cdo_selectors_restored','music_fields_and_provider_family_restored','probe_unrooted','native_gc_boundary_observed'):value[key]=True
    for team in (0,1,2):
        for seeded in (False,True):
            state=dict(font=dict(SkewAmount=0.,bForceMonospaced=False,bMaterialIsStencil=False,MonospacedWidth=1.),brushes={'slot':'material'})
            value['style_pairs'].append(dict(team=team,seeded=seeded,original=copy.deepcopy(state),python=state,python_material_entries=1,original_material_entries=1))
    for kind in ('draw','victory','defeat','draw'):
        state=dict(text={'draw':"You're All Winners",'victory':'Victorious','defeat':'Defeated'}[kind])
        value['result_pairs'].append(dict(kind=kind,original=copy.deepcopy(state),python=state,python_construct_entries=1,original_construct_entries=1,python_literal_entries=1,original_stingers=[] if kind=='defeat' else [True],python_stingers=[] if kind=='defeat' else [True]))
    for latch in (False,False,True,True,False,False):
        value['waiting_cases'].append(dict(natural_initializations=1,native_proxies_added=1,after_parent_messages=0,matching_callbacks=3,countdown_started=True,first_message_animation=not latch,initial_latch=latch,latch_preserved_after_repeat_and_remove=True,selected_callback_profile='Python',expected_callback_profile='Python'))
    value.update(owned_proxy_gi_refs_before_gc=6,owned_proxy_gi_refs_after_gc_and_message=0,owned_proxies_inactive_after_gc_and_message=True)
    value['localized_text_pairs']=[dict(original=str(i),python=str(i)) for i in range(3)]
    value['manager_cases']=[dict(**{'class':label},default_python_message_dispatch=True,added=True,removed=True,native_parent_gate_entries=1) for label in ('match','waiting')]
    return value


class MessageWidgetContractTests(unittest.TestCase):
    def test_complete_native_widget_matrix(self):self.assertEqual(validate(report())['actual_owned_native_message_deliveries'],18)
    def test_full_font_or_brush_state_difference_rejected(self):
        value=report();value['style_pairs'][0]['python']['brushes']['slot']='different'
        with self.assertRaises(RuntimeError):validate(value)
    def test_identical_but_wrong_preserved_font_defaults_rejected(self):
        value=report()
        for side in ('original','python'):value['style_pairs'][0][side]['font']['SkewAmount']=.5
        with self.assertRaises(RuntimeError):validate(value)
    def test_wrong_ability_result_literal_is_rejected(self):
        value=report();value['result_pairs'][0]['python']['text']='Defeated'
        with self.assertRaises(RuntimeError):validate(value)
    def test_actual_stinger_forwarding_required(self):
        value=report();value['result_pairs'][1]['python_stingers']=[]
        with self.assertRaises(RuntimeError):validate(value)
    def test_two_python_runs_are_not_a_blueprint_comparator(self):
        value=report();value['style_pairs'][0]['original_material_entries']=0
        with self.assertRaises(RuntimeError):validate(value)
    def test_replayed_initialization_or_duplicate_proxy_rejected(self):
        value=report();value['waiting_cases'][0]['native_proxies_added']=2
        with self.assertRaises(RuntimeError):validate(value)
    def test_parent_channel_must_not_reach_exact_listener(self):
        value=report();value['waiting_cases'][0]['after_parent_messages']=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_live_callback_must_follow_switched_profile(self):
        value=report();value['waiting_cases'][-1]['selected_callback_profile']='BlueprintFallback'
        with self.assertRaises(RuntimeError):validate(value)
    def test_gc_and_matching_message_must_release_owned_native_proxies(self):
        value=report();value['owned_proxy_gi_refs_after_gc_and_message']=1
        with self.assertRaises(RuntimeError):validate(value)
    def test_real_cue_children_and_bounded_scope_required(self):
        value=report();value['manager_cases'].pop()
        with self.assertRaises(RuntimeError):validate(value)
        value=report();value['pixels_tested']=True
        with self.assertRaises(RuntimeError):validate(value)
