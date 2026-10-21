import importlib.util
import io
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('migration_container', Path(__file__).resolve().parents[1]/'Tools/inspect_migration_container.py')
container = importlib.util.module_from_spec(spec)
spec.loader.exec_module(container)


class MigrationContainerTests(unittest.TestCase):
    def plan(self):
        asset = dict(relative_path='Plugins/GameFeatures/ShooterCore/Content/Game/B_Test.uasset')
        return dict(status='passed', project_name='Lyra', static_scope=[246, 182, 63, 11], candidate_assets=[asset],
                    accepted_overlay_assets=[asset], runtime_maps=[dict(relative_path='Content/Maps/Main.umap')])

    def listing(self, rows):
        return io.StringIO('Filename, ChunkType, Size\n'+rows)

    def test_actual_feature_and_project_packages_close_presence_only(self):
        report = container.inspect(self.plan(), self.listing('../../../Lyra/Plugins/GameFeatures/ShooterCore/Content/Game/B_Test.uasset, ExportBundleData, 20\n../../../Lyra/Content/Maps/Main.umap, ExportBundleData, 10\n'))
        self.assertEqual(report['status'], 'passed')
        self.assertFalse(report['runtime_acceptance'])
        self.assertFalse(report['full_acceptance'])

    def test_bulk_data_cannot_stand_in_for_a_missing_package(self):
        report = container.inspect(self.plan(), self.listing('../../../Lyra/Plugins/GameFeatures/ShooterCore/Content/Game/B_Test.uasset, BulkData, 20\n../../../Lyra/Content/Maps/Main.umap, ExportBundleData, 10\n'))
        self.assertEqual(report['status'], 'review_required')
        self.assertEqual(report['coverage']['candidate_assets']['present'], 0)
        self.assertEqual(len(report['coverage']['overlay_assets']['missing']), 1)

    def test_other_plugin_with_same_tail_does_not_cover_feature_asset(self):
        report = container.inspect(self.plan(), self.listing('../../../Lyra/Plugins/Other/Content/Game/B_Test.uasset, ExportBundleData, 20\n../../../Lyra/Content/Maps/Main.umap, ExportBundleData, 10\n'))
        self.assertEqual(report['coverage']['candidate_assets']['present'], 0)

    def test_empty_or_incompatible_listing_is_rejected(self):
        for data in ('', 'Filename,Other\nA,B\n', 'Filename, ChunkType, Size\n'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                container.inspect(self.plan(), io.StringIO(data))

    def test_engine_content_cannot_cover_project_map(self):
        report = container.inspect(self.plan(), self.listing('../../../Lyra/Plugins/GameFeatures/ShooterCore/Content/Game/B_Test.uasset, ExportBundleData, 20\n../../../Engine/Content/Maps/Main.umap, ExportBundleData, 10\n'))
        self.assertEqual(report['coverage']['runtime_maps']['present'], 0)

    def test_changed_original_scope_is_rejected(self):
        plan = self.plan();plan['static_scope'][0] = 245
        with self.assertRaises(ValueError):container.inspect(plan, self.listing(''))
