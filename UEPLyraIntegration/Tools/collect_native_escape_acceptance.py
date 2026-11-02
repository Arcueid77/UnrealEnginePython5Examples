"""Close actual-window Escape routing, native UI input, and travel evidence."""
import argparse
import json
from pathlib import Path
import sys
from collect_native_message_acceptance import REPO,SCRIPTS,load,sha,evidence
sys.path.insert(0,str(SCRIPTS))
from uep_lyra_native.escape_validation_contract import require,validate


def verify_setup(root):
    require(root.is_relative_to(REPO/'.build'),'owned Escape evidence required')
    build=load(root/'Build01/summary.json');assets=load(root/'Assets01/summary.json');plan=load(Path(build['plan']['path']));stage=Path(plan['stage']);overlay=REPO/'Demos/UEPLyraIntegration/Overlay'
    require(build['status']=='built_requires_native_acceptance' and build['error'] is None,'native Escape build failed')
    for row in build['products']:require(sha(Path(row['path']))==row['sha256'],'native Escape module changed')
    require(assets['status']=='passed' and assets['error'] is None and len(assets['assets'])==5,'all four HUD shells and shared Set required')
    for row in assets['assets']:require(sha(stage/row['relative'])==sha(overlay/row['relative'])==row['sha256'],'Escape layout resource changed')
    for row in load(root/'Build01/SourcePatch/summary.json')['sources']:
        require(sha(Path(row['original']))==row['original_sha256'] and sha(Path(row['path']))==row['patched_sha256'],'official/staged HUD source changed')
    patch_format=load(root/'PatchFormat01/summary.json')
    require(patch_format['status']=='passed' and patch_format['format_only'] and not patch_format['native_source_or_binary_changed'] and patch_format['git_apply_check_and_application_passed'],'review patch reproduction failed')
    require(sha(Path(patch_format['patch']))==patch_format['patch_sha256'] and sha(Path(patch_format['previous_patch']))==patch_format['previous_patch_sha256']==load(root/'Build01/SourcePatch/summary.json')['patch']['sha256'],'historical/final patch fingerprint differs')
    for row in patch_format['sources']:require(sha(stage/row['relative'])==row['compiled_source_sha256']==row['applied_sha256'],'review patch does not reproduce the compiled source')
    return build,assets,plan,stage


def collect(root,runtime,output):
    root,output=root.resolve(),output.resolve();runtime=root/runtime
    require(not output.exists(),'fresh Escape ledger required')
    build,assets,plan,stage=verify_setup(root)
    require(load(runtime/'summary.json')['status']=='passed','closed actual Escape window lane failed')
    actions=load(runtime/'ui-actions.json');rules=validate(load(runtime/'runtime.json'),actions)
    require(actions['rendered_ui_window_and_menu_observed'],'actual UI window/Menu pixels were not observed')
    require(sha(SCRIPTS/'uep_lyra_native/escape_menu.py')==sha(runtime/'Inputs/Overlay/Content/Scripts/uep_lyra_native/escape_menu.py'),'Escape policy changed after execution')
    result=dict(schema_version=1,status='accepted',batch='CPP09',candidates=['CPP-015'],target='UE5.8.1 / CPython3.11 / Win64 Development',policy_events=1,asset_family_count=5,
        native_python_actual_escape_and_ui_input=rules,actual_os_keyboard_events_via_computer_use=True,visible_ui_window_and_menu_observed=True,isolated_common_ui_worlds=True,full_shooter_scene_rendering_acceptance=False,
        all_four_original_hud_layout_defaults_graphs_visual_trees_and_inheritance_preserved=True,native_common_ui_action_binding_streamed_loading_input_and_lifetime_ownership_preserved=True,
        native_menu_layer_class_owner_input_mode_and_cleanup_verified=True,native_hud_destruct_and_rebuild_across_two_level_travels=True,
        compiled_unity_units=plan['compiled_unity_units'],reused_unity_units=plan['reused_unity_units'],review_patch_reproduces_compiled_sources=True,patch_eof_format_only_repair=True,
        official_reference_unchanged=True,engine_full_compile_executed=False,cook_package_executed=False,new_platform_acceptance=False,full_cpp_migration_acceptance=False,
        retained_attempts=['Runtime01','Runtime02','Runtime03'],retained_notes=['The unchanged NS_WeaponFire_MuzzleFlash_Rifle asset hit NiagaraEditor graph pin assertions during uncooked shooter-level rendering before Python/UI validation initialized. Its official/Full-stage/CPP-stage SHA256 is DC29A749455F4FB4198F3BAE014EE182F75DC9459BF234BC11CB9B5C893720CB. This batch uses isolated UI worlds, the original game instance/UI policy, original HUD layouts, native Menu layers and real OS Escape input; no shooter/Niagara rendering repair is claimed.', 'Runtime02 rendered the isolated world and found the fixture used a guessed Game_Stack name; the original layout and its existing policy name the stack GameLayer_Stack.', 'Runtime03 reached actual-input step one, but Windows was locked (LockApp and LogonUI active). No Escape input was sent. Only its identified test process was stopped; operator-stop.json records the external prerequisite.'],
        evidence=[evidence(root/'Build01/summary.json'),evidence(root/'Assets01/summary.json'),evidence(root/'Fixtures01/summary.json'),evidence(root/'PatchFormat01/summary.json'),evidence(runtime/'summary.json'),evidence(runtime/'ui-actions.json')])
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');return dict(status='accepted',batch='CPP09',candidates=1,ledger=str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--runtime',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(collect(a.root,a.runtime,a.output),indent=2))
