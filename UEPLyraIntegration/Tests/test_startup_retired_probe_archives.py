import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
from audit_playable_startup_acceptance import frozen_startup_input


class RetiredStartupProbeTests(unittest.TestCase):
    def fixture(self,root,name='uep_lyra_abilities/autoreload_validation.py'):
        path=root/'Demos/UEPLyraIntegration/Overlay/Content/Scripts'/name
        path.parent.mkdir(parents=True);path.write_bytes(b'new probe\n')
        archive=root/'.build/recovered.py';archive.parent.mkdir();archive.write_bytes(b'old probe\n')
        row=dict(path=str(path),sha256=hashlib.sha256(archive.read_bytes()).hexdigest().upper())
        return path,archive,row

    def test_exact_retired_unselected_probe_bytes_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,archive,row=self.fixture(root)
            with self.assertRaises(ValueError):frozen_startup_input(row,root,None)
            result=frozen_startup_input(row,root,{str(path.resolve()):str(archive)})
            self.assertEqual(result['recorded_sha256'],row['sha256'])
            archive.write_bytes(b'wrong\n')
            with self.assertRaises(ValueError):frozen_startup_input(row,root,{str(path.resolve()):str(archive)})

    def test_production_source_cannot_use_a_retired_probe_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,archive,row=self.fixture(root,'uep_lyra_hud/bootstrap.py')
            with self.assertRaises(ValueError):frozen_startup_input(row,root,{str(path.resolve()):str(archive)})

    def test_current_exact_bytes_need_no_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,archive,row=self.fixture(root)
            path.write_bytes(archive.read_bytes())
            self.assertIsNone(frozen_startup_input(row,root,None))


if __name__=='__main__':unittest.main()
