"""Run unchanged scenario finish code with a private deferred-exit namespace."""
import argparse
import importlib
import json
from pathlib import Path
import types

SCENARIOS=(
    ('foundation_buttons','UEP_FOUNDATION_BUTTONS'),
    ('bound_action','UEP_BOUND_ACTION'),
    ('foundation_widgets','UEP_FOUNDATION_WIDGETS'),
    ('settings_editors','UEP_SETTINGS_EDITORS'),
    ('settings_screens','UEP_SETTINGS_SCREENS'),
    ('menu_buttons','UEP_MENU_BUTTONS'),
    ('session_button','UEP_SESSION_BUTTON'),
    ('experience_tile','UEP_EXPERIENCE_TILE'),
    ('credits_widgets','UEP_CREDITS_WIDGETS'),
    ('diagnostic_widgets','UEP_DIAGNOSTIC_WIDGETS'),
)


def require(value,message):
    if not value:raise RuntimeError(message)


def defer_finish_exit(function,on_exit):
    """The original bytecode and module globals stay unchanged.

    Only this cloned finish function sees the proxy. Cleanup, result writes and
    logs still call their original implementations. Native callbacks and the
    real module's request_exit remain outside the proxy.
    """
    original_ue=function.__globals__['ue']
    class ExitProxy:
        def __getattr__(self,name):
            return on_exit if name=='request_exit' else getattr(original_ue,name)
    namespace=dict(function.__globals__,ue=ExitProxy())
    deferred=types.FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    deferred.__kwdefaults__=function.__kwdefaults__
    deferred.__dict__.update(function.__dict__)
    return deferred


def validate(report,directory):
    require(report['status']=='passed' and report['error'] is None,'UI suite failed')
    require([r['scenario'] for r in report['cases']]==[name for name,_ in SCENARIOS],'Missing/reordered UI scenario')
    require(report['deferred_case_exit_requests']==len(SCENARIOS),'Each original finish must request exit exactly once')
    require(report['native_world_reused'] and report['final_native_exit_requested'] and report['finalized_during_actual_interpreter_exit'],'Combined native lifecycle evidence missing')
    for flag in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','original_scenario_assertions_changed'):
        require(report[flag] is False,'UI suite scope overclaim: '+flag)
    for row in report['cases']:
        require(row['status']=='passed' and row['error'] is None and row['exit_requests']==1 and row['original_finish_code_preserved'],'Scenario failed or original finish changed')
        p=Path(directory)/row['report_file'];value=json.loads(p.read_text(encoding='utf-8-sig'))
        require(value['status']=='passed' and value['error'] is None,'Native scenario report did not pass: '+row['scenario'])
        importlib.import_module('uep_lyra_hud.'+row['scenario']+'_contract').validate(value)
    return dict(status='passed',native_scenario_groups=len(SCENARIOS),one_native_process=True,full_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);args=parser.parse_args();p=Path(args.report)
    print(json.dumps(validate(json.loads(p.read_text(encoding='utf-8-sig')),p.parent)))
