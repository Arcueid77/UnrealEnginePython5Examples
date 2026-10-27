import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Tools'))
import prepare_current_runtime_package as prepare


class CurrentRuntimePackageTests(unittest.TestCase):
    def test_owned_path_rejects_root_and_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(prepare.inside(root/'owned',root),root/'owned')
            for path in (root,root.parent/'outside',root/'inside/../../outside'):
                with self.assertRaises(ValueError):prepare.inside(path,root)

    def test_changed_product_cannot_reuse_accepted_status(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'pakchunk.ucas';file.write_bytes(b'cooked')
            row=dict(path=str(file),sha256=prepare.sha(file).lower())
            prepare.verify_rows([row]);file.write_bytes(b'changed')
            with self.assertRaises(ValueError):prepare.verify_rows([row])
            with self.assertRaises(ValueError):prepare.verify_rows([])

    def test_changed_asset_requires_recook_and_candidate_path_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory);file=stage/'Content/Asset.uasset';file.parent.mkdir();file.write_bytes(b'original')
            row=dict(relative_path='Content/Asset.uasset',stage=str(file),sha256=prepare.sha(file))
            plan=dict(candidate_assets=[dict(row) for _ in range(246)],
                accepted_overlay_assets=[dict(row) for _ in range(460)],runtime_maps=[dict(row) for _ in range(12)])
            self.assertEqual(len(prepare.asset_rows(plan,stage)),718)
            plan['candidate_assets'][0]['relative_path']='../outside.uasset'
            with self.assertRaises(ValueError):prepare.asset_rows(plan,stage)
            plan['candidate_assets'][0]=dict(row);file.write_bytes(b'new asset')
            with self.assertRaises(ValueError):prepare.asset_rows(plan,stage)

    def test_partial_inventory_cannot_be_called_original_content(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):prepare.asset_rows(dict(candidate_assets=[],accepted_overlay_assets=[],runtime_maps=[]),Path(directory))

    def test_existing_destination_is_rejected_without_touching_it(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);stage=repo/'.build/Stage';stage.mkdir(parents=True)
            (stage/'.uep-lyra-full-stage.json').write_text('{}')
            output=repo/'.build/Output';output.mkdir();sentinel=output/'keep';sentinel.write_bytes(b'preserve')
            with self.assertRaises(ValueError):prepare.prepare(repo,stage,repo/'.build/Cook',repo/'.build/Game',output)
            self.assertEqual(sentinel.read_bytes(),b'preserve')

    def test_failed_native_build_is_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory);owned=repo/'.build';stage=owned/'Stage';stage.mkdir(parents=True)
            (stage/'.uep-lyra-full-stage.json').write_text('{}')
            cook=owned/'Cook';cook.mkdir();game=owned/'Game';game.mkdir()
            (cook/'summary.json').write_text(json.dumps(dict(status='passed',scope='current-original-migration-content-cook-package',process={'exit_code':0})))
            (game/'summary.json').write_text(json.dumps(dict(status='failed')))
            output=owned/'Output'
            with self.assertRaises(ValueError):prepare.prepare(repo,stage,cook,game,output)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
