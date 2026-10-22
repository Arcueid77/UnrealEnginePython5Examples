import unittest
from uep_lyra_abilities.arena_natural_bomb_contract import validate
from uep_lyra_hud.startup import validation_module


def report():
    result=dict(status='passed',profile='Python',local_players=2,distinct_player_owners=True,map='L_TopDown_LocalMultiplayer',native_mode='Standalone',ability_granted_by_original_experience=True,input_action_from_original_pawn_data=True,input_entry='PlayerController.inject_enhanced_input_for_action',cleanup_complete=True,native_local_player_removed=True,health_unchanged=False)
    for key in ('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written','pawn_position_written','physical_input_tested','network_acceptance','packaged_runtime','full_acceptance','damage_applied_by_fixture','explosion_called_by_fixture','death_called_by_fixture','natural_gameplay_state_reverted'):result[key]=False
    result['drop']=dict(owner=0,new_bombs=1,instigator_matches_owner=True,saved_state_matches_owner=True,remaining_before=[1.,1.],remaining_after=[0.,1.],foreign_owner_unchanged=True,bomb_profiles_match=True)
    result['natural']=dict(health_before=[100.,100.],health_after=[0.,100.],bomb_destroyed_naturally=True,remaining_after_refund=[1.,1.],native_death_started=True,native_death_finished=True,selected_death_callbacks=[1,1],other_death_callbacks=[0,0],selected_bomb_destroyed_callback=1,bombs_destroyed_by_cleanup=0,original_fuse_seconds=2.,bomb_age_at_first_observation_seconds=.4,damage_after_observation_seconds=1.6,damage_after_creation_seconds=2.,death_task_seconds=2.,native_move_distance=90.,original_blast_query_contains_owner=True)
    result['hud']={phase:[dict(target_owner=i,native_attribute_found=True,value=float(v),text=str(v),selected_profile_callback=True,effective_profile_matches=True) for i,v in enumerate(values)] for phase,values in (('before',[1,1]),('spent',[0,1]),('refunded',[1,1]))}
    result['hud_profiles_selected_after_native_construction_before_input']=True
    result['images']=[dict(phase=phase,path=phase+'.png') for phase in ('before','spent','refunded')]
    return result


class ArenaNaturalBombContractTests(unittest.TestCase):
    def test_natural_self_death_keeps_foreign_owner_alive(self):validate(report())

    def test_entry_is_explicit_and_commandlets_excluded(self):
        flag='-UEPArenaNaturalResult=owned/result.json'
        self.assertEqual(validation_module([flag]),'uep_lyra_abilities.arena_natural_bomb_validation')
        self.assertIsNone(validation_module(['-run=Py',flag]))

    def test_direct_damage_explosion_or_death_calls_rejected(self):
        for field in ('damage_applied_by_fixture','explosion_called_by_fixture','death_called_by_fixture'):
            value=report();value[field]=True
            with self.subTest(field=field),self.assertRaises(AssertionError):validate(value)

    def test_early_destroy_cannot_prove_natural_fuse(self):
        value=report();value['natural']['bombs_destroyed_by_cleanup']=1
        with self.assertRaises(AssertionError):validate(value)
        value=report();value['natural'].update(damage_after_observation_seconds=.1,damage_after_creation_seconds=.5)
        with self.assertRaises(AssertionError):validate(value)

    def test_foreign_owner_damage_is_rejected(self):
        value=report();value['natural']['health_after']=[0.,0.]
        with self.assertRaises(AssertionError):validate(value)

    def test_native_two_second_death_task_and_profile_required(self):
        for field,new in (('death_task_seconds',.1),('selected_death_callbacks',[1,0]),('other_death_callbacks',[1,1])):
            value=report();value['natural'][field]=new
            with self.subTest(field=field),self.assertRaises(AssertionError):validate(value)

    def test_hud_must_follow_each_actual_target(self):
        value=report();value['hud']['spent'][1]['text']='0'
        with self.assertRaises(AssertionError):validate(value)

    def test_unchanged_foreign_attribute_needs_no_update_callback(self):
        value=report()
        for phase in ('spent','refunded'):value['hud'][phase][1]['selected_profile_callback']=False
        validate(value)
        value['hud']['spent'][0]['selected_profile_callback']=False
        with self.assertRaises(AssertionError):validate(value)

    def test_refund_and_teardown_are_required(self):
        value=report();value['natural']['remaining_after_refund']=[0.,1.]
        with self.assertRaises(AssertionError):validate(value)
        value=report();value['cleanup_complete']=False
        with self.assertRaises(AssertionError):validate(value)
