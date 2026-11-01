"""Native spawner guards, real timer/standing overlap, and destroy proof."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'spawner runtime/finalizer failed')
    require([c['name'] for c in r['guards']]==['null_pawn','pawn_without_asc','missing_definition','unavailable','full_slots'],'native spawner guard matrix incomplete')
    require(all(c['unchanged'] for c in r['guards']),'rejected native pickup mutated inventory/availability')
    selected='python_' if r['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_';m=r['metrics']
    require(m[selected+'attempt']>=8 and m[selected+'complete']==m[selected+'reset']==1 and all(m[other+k]==0 for k in ('attempt','complete','reset')),'native spawner selected dispatch/timer completion differs')
    require(r['first_pickup_delta']==1 and r['cooldown_reentry_delta']==0 and r['standing_overlap_delta']==2 and r['overlap_begin_events']==1,'native success/reentry/stationary retry differs')
    require(r['pickup_visibility_hidden'] and r['timer_reset_visibility_restored'] and r['destroyed_with_cooldown_pending'] and r['no_callbacks_after_destroy'],'native timer/availability/lifetime proof incomplete')
    require(r['original_player_and_inventory_restored'] and r['selectors_restored'] and r['scope_closed'],'spawner native state cleanup failed')
    require(not r['timer_callback_replayed'] and not r['native_timer_replaced'],'spawner native timers bypassed')


def compare(a,b):
    validate(a);validate(b)
    for key in ('guards','first_pickup_delta','cooldown_reentry_delta','standing_overlap_delta','overlap_begin_events'):require(a[key]==b[key],'native/Python spawner result differs: '+key)
    return dict(status='passed',guards=5,native_timer_completion=True,stationary_native_overlap_retry=True,destroy_cancels_callbacks=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--python',type=Path,required=True);a=p.parse_args();print(json.dumps(compare(json.loads(a.native.read_text(encoding='utf-8-sig')),json.loads(a.python.read_text(encoding='utf-8-sig'))),indent=2))
