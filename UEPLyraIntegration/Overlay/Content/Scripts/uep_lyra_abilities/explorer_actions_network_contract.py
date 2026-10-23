"""Original placed-target interaction prediction and owner-isolation evidence."""
import argparse,json
from pathlib import Path

PROFILES=('BlueprintFallback','Python')
PEERS=('A','B0')
CASES=tuple((peer,kind) for peer in PEERS for kind in ('collect','sit'))
TARGETS={k:'/ShooterExplorer/Items/'+n+'.'+n+'_C' for k,n in (('collect','B_InteractableRock'),('sit','B_InteractableChair'))}
FALSE_FIELDS=('full_acceptance','packaged_runtime','physical_input_tested','pixels_tested','cpp_compile_executed','cook_package_executed','callbacks_replayed','inventory_or_health_written','abilities_granted_by_fixture','fixture_actors_spawned','production_widget_reachability_tested','synthetic_duration_broadcast')

def require(value,message):
    if not value:raise ValueError(message)

def expected_inventory(before,templates):
    result=dict(before)
    for row in templates:result[row['definition']]=result.get(row['definition'],0)+row['count']
    return result

def validate(reports):
    require(set(reports)=={'server',*PEERS},'server and two actual clients required')
    profile=reports['server']['profile'];require(profile in PROFILES,'unsupported action profile')
    for peer,r in reports.items():
        require(r['status']=='passed' and r['error'] is None and r['peer']==peer and r['profile']==profile,'native peer did not pass')
        require(all(r[k] is False for k in FALSE_FIELDS),'network action scope overclaim')
        for key in ('selectors_restored','observers_restored','duration_scope_closed','actual_exit_finalizer','poses_restored'):
            require(r[key] is True,'network cleanup missing: '+key)
        require([(c['owner'],c['kind']) for c in r['cases']]==list(CASES),'actual original target sequence incomplete')
        require(r['shutdown_active_progress']==0,'progress listener survived interpreter shutdown')
    require(reports['A']['player_id']!=reports['B0']['player_id'],'two distinct original player owners required')
    prefix='python' if profile=='Python' else 'fallback';other='fallback' if profile=='Python' else 'python'
    for index,(owner,kind) in enumerate(CASES):
        authority=reports['server']['cases'][index]
        client=reports[owner]['cases'][index]
        foreign=reports[PEERS[1-PEERS.index(owner)]]['cases'][index]
        for row,role in ((authority,3),(client,2)):
            require(row['role']==role and row['target_class']==TARGETS[kind],'native target/authority role differs')
            require(len(row['events'])==1 and row['events'][0]['authority']==(role==3) and row['events'][0]['instigator']==row['pawn'] and row['events'][0]['target']==row['target'],'native GAS entry payload/role missing')
            require(len(row['action_deltas'])==1 and all(d[prefix+'_activate']==1 and d[other+'_activate']==0 and d[prefix+'_end']==1 and d[other+'_end']==0 for d in row['action_deltas']),'selected action profile was not executed exactly once')
            require(row['native_tasks_closed'],'native action task survived completion')
        if profile=='Python':
            require(client['action_deltas'][0]['client']==1 and client['action_deltas'][0]['native_duration_messages']==1 and authority['action_deltas'][0]['authority']==1 and authority['action_deltas'][0]['client']==0,'actual predicted/authority Python branch missing')
        require(client['input_asset']=='/ShooterExplorer/Input/Actions/IA_Interact.IA_Interact' and client['interactor_press_deltas'] and all(d[prefix+'_press']==1 and d[other+'_press']==0 for d in client['interactor_press_deltas']),'Enhanced Input did not traverse selected natural interactors')
        require(client['duration_delta']==1 and client['durations']==[{'instigator':client['pawn'],'duration':.5}] and client['progress_matched_original'] and client['progress_completed'],'predicted native duration and original/Python UI pair incomplete')
        require(authority['duration_delta']==0 and foreign['duration_delta']==0 and foreign['inventory_after']==foreign['inventory_before'] and foreign['own_activation_delta']==0,'duration/inventory/action crossed owner boundary')
        expected=expected_inventory(authority['inventory_before'],authority['pickup_templates']) if kind=='collect' else authority['inventory_before']
        require(authority['inventory_after']==expected and client['inventory_after']==expected and authority['other_inventory_before']==authority['other_inventory_after'],'native authoritative pickup or owner-only replication differs')
        require(authority['target_expired'] if kind=='collect' else authority['target_preserved'],'native placed target lifetime differs')
    return reports

def validate_pair(groups):
    require(len(groups)==2 and tuple(g['server']['profile'] for g in groups)==PROFILES,'original and Python network groups required')
    for g in groups:validate(g)
    for a,b in zip(groups[0]['server']['cases'],groups[1]['server']['cases']):
        for key in ('kind','owner','inventory_before','inventory_after','other_inventory_before','other_inventory_after','pickup_templates','target_class'):
            require(a[key]==b[key],'original/Python network result differs: '+key)
    return groups

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory');parser.add_argument('--directories',nargs=2);args=parser.parse_args()
    def load(directory):return {p:json.loads((Path(directory)/(p+'.json')).read_text(encoding='utf-8-sig')) for p in ('server',*PEERS)}
    if args.directories:validate_pair([load(d) for d in args.directories])
    elif args.directory:validate(load(args.directory))
    else:parser.error('--directory or --directories required')
    print('UEP_EXPLORER_ACTIONS_NETWORK_GATE_PASSED')
