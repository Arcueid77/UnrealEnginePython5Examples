import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import audit_weapon_example_acceptance as audit
from audit_migration_acceptance import attach_weapon_example_review


def sources():
    return {m:'\n'.join('value.call_function('+repr(n)+')' for n in sorted(names)) for m,names in audit.CALLS.items()}


class WeaponExampleAcceptanceTests(unittest.TestCase):
    def test_sampler_cannot_gain_ammo_writes_or_dynamic_native_calls(self):
        audit.presenter_calls(sources())
        for extra in ('item.call_function("AddStatTagStack")','item.set_property("Ammo",0)',
                      'item.call_function(variable)'):
            values=sources();values['weapon_observer']+='\n'+extra
            with self.subTest(extra=extra),self.assertRaises(ValueError):audit.presenter_calls(values)

    def test_reload_input_boundary_cannot_become_server_mutation(self):
        values=sources();values['ammo_mixin']=values['ammo_mixin'].replace('InjectInputVectorForAction','ServerReload')
        with self.assertRaises(ValueError):audit.presenter_calls(values)

    def test_actual_package_identity_requires_current_native_binary(self):
        path=Path(tempfile.gettempdir())/'Package/LyraGame.exe'
        summary=dict(status='passed',packaged_runtime=True,cpp_compile_executed=False,cook_package_executed=False,
            process=dict(executable=str(path),pid=10,exit_code=0,arguments=['-basedir='+str(path.parent)]))
        payload=dict(status='passed',base_archive_unchanged=True,reused_cooked_candidates=246,reused_overlay_assets=460,
            reused_runtime_maps=12,packaged_executable=str(path),current_executable_sha256='A'*64)
        build=dict(status='passed',no_engine_changes_requested=True,process={'exit_code':0},products=[dict(path=str(path),sha256='A'*64)])
        audit.package_identity(summary,payload,build)
        for change in ('exit','editor','old_binary','missing_asset','no_basedir'):
            s,p,b=copy.deepcopy((summary,payload,build))
            if change=='exit':s['process']['exit_code']=1
            elif change=='editor':s['process']['executable']=str(path.with_name('UnrealEditor.exe'))
            elif change=='old_binary':p['current_executable_sha256']='B'*64
            elif change=='missing_asset':p['reused_cooked_candidates']=245
            else:s['process']['arguments']=[]
            with self.subTest(change=change),self.assertRaises(ValueError):audit.package_identity(s,p,b)

    def test_screenshot_status_cannot_promote_partial_or_full_visual_claim(self):
        images=[dict(paired_ammo_text=True,three_counter_styles_visible=True,shader_preparation_overlay_absent=True)]
        document=dict(status='reviewed',pixel_diff_executed=False,full_visual_acceptance=False,images=images)
        audit.visual_gate(document,images)
        for field in ('three_counter_styles_visible','shader_preparation_overlay_absent'):
            changed=copy.deepcopy(document);changed['images'][0][field]=False
            with self.assertRaises(ValueError):audit.visual_gate(changed,changed['images'])
        document['full_visual_acceptance']=True
        with self.assertRaises(ValueError):audit.visual_gate(document,images)

    def test_attachment_accepts_only_exact_original_weapon_example_criterion(self):
        report=dict(requirements=[dict(version='0.9.0',text=audit.REQUIREMENT,completion_proven=False),
            dict(version='0.9.0',text='Batch1A visual',completion_proven=False)],inputs=[])
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'proof.json';path.write_text('{}')
            with patch.object(audit,'verify_documentation',return_value={'status':'passed'}):
                attach_weapon_example_review(report,{}, {},directory,path)
            self.assertTrue(report['requirements'][0]['completion_proven'])
            self.assertFalse(report['requirements'][1]['completion_proven'])
            report['requirements'][0]['version']='0.14.0'
            with patch.object(audit,'verify_documentation',return_value={}),self.assertRaises(ValueError):
                attach_weapon_example_review(report,{}, {},directory,path)

    def test_recorded_claim_requires_matching_live_reinspection(self):
        expected=dict(status='passed',criterion=audit.REQUIREMENT,current_packaged_executable_sha256='A'*64,
            paired_state_comparisons_per_runtime=38,weapon_scenarios_per_runtime=42,native_gameplay_authority_retained=True)
        document=dict(criterion=audit.REQUIREMENT,completion_proven=True,review=expected)
        with patch.object(audit,'inspect',return_value=expected):
            audit.verify_documentation(document,{}, {},'.')
            altered=copy.deepcopy(document);altered['review']['current_packaged_executable_sha256']='B'*64
            with self.assertRaises(ValueError):audit.verify_documentation(altered,{}, {},'.')


if __name__=='__main__':unittest.main()
