"""Independent style/result/countdown/native-listener and Cue integration gate."""
import argparse
import json
from pathlib import Path
from collections import Counter


def require(value,text):
    if not value:raise RuntimeError(text)


def close(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return abs(a-b)<1e-5
    return a==b


def validate(report):
    require(report['status']=='passed' and report['error'] is None and report['native_mode']=='Standalone','native message widget run failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','native_invalid_material_index_tested','native_no_team_initialization_tested','callbacks_replayed','python_subscription_roots_added','native_proxies_cancelled_by_probe','health_properties_written'):
        require(report[key] is False,'message widget scope overclaim: '+key)
    for key in ('all_owned_widgets_removed','health_unchanged','profiles_and_cdo_selectors_restored','music_fields_and_provider_family_restored','probe_unrooted','native_gc_boundary_observed'):
        require(report[key] is True,'message widget cleanup missing: '+key)
    styles=report['style_pairs'];require(len(styles)==6,'native team/style matrix incomplete')
    require(Counter((r['team'],r['seeded']) for r in styles)==Counter((t,s) for t in (0,1,2) for s in (False,True)),'native seeded styles missing')
    for row in styles:
        require(close(row['original'],row['python']) and row['python_material_entries']==row['original_material_entries']==1,'actual native font/brush parity differs')
        require(row['python']['font']['SkewAmount']==0. and row['python']['font']['bForceMonospaced'] is False and row['python']['font']['bMaterialIsStencil'] is False and row['python']['font']['MonospacedWidth']==1.,'source font defaults were silently preserved instead of reset')
    results=report['result_pairs'];require(len(results)==4,'AbilityLevel result matrix incomplete')
    for row in results:
        require(close(row['original'],row['python']) and row['python_construct_entries']==row['original_construct_entries']==1 and row['python_literal_entries']==1,'native match result/animation/style parity differs')
        require(row['original_stingers']==row['python_stingers']==([] if row['kind']=='defeat' else [True]),'actual native Stinger receiver differs')
        require(row['python']['text']=={'draw':"You're All Winners",'victory':'Victorious','defeat':'Defeated'}[row['kind']],'source localized literal content differs')
    waiting=report['waiting_cases'];require(len(waiting)==6,'native initialization/profile-switch matrix incomplete')
    for row in waiting:
        require(row['natural_initializations']==1 and row['native_proxies_added']==1,'OnInitialized or original native proxy was replayed/duplicated')
        require(row['after_parent_messages']==0 and row['matching_callbacks']==3,'exact-match native listener delivery differs')
        require(row['countdown_started'] and row['first_message_animation']==(not row['initial_latch']) and row['latch_preserved_after_repeat_and_remove'],'one-shot countdown latch differs')
        require(row['selected_callback_profile']==row['expected_callback_profile'],'live native callback ignored Profile switch')
    require(report['owned_proxy_gi_refs_before_gc']==6 and report['owned_proxy_gi_refs_after_gc_and_message']==0 and report['owned_proxies_inactive_after_gc_and_message'],'native weak-widget/GI proxy cleanup differs')
    require(len(report['localized_text_pairs'])==3 and all(r['original']==r['python'] for r in report['localized_text_pairs']),'original localized waiting data adapter differs')
    require(Counter(r['class'] for r in report['manager_cases'])==Counter(('match','waiting')),'real message Cue children missing')
    for row in report['manager_cases']:
        require(row['default_python_message_dispatch'] and row['added'] and row['removed'] and row['native_parent_gate_entries']==1,'real Cue manager did not naturally execute migrated widget business')
    return dict(status='passed',native_style_pairs=6,native_result_pairs=4,natural_waiting_widgets=6,actual_owned_native_message_deliveries=18,real_manager_children=2,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
