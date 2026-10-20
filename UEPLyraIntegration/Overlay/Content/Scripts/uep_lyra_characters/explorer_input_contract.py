"""Actual engine injections on both Explorer classes; native GAS/equipment results."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
from .enhanced_input_contract import ACTIONS,CASES
from .quickbar_input_contract import DEFINITIONS
CLASSES={key:'/ShooterExplorer/Blueprint/'+name+'.'+name+'_C' for key,name in (('hero','B_Hero_Explorer'),('pawn','B_Pawn_Explorer'))}

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','whole_characters_migrated','physical_keyboard_tested','python_handler_replayed','bp_receiver_called_by_fixture','inventory_properties_written','native_rpc_bypassed')
TRUE_FIELDS=('original_player_inventory_and_health_unchanged','owned_objects_profiles_roots_and_tasks_restored','owned_native_proxies_and_observers_closed')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['profile'] in ('Python','BlueprintFallback'),'Explorer input native validation failed')
    for name in FALSE_FIELDS:require(r[name] is False,'Explorer input overclaim: '+name)
    for name in TRUE_FIELDS:require(r[name] is True,'Explorer input cleanup missing: '+name)
    require([c['kind'] for c in r['characters']]==['hero','pawn'],'both original Explorer input classes required')
    for actor in r['characters']:
        require(actor['native_class']==CLASSES[actor['kind']] and set(actor['native_receiver_names'])==set(ACTIONS),'original input class/binding table missing')
        require(actor['native_profile_method_counts']==dict(Python=25,BlueprintFallback=20),'native Original fallback/profile family differs')
        require([case['name'] for case in actor['input_cases']]==[c[0] for c in CASES],'native input case matrix incomplete')
        for row,spec in zip(actor['input_cases'],CASES):
            name,action,initial,expected,empty=spec;_,_,magnitude,tag=ACTIONS[action];py=r['profile']=='Python';sent=empty is None;model=row['inventory']
            require(row['positive_native_injections']==1 and row['native_input_subsystem_used'] and row['native_bound_receiver']==actor['native_receiver_names'][action] and row['receiver_is_native_router'],'actual engine input/retained receiver path missing')
            require(row['input_counters']==dict(python_calls=int(py),fallback_calls=0,**{key:int(py and key==action) for key in ACTIONS}) and row['helper_counters']['python_calls']==int(py) and row['helper_counters']['fallback_calls']==int(not py),'input receiver/helper dispatch count differs')
            require(model['active']==expected and model['items']==sorted(DEFINITIONS) and model['slots']==[None if i==empty else item for i,item in enumerate(DEFINITIONS)] and model['definition']==DEFINITIONS[expected] and model['equipment_instigator_matches'] and model['equipment_class']==DEFINITIONS[expected].replace('/ID_','/B_WeaponInstance_').replace('.ID_','.B_WeaponInstance_'),'native input inventory/equipment result differs')
            require(row['events']==([dict(tag=tag,magnitude=float(magnitude),instigator_null=True,target_null=True,optional_objects_null=True)] if sent else []),'native input GAS tag/raw default magnitude differs')
            require(row['native_tasks_before']==row['native_tasks_after']==3 and row['inventory_items_unchanged'] and row['task_scope_closed'] and row['no_repeated_or_release_handler'],'native input task/release/owned-item lifetime differs')
    return dict(status='passed',profile=r['profile'],characters=2,native_input_cases=16,whole_characters_migrated=False,full_acceptance=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
