"""Independent native async/order/cancel/duration/lifecycle assertions."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require

NAMES=['filter_channel_foreign_and_no_owner','real_registry_fifo','out_of_order_2_1_0','cancel_current','cancel_pending','location_skip_advances_sequence','removed_visible_timer_cancelled','pending_async_cancel_and_rebuild','real_native_foreign_notification_filtered','single_listener_after_rebuild','invalid_registry_id_rolls_back']


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'native accolade runtime/finalizer failed')
    require([c['name'] for c in r['cases']]==NAMES,'accolade policy matrix incomplete')
    for case in r['cases']:
        if 'pairs' not in case:continue
        a,b=case['pairs'];require(a['profile']=='NativeFallback' and b['profile']=='Python','native/Python host pair differs')
        for field in ('create_order','kinds','sequences'):require(a[field]==b[field],'native/Python accolade '+field+' differs: '+case['name'])
        if case['name']!='cancel_current':require(a['duration_checks'] and b['duration_checks'],'native display duration differs: '+case['name'])
    require(r['cases'][0]['results']==[True,True] and r['cases'][-1]['allocated']==[0,0] and r['cases'][-1]['empty'],'filter/failure branch failed')
    require(r['async_pending_at_rebuild']==[True,True],'teardown fixture did not overlap an actual pending native asset callback')
    require(r['registry_pending_at_rebuild']==[True,True],'teardown fixture did not overlap an actual pending native registry callback')
    require(all(r['cases'][i]['passed'] for i in (6,7,8)),'native remove/rebuild/filter failed')
    for row in r['metrics']:
        selected='python_' if row['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_';m=row['metrics']
        require(all(m[selected+k]>0 for k in ('notify','row','consider','process','display','pop','clear')),'selected accolade policy bypassed')
        require(all(m[other+k]==0 for k in ('notify','row','consider','process','display','pop','clear')),'wrong accolade policy executed')
    require(r['presentation_samples'] and all(all(s.values()) for s in r['presentation_samples']),'native FText/icon/widget presentation regression failed')
    require(r['widgets_removed_and_unrooted'] and r['profile_classes_restored'],'accolade ownership cleanup failed')
    require(not any(r[k] for k in ('timer_callbacks_replayed','native_registry_replaced','localized_text_roundtripped','network_acceptance')),'accolade runtime overclaims')
    return dict(status='passed',cases=len(NAMES),native_registry_and_asset_callbacks=True,original_cpp_python_queue_order_equal=True,native_timer_and_rebuild_cleanup=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);print(json.dumps(validate(json.loads(p.parse_args().report.read_text(encoding='utf-8-sig'))),indent=2))
