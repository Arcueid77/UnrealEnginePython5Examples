"""Two real local players enter the original Arena drop path through input."""


def validate(report):
    assert report['status']=='passed' and report['profile'] in ('Python','BlueprintFallback')
    assert report['map']=='L_TopDown_LocalMultiplayer' and report['native_mode']=='Standalone'
    assert report['local_players']==2 and report['distinct_player_owners']
    assert report['ability_granted_by_original_experience'] and report['input_action_from_original_pawn_data']
    assert report['input_entry']=='PlayerController.inject_enhanced_input_for_action'
    assert not any(report[key] for key in ('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written','pawn_position_written','physical_input_tested','network_acceptance','packaged_runtime','full_acceptance'))
    assert [row['owner'] for row in report['cases']]==[0,1]
    for row in report['cases']:
        assert row['new_bombs']==1 and row['instigator_matches_owner'] and row['saved_state_matches_owner']
        assert row['remaining_before']==[1.,1.]
        expected=[1.,1.];expected[row['owner']]=0.
        assert row['remaining_after']==expected and row['foreign_owner_unchanged']
        assert row['repeat_input_new_bombs']==0 and row['repeat_input_keeps_cost']==expected
        assert row['native_destroy_refund']==[1.,1.] and row['selected_profile_callbacks']>0
        assert row['other_profile_callbacks']==0 and row['bomb_profiles_match']
    assert report['cleanup_complete'] and report['native_local_player_removed'] and report['health_unchanged']
    assert report['test_bombs_destroyed_before_fuse'] and not report['natural_explosion_tested']


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);args=parser.parse_args()
    validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))
    print('Arena two-local-player input ownership contract passed')
