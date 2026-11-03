"""Same raw native network matrix, with the actual listen-host UI invariant."""
import argparse
import json
from pathlib import Path
import sys
SCRIPTS=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native import rule_network_contract as baseline
from uep_lyra_abilities.auto_respawn_reset_contract import RESET_CLASS,CHANNEL
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from uep_lyra_abilities.auto_respawn_events_contract import check_messages

def check_listen_reset_row(row,*,server=False,owner_client=False):
    pending='pending-long' in row['name'];switched='switch' in row['name']
    final=('BlueprintFallback' if row['profile']=='Python' else 'Python') if switched else row['profile']
    require(row['native_reset_class']==RESET_CLASS and row['native_reset_existing_specs']==1 and
        row['trigger_entry']=='SendGameplayEventToActor(GameplayEvent.RequestReset)' and row['native_reset_requests']==1,'real existing native Reset producer missing')
    # A Game listen process can retain its native UI reference after removing
    # its LocalPlayer. Assert that real stable reference instead of applying
    # the Editor dedicated-server invariant. Raw reports are never rewritten.
    require(row['old_pawn']!=row['new_pawn'] and row['health_before']>0 and row['health_after']>0 and
        row['death_after']==0 and row['native_type_preserved'] is True and row['delay_unchanged'] is True and
        row['specs_before']==row['specs_after'] and row['auto_active_before'] is row['auto_active_after'] and
        row['final_profile']==final and row['runtime_ended'] is False and row['reset_proxy_active'] is True and
        row['ui_valid_before'] is True and row['ui_valid_after'] is True,'listen Reset native state/Profile/UI/spec preservation differs')
    require(row['reset_messages']==[dict(channel=CHANNEL,player_id=row['player_id'],owner_matches=True)],'typed native Reset owner missing/duplicated')
    check_messages(row['event_messages'],row['player_id'],completion=True,duration_expected=pending)
    require(row['elapsed_game_seconds']>=(5.7 if pending else .3),'Reset observed before original delay')
    stats,ev=row['activation_counters'],row['event_counters']
    require(stats['native_reset_starts']==stats['native_reset_cancelled']==stats['removed']==stats['fallback_removed']==stats['end_cleanups']==stats['fallback_end_cleanups']==0,'Reset duplicated or ended its owned lifetime')
    require(stats['reset_messages']==stats['resets_handled']==int(final=='Python') and stats['foreign_resets']==0 and stats['fallback_reset_messages']==int(final=='BlueprintFallback'),'native Reset profile dispatch differs')
    require(ev['long_continuations']+ev['fallback_long_continuations']==int(pending) and
        ev['short_continuations']+ev['fallback_short_continuations']==1 and
        ev['native_restarts']==ev['native_completion_rpcs']==int(final=='Python' and not owner_client) and
        ev['cosmetic_completion_messages']==int(final=='Python' and not owner_client),'native Reset restart/RPC/cosmetic counts differ')
    require(row['observer_closed'] is True and row['original_delay_written'] is False and row['callbacks_replayed'] is False,'Reset observer/callback scope differs')

def validate(reports,family):
    original=baseline.check_row
    try:
        baseline.check_row=check_listen_reset_row
        result=baseline.validate(reports,family)
    finally:baseline.check_row=original
    return dict(result,packaged_authority_mode='ListenServer',native_listen_ui_reference_preserved=True,raw_peer_reports_rewritten=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--family',choices=('Damage','Pawn'),required=True);p.add_argument('--result',type=Path)
    a=p.parse_args();result=validate({peer:json.loads((a.directory/(peer+'.json')).read_text(encoding='utf-8-sig')) for peer in ('server','A','B0')},a.family)
    if a.result:a.result.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))
