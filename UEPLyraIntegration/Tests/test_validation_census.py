from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts"))
from uep_lyra_hud.validation_census import UniqueWidgetCensus


class NativeCensus(unittest.TestCase):
    def test_no_acceptance_until_native_membership_is_unique(self):
        census = UniqueWidgetCensus()
        self.assertFalse(census.ready(["old", "new"], "world", 0.0))
        self.assertFalse(census.ready(["old", "new"], "world", .1))
        self.assertTrue(census.ready(["new"], "world", .2))
        self.assertFalse(census.ready([], "world", .3))

    def test_persistent_duplicates_fail_even_if_names_change(self):
        census = UniqueWidgetCensus()
        for index in range(3):
            self.assertFalse(census.ready(["old", "new"+str(index)], "world", index))
        with self.assertRaisesRegex(RuntimeError, "persistent duplicate"):
            census.ready(["other", "another"], "world", 3.0)

    def test_long_asset_pause_is_not_four_duplicate_observations(self):
        census = UniqueWidgetCensus()
        self.assertFalse(census.ready(["old", "new"], "world", 0.0))
        self.assertFalse(census.ready(["old", "new"], "world", 30.0))
        self.assertTrue(census.ready(["new"], "world", 30.1))

    def test_new_world_starts_its_own_bounded_transition(self):
        census = UniqueWidgetCensus()
        self.assertFalse(census.ready(["old", "new"], "world1", 0.0))
        self.assertFalse(census.ready(["old", "new"], "world2", 30.0))
