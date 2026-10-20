"""Test the startup selector without importing UE or launching a client."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Overlay" / "Content" / "Scripts"))
from uep_lyra_hud.startup import validation_module


class StartupSelectionTests(unittest.TestCase):
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
