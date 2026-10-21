"""Test the startup selector without importing UE or launching a client."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"))
from uep_lyra_hud.startup import validation_module


class StartupSelectionTests(unittest.TestCase):
    def test_hero_parent_equipment_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPHeroParentEquipmentResult=report.json']),'uep_lyra_characters.hero_default_equipment_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPHeroParentEquipmentResult=report.json']))

    def test_hero_parent_stencil_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPHeroParentStencilResult=report.json']),'uep_lyra_characters.hero_default_stencil_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPHeroParentStencilResult=report.json']))

    def test_retained_explorer_shells_require_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerShellsResult=report.json']),'uep_lyra_characters.explorer_shells_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerShellsResult=report.json']))

    def test_explorer_marker_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerMarkerResult=report.json']),'uep_lyra_abilities.explorer_marker_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerMarkerResult=report.json']))

    def test_collect_cue_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPCollectCueResult=report.json']),'uep_lyra_weapons.collect_cue_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPCollectCueResult=report.json']))

    def test_explorer_actions_require_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerActionsResult=report.json']),'uep_lyra_abilities.explorer_actions_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerActionsResult=report.json']))

    def test_explorer_interact_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerInteractResult=report.json']),'uep_lyra_abilities.explorer_interact_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerInteractResult=report.json']))

    def test_explorer_item_list_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerItemListResult=report.json']),'uep_lyra_hud.explorer_item_list_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerItemListResult=report.json']))

    def test_explorer_toast_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerToastResult=report.json']),'uep_lyra_hud.explorer_toast_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerToastResult=report.json']))

    def test_explorer_grid_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerGridResult=report.json']),'uep_lyra_hud.explorer_grid_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerGridResult=report.json']))

    def test_explorer_screens_require_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerScreensResult=report.json']),'uep_lyra_hud.explorer_screens_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerScreensResult=report.json']))

    def test_explorer_behavior_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerBehaviorResult=report.json']),'uep_lyra_characters.explorer_behavior_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerBehaviorResult=report.json']))

    def test_explorer_input_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerInputResult=report.json']),'uep_lyra_characters.explorer_input_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerInputResult=report.json']))

    def test_explorer_beginplay_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerBeginPlayResult=report.json']),'uep_lyra_characters.explorer_beginplay_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerBeginPlayResult=report.json']))

    def test_explorer_init_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerInitResult=report.json']),'uep_lyra_characters.explorer_init_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerInitResult=report.json']))

    def test_explorer_callbacks_require_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerCallbacksResult=report.json']),'uep_lyra_characters.explorer_callbacks_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerCallbacksResult=report.json']))

    def test_explorer_style_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerStyleResult=report.json']),'uep_lyra_characters.explorer_style_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerStyleResult=report.json']))

    def test_explorer_helpers_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerHelpersResult=report.json']),'uep_lyra_characters.explorer_helpers_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerHelpersResult=report.json']))

    def test_explorer_state_requires_explicit_native_lane(self):
        self.assertEqual(validation_module(['-UEPExplorerStateResult=report.json']),'uep_lyra_world.explorer_state_validation')
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerStateResult=report.json']))
        self.assertIsNone(validation_module(['LyraStarterGame.uproject','-game']))

    def test_autoreload_lane_is_explicit_and_skips_commandlets(self):
        self.assertEqual(validation_module(["-UEPWeaponInstanceResult=report.json"]), "uep_lyra_weapons.weapon_instance_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPWeaponInstanceResult=report.json"]))
        self.assertEqual(validation_module(["-UEPReloadMagazineNetworkResult=report.json"]), "uep_lyra_abilities.reload_magazine_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPReloadMagazineNetworkResult=report.json"]))
        self.assertEqual(validation_module(["-UEPReloadMagazineResult=report.json"]), "uep_lyra_abilities.reload_magazine_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPReloadMagazineResult=report.json"]))
        self.assertEqual(validation_module(["-UEPAutoReloadResult=report.json"]), "uep_lyra_abilities.autoreload_validation")
        self.assertEqual(validation_module(["-UEPHeroHealResult=report.json"]), "uep_lyra_abilities.hero_heal_validation")
        self.assertEqual(validation_module(["-UEPADSResult=report.json"]), "uep_lyra_abilities.ads_validation")
        self.assertEqual(validation_module(["-UEPDropWeaponResult=report.json"]), "uep_lyra_abilities.drop_weapon_validation")
        self.assertEqual(validation_module(["-UEPDropWeaponNetworkResult=report.json"]), "uep_lyra_abilities.drop_weapon_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPDropWeaponNetworkResult=report.json"]))
        self.assertIsNone(validation_module(["-run=Py", "-UEPDropWeaponResult=report.json"]))
        self.assertEqual(validation_module(["-UEPADSNetworkResult=report.json"]), "uep_lyra_abilities.ads_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPADSNetworkResult=report.json"]))
        self.assertIsNone(validation_module(["-run=Py", "-UEPADSResult=report.json"]))
        self.assertEqual(validation_module(["-UEPHeroHealNetworkResult=report.json"]), "uep_lyra_abilities.hero_heal_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPHeroHealNetworkResult=report.json"]))
        self.assertIsNone(validation_module(["-run=Py", "-UEPHeroHealResult=report.json"]))
        self.assertEqual(validation_module(["-UEPAutoReloadNetworkResult=report.json"]), "uep_lyra_abilities.autoreload_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPAutoReloadNetworkResult=report.json"]))
        self.assertIsNone(validation_module(["-run=Py", "-UEPAutoReloadResult=report.json"]))

    def test_cosmetic_lane_requires_explicit_flag_and_skips_commandlets(self):
        self.assertEqual(validation_module(["-UEPCosmeticResult=report.json"]), "uep_lyra_characters.cosmetic_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCosmeticResult=report.json"]))
        self.assertEqual(validation_module(["-UEPCosmeticNetworkResult=report.json"]), "uep_lyra_characters.cosmetic_network_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPCosmeticNetworkResult=report.json"]))

    def test_original_interaction_inspection_requires_explicit_flag(self):
        self.assertEqual(validation_module(["-UEPInteractionInspectionResult=report.json"]),
                         "uep_lyra_world.interaction_inspection")
        self.assertIsNone(validation_module(["-run=Py", "-UEPInteractionInspectionResult=report.json"]))
        self.assertEqual(validation_module(["-UEPInteractionInspectionResult=report.json", "-UEPInteractionProducer"]),
                         "uep_lyra_world.interaction_producer_network")

    def test_normal_play_does_not_run_a_probe(self):
        self.assertIsNone(validation_module(["LyraStarterGame.uproject", "-game"]))

    def test_teleporter_lane_is_explicit_and_commandlets_do_not_run_it(self):
        self.assertEqual(validation_module(["-UEPTeleporterResult=report.json"]), "uep_lyra_world.teleporter_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPTeleporterResult=report.json"]))

    def test_commandlets_override_all_validation_flags(self):
        self.assertIsNone(validation_module(["-run=Py", "-UEPLyraMultiClient"]))

    def test_nameplate_lane_is_explicit_and_disabled_in_commandlets(self):
        self.assertEqual(validation_module(["-UEPNameplateResult=report.json"]), "uep_lyra_hud.nameplate_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPNameplateResult=report.json"]))

    def test_nameplate_component_lane_is_explicit_and_disabled_in_commandlets(self):
        self.assertEqual(validation_module(["-UEPNameplateComponentsResult=report.json"]), "uep_lyra_hud.nameplate_components_validation")
        self.assertIsNone(validation_module(["-run=Py", "-UEPNameplateComponentsResult=report.json"]))

    def test_existing_modes_remain_explicit(self):
        self.assertEqual(validation_module(["-UEPLyraSmokeResult=report.json"]), "uep_lyra_probe")
        self.assertEqual(validation_module(["-UEPLyraMode=standalone"]), "uep_lyra_probe")
        self.assertEqual(validation_module(["-UEPLyraMultiClient"]), "uep_lyra_network")
        self.assertEqual(validation_module(["-UEPLyraHUDVisualResult=report.json"]), "uep_lyra_hud.visual_validation")
        self.assertEqual(validation_module(["-UEPLyraWeaponHUDResult=report.json"]), "uep_lyra_hud.weapon_validation")
        self.assertEqual(validation_module(["-UEPReticleAmmoResult=report.json"]), "uep_lyra_hud.reticle_validation")
        self.assertEqual(validation_module(["-UEPEffectPadResult=report.json"]), "uep_lyra_world.effect_pad_validation")
        self.assertEqual(validation_module(["-UEPEffectPadGameplayResult=report.json"]), "uep_lyra_world.effect_pad_gameplay_validation")
        self.assertEqual(validation_module(["-UEPEffectPadNetwork", "-UEPLyraMultiClient"]), "uep_lyra_world.effect_pad_network_validation")
        self.assertEqual(validation_module(["-UEPTypedMessageResult=report.json"]), "uep_lyra_hud.message_payload_validation")
        self.assertEqual(validation_module(["-UEPWeaponReticleResult=report.json"]), "uep_lyra_hud.weapon_reticle_validation")
        self.assertEqual(validation_module(["-UEPOpenMenuResult=report.json"]), "uep_lyra_hud.open_menu_validation")
        self.assertEqual(validation_module(["-UEPReticleHostResult=report.json"]), "uep_lyra_hud.reticle_host_validation")
        self.assertEqual(validation_module(["-UEPAbilityProgressResult=report.json"]), "uep_lyra_hud.ability_progress_validation")
        self.assertEqual(validation_module(["-UEPAbilityFailureResult=report.json"]), "uep_lyra_hud.ability_failure_validation")
        self.assertEqual(validation_module(["-UEPAbilityFailureResult=report.json", "-UEPAbilityFailureCulture"]), "uep_lyra_hud.ability_failure_culture_validation")
