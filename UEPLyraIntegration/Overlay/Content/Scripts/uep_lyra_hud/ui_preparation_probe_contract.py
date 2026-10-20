"""Exact original latent macro versus shared Python class/setter semantics."""
import argparse
import json
from pathlib import Path
from uep_lyra_weapons.hero_burst_cue_contract import require
CASES=('null','spinner','loading_host','wrong_actor')
FALSE_FIELDS=('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_async_callbacks_replayed','health_properties_written')
def validate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_mode']=='Standalone','UI preparation probe failed')
    for field in FALSE_FIELDS:require(r[field] is False,'UI preparation probe overclaim: '+field)
    require(r['direct_python_helper_inputs'] is True,'direct helper test boundary missing')
    require(r['owned_objects_roots_loading_class_and_health_restored'] is True,'UI preparation probe cleanup failed')
    require([c['case'] for c in r['cases']]==list(CASES),'UI preparation native cases incomplete')
    for c in r['cases']:
        require(c['actual_original_native_completions']==c['actual_helper_native_continuations']==1 and c['original_setter_notifications']==c['python_setter_notifications']==1,'native preparation setter/continuation count differs')
        require(c['original_class']==c['python_class']==c['expected_class'],'native original/Python class semantics differ')
        if c['case'] in ('null','wrong_actor'):require(c['expected_class'] is None,'pure cast failure must clear and continue')
        else:require(c['expected_class'] is not None,'valid widget class missing')
    return dict(status='passed',native_original_macro_cases=4,direct_python_helper_cases=4,full_acceptance=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
