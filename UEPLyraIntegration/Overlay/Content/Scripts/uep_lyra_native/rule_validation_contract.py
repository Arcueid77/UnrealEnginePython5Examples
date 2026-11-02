"""Bounded actual runtime gates; hardware, audio output and online stay explicit."""
import argparse
import json
from pathlib import Path


def require(value,message):
    if not value:raise AssertionError(message)


def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['selector_restored'] and r['owned_actors_destroyed'],'native rule runtime/cleanup failed')
    require(not any(r[k] for k in ('physical_input_tested','online_service_tested','network_acceptance','audio_playback_tested')),'rule runtime overclaim')
    family=r['family'];selected=r['profile'].endswith('Python');metrics=r['rule_metrics'];calls=sum(v for k,v in metrics['applied'].items() if k.startswith(family+'.'))
    require(calls>0 if selected else calls==0,'native/Python rule route differs: '+family)
    require(len(metrics['trace'])<=128,'rule trace unbounded')
    if family=='Device':
        for key in ('device_callback_inputs_supplied_by_fixture','unrelated_connection_ignored','owner_connection_scheduled','duplicate_notification_coalesced','native_process_tick_finished','unrelated_pairing_ignored','new_owner_pairing_scheduled','old_owner_pairing_scheduled','device_traits_restored'):require(r[key],'native device callback/ticker mismatch: '+key)
    elif family=='Replay':
        require([row['keep'] for row in r['replays']]==[0,1,2,5],'real memory replay retention limits missing')
        for row in r['replays']:require(row['created']==4 and row['remaining']==(4 if row['keep']==0 else min(4,row['keep'])) and row['failure_stopped'] and row['temporary_memory_only'] and row['cleaned'],'native replay deletion/requery/failure/cleanup differs')
    elif family=='Audio':
        require(r['audio_range_calls']==[True,False,True,False] and r['audio_loading_calls']==[False,True,True,False,False] and r['native_audio_state_and_readonly_chain_guards_passed'],'native audio mix/resource calls differ')
        if selected:
            loading=[row for row in metrics['trace'] if row['operation']=='Audio.Loading'][-5:]
            require([row['wanted'] for row in loading]==r['audio_loading_calls'],'native loading mix inputs not delivered')
            for row in loading:require(row['changed']==(row['before']!=row['wanted'] and row['has_mix'] and row['has_world']),'native loading mix duplicate/resource rule differs')
    elif family=='Damage':
        require(r['damage_queries']==[False,True,False,True,True,False,False,True],'native team/self/non-team/invalid damage query differs')
        d=r['actual_damage'];require(abs(d['enemy_before']-d['enemy_after']-10.)<.0001 and d['ally_before']==d['ally_after'],'original native damage GE did not respect enemy/friendly rules')
    else:
        require(family=='Pawn','unexpected rule family');p=r['pawn']
        require(p['player_state_priority'] and p['selected'] and p['experience_fallback'] and p['null_controller_rejected'] and p['bot_permissions'] and p['actual_pawn_class']==p['selected_pawn_class'],'native Pawn data/permissions/actual spawn differs')
    return dict(status='passed',family=family,profile=r['profile'],physical_input_tested=False,online_service_tested=False,audio_playback_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
