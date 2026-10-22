"""Natural input -> Arena bomb fuse -> self damage/death and native HUD."""


def validate(report):
    assert report['status']=='passed' and report['profile'] in ('Python','BlueprintFallback')
    assert report['local_players']==2 and report['distinct_player_owners']
    assert report['map']=='L_TopDown_LocalMultiplayer' and report['native_mode']=='Standalone'
    assert report['ability_granted_by_original_experience'] and report['input_action_from_original_pawn_data']
    assert report['input_entry']=='PlayerController.inject_enhanced_input_for_action'
    assert not any(report[k] for k in ('direct_ability_activation','callbacks_replayed','manual_bomb_spawn','attributes_written','pawn_position_written','physical_input_tested','network_acceptance','packaged_runtime','full_acceptance','damage_applied_by_fixture','explosion_called_by_fixture','death_called_by_fixture','natural_gameplay_state_reverted'))
    row=report['drop']
    assert row['owner']==0 and row['new_bombs']==1 and row['instigator_matches_owner'] and row['saved_state_matches_owner']
    assert row['remaining_before']==[1.,1.] and row['remaining_after']==[0.,1.] and row['foreign_owner_unchanged'] and row['bomb_profiles_match']
    natural=report['natural']
    assert natural['health_before']==[100.,100.] and natural['health_after']==[0.,100.]
    assert natural['bomb_destroyed_naturally'] and natural['remaining_after_refund']==[1.,1.]
    assert natural['native_death_started'] and natural['native_death_finished']
    assert natural['selected_death_callbacks']==[1,1] and natural['other_death_callbacks']==[0,0]
    assert natural['selected_bomb_destroyed_callback']==1 and natural['bombs_destroyed_by_cleanup']==0
    assert natural['original_fuse_seconds']>0 and natural['damage_after_creation_seconds']>=natural['original_fuse_seconds']-.15
    assert natural['bomb_age_at_first_observation_seconds']>=0
    assert abs(natural['damage_after_creation_seconds']-natural['damage_after_observation_seconds']-natural['bomb_age_at_first_observation_seconds'])<1e-5
    assert 1.85<=natural['death_task_seconds']<=2.5
    for phase,values in (('before',[1,1]),('spent',[0,1]),('refunded',[1,1])):
        rows=report['hud'][phase]
        assert {r['target_owner'] for r in rows}=={0,1}
        assert all(r['native_attribute_found'] and r['value']==values[r['target_owner']] and r['text']==str(values[r['target_owner']]) and r['effective_profile_matches'] and (phase=='before' or r['target_owner']==1 or r['selected_profile_callback']) for r in rows)
    assert report['hud_profiles_selected_after_native_construction_before_input']
    assert natural['native_move_distance']>=85. and natural['original_blast_query_contains_owner']
    assert report['cleanup_complete'] and report['native_local_player_removed'] and not report['health_unchanged']
    assert [r['phase'] for r in report['images']]==['before','spent','refunded']


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);args=parser.parse_args()
    report=json.loads(Path(args.report).read_text(encoding='utf-8-sig'));validate(report)
    import struct
    for row in report['images']:
        data=Path(row['path']).read_bytes()
        assert data[:8]==b'\x89PNG\r\n\x1a\n' and data[12:16]==b'IHDR'
        width,height=struct.unpack('>II',data[16:24]);assert width>0 and height>0
    print('Arena natural bomb/death/HUD contract passed')
