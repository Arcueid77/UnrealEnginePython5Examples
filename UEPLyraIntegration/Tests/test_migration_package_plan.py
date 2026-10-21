import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('migration_package_plan',Path(__file__).resolve().parents[1]/'Tools/plan_migration_package.py')
plan=importlib.util.module_from_spec(spec);spec.loader.exec_module(plan)


class MigrationPackagePlanTests(unittest.TestCase):
    def test_project_and_feature_mounts_resolve_to_stage(self):
        root=Path('stage')
        self.assertEqual(plan.package_file(root,'/Game/UI/W_Test.W_Test'),root/'Content/UI/W_Test.uasset')
        self.assertEqual(plan.package_file(root,'/TopDownArena/Game/Bombs/B_Bomb_Base.B_Bomb_Base'),root/'Plugins/GameFeatures/TopDownArena/Content/Game/Bombs/B_Bomb_Base.uasset')

    def test_unknown_mount_traversal_and_wrong_object_name_are_rejected(self):
        for name in ('/Other/Thing.Thing','/Game/A/../Outside','/Game/A\\Outside.Outside','/Game/A.Else','Game/A.A'):
            with self.subTest(name=name), self.assertRaises(ValueError):plan.package_file(Path('stage'),name)

    def test_overlay_paths_preserve_virtual_mounts(self):
        self.assertEqual(plan.virtual_file(Path('Content/UEPMixins/DA_Test.uasset')),'/Game/UEPMixins/DA_Test')
        self.assertEqual(plan.virtual_file(Path('Plugins/GameFeatures/ShooterCore/Content/Game/B_Test.uasset')),'/ShooterCore/Game/B_Test')

    def test_non_content_overlay_layout_rejected(self):
        with self.assertRaises(ValueError):plan.virtual_file(Path('Other/B_Test.uasset'))

    def test_unmarked_stage_does_not_become_a_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):plan.inspect(root,root/'overlay',root/'batches.json')
