import unittest
from uep_lyra_abilities.arena_local_input_contract import validate
from uep_lyra_hud.startup import validation_module


def report():
    result=dict(status='passed',profile='Python',map='L_TopDown_LocalMultiplayer',native_mode='Standalone',local_players=2,distinct_player_owners=True,ability_granted_by_original_experience=True,input_action_from_original_pawn_data=True,input_entry='PlayerController.inject_enhanced_input_for_action',cleanup_complete=True,native_local_player_removed=True,health_unchanged=True,test_bombs_destroyed_before_fuse=True,natural_explosion_tested=False,cases=[])
    for key in ('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written','pawn_position_written','physical_input_tested','network_acceptance','packaged_runtime','full_acceptance'):result[key]=False
    for owner in (0,1):
        after=[1.,1.];after[owner]=0.
        result['cases'].append(dict(owner=owner,new_bombs=1,instigator_matches_owner=True,saved_state_matches_owner=True,remaining_before=[1.,1.],remaining_after=after,foreign_owner_unchanged=True,repeat_input_new_bombs=0,repeat_input_keeps_cost=after,native_destroy_refund=[1.,1.],selected_profile_callbacks=3,other_profile_callbacks=0,bomb_profiles_match=True))
    return result


class ArenaLocalInputContractTests(unittest.TestCase):
    def test_both_owners_must_independently_enter_native_input(self):
        validate(report())
        value=report();value['cases'][1]['owner']=0
        with self.assertRaises(AssertionError):validate(value)

    def test_input_route_is_explicit_and_not_a_commandlet(self):
        flag='-UEPArenaLocalInputResult=owned/result.json'
        self.assertEqual(validation_module([flag]),'uep_lyra_abilities.arena_local_input_validation')
        self.assertIsNone(validation_module(['-run=Py',flag]))

    def test_foreign_cost_cannot_change(self):
        value=report();value['cases'][0]['remaining_after']=[0.,0.]
        with self.assertRaises(AssertionError):validate(value)

    def test_injected_ability_or_replayed_callbacks_cannot_prove_input(self):
        for key in ('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written'):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(AssertionError):validate(value)

    def test_wrong_bomb_owner_and_wrong_profile_rejected(self):
        for key in ('instigator_matches_owner','saved_state_matches_owner','bomb_profiles_match'):
            value=report();value['cases'][1][key]=False
            with self.subTest(key=key),self.assertRaises(AssertionError):validate(value)

    def test_cost_rejection_and_refund_are_required(self):
        value=report();value['cases'][0]['repeat_input_new_bombs']=1
        with self.assertRaises(AssertionError):validate(value)
        value=report();value['cases'][0]['native_destroy_refund']=[0.,1.]
        with self.assertRaises(AssertionError):validate(value)

    def test_cleanup_and_health_cannot_be_omitted(self):
        for key in ('cleanup_complete','native_local_player_removed','health_unchanged'):
            value=report();value[key]=False
            with self.subTest(key=key),self.assertRaises(AssertionError):validate(value)

    def test_synthetic_input_does_not_claim_hardware_or_natural_fuse(self):
        for key in ('physical_input_tested','natural_explosion_tested','packaged_runtime','full_acceptance'):
            value=report();value[key]=True
            with self.subTest(key=key),self.assertRaises(AssertionError):validate(value)
