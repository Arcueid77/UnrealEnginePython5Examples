"""Native BeginPlay fixture guards; synthetic shape is never runtime acceptance."""
import unittest
import test_character_visibility_contract as visibility_models
from uep_lyra_characters.begin_play_contract import validate, CLASS, P


def counters(py=True):
    return dict(python_calls=int(py), fallback_calls=int(not py), parent_calls=int(py), listen_calls=int(py), hide_calls=int(py), register_calls=int(py), order=["parent", "listen", "hide", "register"] if py else [])


def upgrade(value): value.update(begin_play_business_migrated=True, begin_play_manually_replayed=False, ancestor_construction_death_business_migrated=False); return value


def report():
    value = upgrade(visibility_models.report()); value.update(natural_startup_begin_play=counters(), begin_play_cases=[])
    for name in ("pending", "ready"):
        for profile in ("BlueprintFallback", "Python"):
            py = profile == "Python"
            value["begin_play_cases"].append(dict(name=name, profile=profile, native_character_class=CLASS, begin_play_counters=counters(py), actual_native_new_actor_begin_play=True,
                fixture_cdo_profile_temporarily_overridden_for_spawn=True, cdo_profile_restored_immediately=True, cdo_profile_still_restored=True,
                actor_was_not_rooted=True, owned_new_pawn_destroyed=True, no_late_script_work_after_owned_destruction=True, owned_team_observers_collected=True,
                original_active_proxies_preserved=True, begin_play_quiet_after_destroy=True, begin_play_manually_replayed=False,
                cleanup=dict(owned_pawn_controller_playerstate_producer_destroyed=True, original_bot_producer_list_preserved=True),
                listener_counters=dict(python_calls=int(py), fallback_calls=int(not py), factories=int(py), binds=int(py), activations=int(py)),
                native_hidden=name == "pending", visibility_counters=visibility_models.evidence(py=py) if name == "ready" else dict(python_calls=0, fallback_calls=0),
                native_inventory_model=dict(items=[P], slots=[P, None, None]) if name == "ready" else None))
    return value


class CharacterBeginPlayReportModels(unittest.TestCase):
    def setUp(self): self.report = report()
    def reject(self):
        with self.assertRaises((RuntimeError, AssertionError, ValueError)): validate(self.report)
    def test_complete_shape_is_model(self): self.assertEqual(validate(self.report)["native_begin_play_pairs"], 2)
    def test_no_begin_play_replay(self): self.report["begin_play_manually_replayed"] = True; self.reject()
    def test_exact_order(self): self.report["begin_play_cases"][1]["begin_play_counters"]["order"].reverse(); self.reject()
    def test_native_entry_required(self): self.report["begin_play_cases"][0]["actual_native_new_actor_begin_play"] = False; self.reject()
    def test_cdo_must_restore_immediately(self): self.report["begin_play_cases"][0]["cdo_profile_restored_immediately"] = False; self.reject()
    def test_cdo_must_stay_restored(self): self.report["begin_play_cases"][3]["cdo_profile_still_restored"] = False; self.reject()
    def test_pending_stays_hidden(self): self.report["begin_play_cases"][1]["native_hidden"] = False; self.reject()
    def test_ready_shown(self): self.report["begin_play_cases"][3]["native_hidden"] = True; self.reject()
    def test_no_double_listener(self): self.report["begin_play_cases"][1]["listener_counters"]["factories"] = 2; self.reject()
    def test_previous_native_visibility_regression_required(self): self.report["visibility_cases"][1]["hidden_before_resume"] = False; self.reject()
    def test_private_selector(self):
        from uep_lyra_hud.startup import validation_module
        self.assertEqual(validation_module(["-UEPCharacterBeginPlayResult=x"]), "uep_lyra_characters.begin_play_validation")
