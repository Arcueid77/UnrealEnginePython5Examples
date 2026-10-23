"""Semantic checks for actual Explorer inventory Experience input and native UI."""
import argparse,json
from pathlib import Path
MAP='/ShooterExplorer/Maps/L_InventoryTestMap'
PROFILES=('BlueprintFallback','Python')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','physical_input_tested','cpp_compile_executed','cook_package_executed','callbacks_replayed','inventory_or_health_written','abilities_granted_by_fixture','fixture_actors_spawned')
def require(value,message):
    if not value:raise ValueError(message)
def validate(report):
    require(report['status']=='passed' and report['error'] is None,'Explorer actual Experience did not pass')
    require(all(report[k] is False for k in FALSE_FIELDS),'Explorer Experience scope overclaimed')
    require(report['selectors_restored'] and report['actual_exit_finalizer'] and report['old_profile_pawns_and_controllers_destroyed'],'Explorer travel/profile/actual exit cleanup missing')
    require(report['native_level_open_requests']==1 and len(report['cases'])==1 and report['selected_profile'] in PROFILES,'one isolated fresh Explorer profile world required')
    require('/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C' in report['selected_class_paths'],'actual Explorer hero not selected')
    for row in report['cases']:
        profile=report['selected_profile']
        prefix='python' if profile=='Python' else 'fallback'
        require(row['profile']==profile and row['world']==MAP+'.L_InventoryTestMap' and row['pawn_class']=='/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C','actual original Explorer world/hero/profile changed')
        require(row['experience']=='/ShooterExplorer/System/Experiences/B_TestInventoryExperience.Default__B_TestInventoryExperience_C','original native inventory Experience not active')
        require(row['visible'] and row['health']==100. and row['native_role']==3 and row['input_subsystem_used'],'natural Explorer readiness/authority/input missing')
        require(row['initial_inventory'] and row['inventory_preserved'],'actual original Explorer inventory missing or modified')
        require(row['natural_begin'][prefix+'_calls']==1 and row['natural_begin']['fallback_calls' if profile=='Python' else 'python_calls']==0,'fresh native BeginPlay did not use exactly one selected profile')
        require(row['movement']['input_frames']==24 and row['movement']['distance_squared']>100.,'native movement input did not move actual Explorer pawn')
        require([m['kind'] for m in row['menus']]==['inventory','map'],'actual native Explorer menu input sequence incomplete')
        for menu in row['menus']:
            require(menu['native_layer']=='UI.Layer.GameMenu' and menu['native_widgets']>=1 and menu['native_active_widget_observed'] and menu['native_removed'],'actual native Explorer screen lifecycle incomplete')
            require(len(menu['callback_deltas'])==menu['native_widgets'] and all(d==dict(python=int(profile=='Python'),fallback=int(profile!='Python')) for d in menu['callback_deltas']),'Explorer screen deactivation did not use selected profile once')
    return report
def validate_pair(reports):
    require(len(reports)==2 and tuple(r['selected_profile'] for r in reports)==PROFILES,'two isolated Original/Python Explorer reports required')
    for report in reports:validate(report)
    first,second=[r['cases'][0] for r in reports]
    require(reports[0]['selected_class_paths']==reports[1]['selected_class_paths'],'Original/Python selected native class scope differs')
    require(first['initial_inventory']==second['initial_inventory'] and first['granted_abilities']==second['granted_abilities'],'original/Python actual Experience grants differ')
    require([m['native_widgets'] for m in first['menus']]==[m['native_widgets'] for m in second['menus']],'original/Python actual menu stack counts differ')
    return reports
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report');parser.add_argument('--reports',nargs=2);args=parser.parse_args()
    if args.reports:validate_pair([json.loads(Path(p).read_text(encoding='utf-8-sig')) for p in args.reports])
    elif args.report:validate(json.loads(Path(args.report).read_text(encoding='utf-8-sig')))
    else:parser.error('--report or --reports is required')
    print('UEP_EXPLORER_EXPERIENCE_GATE_PASSED')
