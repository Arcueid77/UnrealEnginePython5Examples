"""Record CPP09 headless progress without accepting the actual-window gate."""
import argparse
import json
from pathlib import Path
from collect_native_escape_acceptance import REPO,SCRIPTS,load,sha,evidence,require,verify_setup
from uep_lyra_native.escape_validation_contract import validate_headless


def collect(root,runtime,output):
    root,runtime,output=(p.resolve() for p in (root,runtime,output))
    require(runtime.is_relative_to(REPO/'.build') and not output.exists(),'owned closed headless run and fresh progress ledger required')
    build,assets,plan,stage=verify_setup(root)
    summary=load(runtime/'summary.json')
    require(summary['status']=='passed' and summary['error'] is None and summary['validation_mode']=='headless_policy' and not summary['actual_window_input_acceptance'],'closed headless policy run required')
    report=load(runtime/'runtime.json');rules=validate_headless(report)
    require(load(runtime/'comparison.json')==rules,'independent headless comparison differs')
    negative=load(runtime/'negative-gates.json')
    require(negative['status']=='passed' and len(negative['cases'])==3 and all(r['rejected'] for r in negative['cases']),'headless evidence isolation checks failed')
    for row in summary['hashes']:require(sha(Path(row['path']))==row['sha256'],'frozen headless runtime input changed')
    require(sha(SCRIPTS/'uep_lyra_native/escape_menu.py')==sha(runtime/'Inputs/Overlay/Content/Scripts/uep_lyra_native/escape_menu.py'),'policy changed after native execution')
    result=dict(schema_version=1,status='implemented_headless_passed_actual_input_pending',batch='CPP09',candidates=['CPP-015'],accepted=False,target='UE5.8.1 / CPython3.11 / Win64 Development',
        policy_events=1,asset_family_count=5,native_python_headless_policy=rules,headless_evidence_rejected_by_actual_window_gate=negative['cases'],
        original_hud_defaults_graphs_visual_trees_and_inheritance_preserved=True,native_common_ui_binding_streamed_loading_and_input_ownership_preserved=True,
        native_menu_layer_class_owner_and_cleanup_verified=True,native_desired_menu_input_config_verified=True,actual_menu_input_mode_transition_acceptance=False,native_hud_destruct_and_rebuild_across_two_level_travels=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],headless_run_cpp_compile_executed=False,
        actual_os_keyboard_input_acceptance=False,visible_ui_window_and_menu_acceptance=False,full_shooter_scene_rendering_acceptance=False,
        pending_acceptance=['14 real Escape key presses in an unlocked actual game window','native input router entering Menu mode and restoring the original state','visible original Menu and final restored UI state'],
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,full_cpp_migration_acceptance=False,
        review_patch_reproduces_compiled_sources=True,patch_eof_format_only_repair=True,
        retained_attempts=['20261101-CPP09/Runtime01','20261101-CPP09/Runtime02','20261101-CPP09/Runtime03'],
        retained_headless_attempts=['20261102-CPP09/Headless01','20261102-CPP09/Headless02','20261102-CPP09/Headless03'],
        retained_notes=['Unchanged original rifle Niagara asset failed during uncooked full shooter rendering before UI validation. UI-only worlds isolate the policy; no Niagara repair or shooter rendering acceptance is claimed.',
            'Runtime02 used the wrong fixture stack name; corrected to the original GameLayer_Stack.',
            'Runtime03 reached input step one but the desktop was locked. No keyboard input was sent. Its identified process was stopped and operator-stop.json preserves that prerequisite.',
            'Headless01-03 observed an active original Menu with its desired Menu configuration while the offscreen action router stayed in All mode, even after waiting and disabling stack transitions. The headless lane checks native/Python observed-state equality and restoration; it explicitly does not accept the Menu-mode transition. The original actual-window gate still requires that transition.'],
        evidence=[evidence(root/'Build01/summary.json'),evidence(root/'Assets01/summary.json'),evidence(root/'Fixtures01/summary.json'),evidence(root/'PatchFormat01/summary.json'),evidence(runtime/'summary.json'),evidence(runtime/'runtime.json'),evidence(runtime/'comparison.json'),evidence(runtime/'negative-gates.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(status=result['status'],accepted=False,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.output),indent=2))
