"""Gate native extension ingress, ExperienceReady and un-replayed UMG ticks."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
CASES=[('zero',0.,True,'0:00'),('fraction',.999,True,'0:00'),('last-second',59.99,True,'0:59'),('minute',60.,True,'1:00'),('minute-fraction',61.99,True,'1:01'),('hour-edge',3599.99,True,'59:59'),('hour',3600.,True,'60:00'),('negative',-5.,True,'0:00'),('not-playing',120.,False,'0:00')]
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['mode'] in ('Baseline','Python','BlueprintFallback'),'Arena HUD native validation failed')
    for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','timer_tick_or_ready_replayed','native_delegates_broadcast_by_fixture','production_round_properties_changed','python_clock_added'):
        require(r[key] is False,'Arena HUD overclaim: '+key)
    require(r['cleanup_complete'] and r['pause_restored'] and r['natural_list'] and r['natural_timer'],'actual Arena HUD or owned cleanup missing')
    listing=r['list_ingress'];require(listing['native_begin_end_component'] and listing['entries_added']==1 and listing['entries_restored'] and listing['native_select_delta']==1 and listing['native_configure_delta']==1,'real extension component did not create/remove one native tile')
    require(r['selector_results']==[True,True,True] and r['invalid_widget_no_tile_configures'],'native list constant class or failed Widget cast differs')
    timer=r['natural_timer'];require(timer['ready_calls']>=1 and timer['tick_calls']>=2 and timer['mode_is_actual_component'],'actual native timer startup missing')
    require(r['owned_experience']['ready_next_frame'] and r['owned_experience']['mode_is_actual_component'],'owned native ExperienceReady did not wait a frame')
    require([v['name'] for v in r['clock_cases']]==[v[0] for v in CASES],'native countdown cases missing/reordered')
    for row,(_,seconds,playing,label) in zip(r['clock_cases'],CASES):
        require(row['input']==seconds and row['playing'] is playing and row['text']==label and row['native_tick_delta']>=2 and row['native_frame_delta']>=1 and row['world_time_frozen'],'original native countdown format or real paused UMG tick differs')
    require(r['invalid_mode']['text_unchanged'] and r['invalid_mode']['native_tick_delta']>=2,'invalid mode must leave previous text unchanged')
    require(r['remount']['construct_delta']==1 and r['remount']['ready_delta']==1 and r['remount']['native_ready_next_frame'] and r['remount']['actual_component_restored'],'natural timer remount did not recreate native experience observation')
    if r['mode']!='Baseline':
        p='python_' if r['mode']=='Python' else 'fallback_';other='fallback_' if r['mode']=='Python' else 'python_'
        for row,methods in ((r['natural_list_counts'],('select','configure')),(r['natural_timer_counts'],('construct','ready','tick'))):
            require(all(row[p+k]>=1 and row[other+k]==0 for k in methods),'selected natural HUD Profile did not execute')
    require(r['actual_round_properties_preserved'] and r['original_list_empty_events_stay_native'],'source round state/empty event preservation missing')
    return dict(status='passed',mode=r['mode'],native_clock_cases=len(CASES),native_extension_lifecycle=True,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
