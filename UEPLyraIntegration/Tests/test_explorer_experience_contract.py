"""Reject forged scope, missing native UI/input, and unequal Experience grants."""
import unittest
from uep_lyra_characters import explorer_experience_contract as contract
from uep_lyra_hud.startup import validation_module


def report(profile='Python'):
    cases=[]
    for profile in (profile,):
        python=profile=='Python'
        menus=[dict(kind=kind,native_layer='UI.Layer.GameMenu',native_widgets=1,native_active_widget_observed=True,native_removed=True,
            callback_deltas=[dict(python=int(python),fallback=int(not python))]) for kind in ('inventory','map')]
        cases.append(dict(profile=profile,world=contract.MAP+'.L_InventoryTestMap',pawn_class='/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C',
            experience='/ShooterExplorer/System/Experiences/B_TestInventoryExperience.Default__B_TestInventoryExperience_C',visible=True,health=100.,native_role=3,input_subsystem_used=True,
            initial_inventory=[dict(definition='original-rifle',count=1)],inventory_preserved=True,natural_begin=dict(python_calls=int(python),fallback_calls=int(not python)),
            movement=dict(input_frames=24,distance_squared=144.),menus=menus,granted_abilities=['original-Interact','original-Inventory']))
    value=dict(status='passed',error=None,selectors_restored=True,actual_exit_finalizer=True,old_profile_pawns_and_controllers_destroyed=True,native_level_open_requests=1,selected_profile=profile,
        selected_class_paths=['/ShooterExplorer/Blueprint/B_Hero_Explorer.B_Hero_Explorer_C'],cases=cases)
    value.update(dict.fromkeys(contract.FALSE_FIELDS,False));return value


class ExplorerExperienceContractTests(unittest.TestCase):
    def test_complete_bounded_semantic_envelope(self):
        value=report();self.assertIs(contract.validate(value),value)
    def test_each_scope_overclaim_is_rejected(self):
        for key in contract.FALSE_FIELDS:
            with self.subTest(key=key):
                value=report();value[key]=True
                with self.assertRaises(ValueError):contract.validate(value)
    def test_travel_and_actual_exit_cleanup_are_required(self):
        for key in ('selectors_restored','actual_exit_finalizer','old_profile_pawns_and_controllers_destroyed'):
            with self.subTest(key=key):
                value=report();value[key]=False
                with self.assertRaises(ValueError):contract.validate(value)
        value=report();value['native_level_open_requests']=0
        with self.assertRaises(ValueError):contract.validate(value)
    def test_temporary_shooter_fixture_does_not_prove_explorer_experience(self):
        value=report();value['cases'][0]['world']='/ShooterMaps/Maps/L_Expanse.L_Expanse'
        with self.assertRaises(ValueError):contract.validate(value)
    def test_fallback_or_missing_native_movement_is_rejected(self):
        for key,change in (('natural_begin',dict(python_calls=1,fallback_calls=1)),('movement',dict(input_frames=24,distance_squared=0.))):
            value=report();value['cases'][0][key]=change
            with self.assertRaises(ValueError):contract.validate(value)
    def test_actual_ui_layer_and_selected_deactivation_are_required(self):
        for change in (dict(native_layer='UI.Layer.Menu'),dict(native_widgets=0),dict(native_removed=False),dict(callback_deltas=[dict(python=0,fallback=1)])):
            value=report();value['cases'][0]['menus'][0].update(change)
            with self.assertRaises(ValueError):contract.validate(value)
    def test_native_grants_and_inventory_must_match(self):
        for key in ('initial_inventory','granted_abilities'):
            values=[report(profile) for profile in contract.PROFILES];values[1]['cases'][0][key]=['different-native-grant']
            with self.assertRaises(ValueError):contract.validate_pair(values)
    def test_pair_requires_distinct_complete_profile_process_reports(self):
        values=[report(profile) for profile in contract.PROFILES]
        self.assertIs(contract.validate_pair(values),values)
        for changed in ([values[0]], [values[1],values[0]], [values[1],values[1]]):
            with self.assertRaises(ValueError):contract.validate_pair(changed)
    def test_only_explicit_playable_flag_selects_probe(self):
        self.assertIsNone(validation_module([]))
        self.assertIsNone(validation_module(['-run=Py','-UEPExplorerExperienceResult=result.json']))
        self.assertEqual(validation_module(['-UEPExplorerExperienceResult=result.json']),'uep_lyra_characters.explorer_experience_validation')


if __name__=='__main__':unittest.main()
