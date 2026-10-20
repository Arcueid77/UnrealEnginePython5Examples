"""Independent native CommonUI deactivation and layer-restoration acceptance."""
import argparse,json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require

FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','deactivation_callback_replayed','original_widget_graphs_replaced')
def validate(r):
    require(r['status']=='passed' and r['error'] is None,'Explorer screen fixture failed')
    for k in FALSE_FIELDS:require(r[k] is False,'Explorer screen overclaim: '+k)
    for k in ('primary_player_inventory_and_health_unchanged','original_layer_widgets_and_transition_restored','owned_widgets_roots_profiles_and_class_selectors_restored'):require(r[k] is True,'Explorer screen cleanup missing: '+k)
    require([(v['kind'],v['profile']) for v in r['cases']]==[(k,p) for k in ('inventory','map') for p in ('BlueprintFallback','Python')],'Explorer screen profile matrix incomplete')
    for row in r['cases']:
        for k in ('natural_native_activation','native_deactivation_callback_once','removed_from_native_layer','repeat_deactivation_no_extra_callback','unstacked_deactivation_safe','original_stack_widgets_preserved'):require(row[k] is True,'native Explorer layer observation missing: '+k)
        require(row['counts']=={'python':int(row['profile']=='Python'),'fallback':int(row['profile']=='BlueprintFallback')},'Explorer screen routed wrong Profile')
    return dict(status='passed',native_screen_cases=4,full_acceptance=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(p.parse_args().report).read_text(encoding='utf-8-sig')))))
