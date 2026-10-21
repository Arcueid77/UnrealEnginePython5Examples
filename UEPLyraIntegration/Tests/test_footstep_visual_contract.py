import hashlib
import struct
import tempfile
from pathlib import Path
import unittest
from test_footstep_locomotion_contract import report as locomotion_report
from uep_lyra_weapons.footstep_visual_contract import validate


class FootstepVisualContractTests(unittest.TestCase):
    def make_report(self, directory, role='client'):
        value = locomotion_report(role)
        value.update(images=[], visual_inspection_completed=False, original_view_target_restored=True, effect_render_visibility_restored=True)
        if role == 'client':
            for kind in ('before', 'after', 'effect-hidden', 'effect-restored'):
                file = Path(directory)/(kind+'.png')
                data = b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+struct.pack('>II', 1024, 768)+b'fixture-header-only'
                file.write_bytes(data)
                value['images'].append(dict(kind=kind, path=str(file), sha256=hashlib.sha256(data).hexdigest(),
                    successful_footsteps_at_capture=int(kind == 'after'), projected_hits_in_view=int(kind == 'after')))
        return value

    def test_captured_pair_is_not_visual_content_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validate(self.make_report(directory))
            self.assertFalse(result['visual_inspection_completed'])
            self.assertEqual(result['native_images'], 4)

    def test_changed_image_or_missing_render_pair_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.make_report(directory);Path(value['images'][0]['path']).write_bytes(b'changed')
            with self.assertRaises(RuntimeError):
                validate(value)
            value = self.make_report(directory);value['images'].pop()
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_screenshot_without_associated_visible_hit_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            value = self.make_report(directory);value['images'][1]['projected_hits_in_view'] = 0
            with self.assertRaises(RuntimeError):
                validate(value)

    def test_unrestored_camera_or_self_certified_visual_claim_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for key, replacement in (('original_view_target_restored', False), ('visual_inspection_completed', True)):
                value = self.make_report(directory);value[key] = replacement
                with self.assertRaises(RuntimeError):
                    validate(value)

    def test_server_without_screenshots_remains_capture_only(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate(self.make_report(directory, 'server'))['native_images'], 0)
