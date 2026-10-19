"""Reject callback replay, lost native weak targets and profile-switch leaks."""
import unittest
from uep_lyra_weapons import weapon_actor_begin_contract as policy


def report():
    data=dict(status="passed",error=None,native_mode="Standalone",cases=[],observation_errors=[],original_team_restored=True,original_pawn_health_unchanged=True,
        test_actors_destroyed=True,test_owned_proxies_cancelled=True,production_profiles_restored=True,original_active_proxies_preserved=True)
    data.update({key:False for key in ("full_acceptance","network_acceptance","packaged_runtime","health_properties_written","begin_play_replayed","team_callback_replayed","python_callback_retained","production_proxy_cancelled_by_script")})
    for cls in policy.CLASSES:
        for profile in policy.PROFILES:
            for owner in policy.OWNERS:
                other="Python" if profile=="BlueprintFallback" else "BlueprintFallback"
                events=[dict(profile=other if index==2 else profile,team=team,assigned=True,stencil_delta=1,color_delta=1) for index,team in enumerate((1,2,1,2))] if owner=="pawn" else [dict(profile=profile,team=-1,assigned=False,stencil_delta=0,color_delta=0)] if owner=="unassigned-pawn" else []
                data["cases"].append(dict(**{"class":cls},profile=profile,owner=owner,actual_native_begin_count=1,actor_destroyed=True,
                    native_proxies_added=int(owner in ("pawn","unassigned-pawn")),events=events,owner_field_is_null=owner in ("none","actor"),owner_matches=owner in ("pawn","unassigned-pawn"),proxy_inactive_after_initial_broadcast=True,
                    proxy_active_after_actor_destroy=True,no_dead_actor_callbacks=True,profile_switch_did_not_create_proxy=True,original_team=1,other_team=2,other_profile=other))
    return data


class TestWeaponActorBeginContract(unittest.TestCase):
    def setUp(self):self.data=report()
    def rejected(self):
        with self.assertRaises(RuntimeError):policy.validate(self.data)
    def test_full_native_matrix(self):self.assertEqual(policy.validate(self.data)["actual_native_weapon_begins"],24)
    def test_begin_replayed(self):self.data["begin_play_replayed"]=True;self.rejected()
    def test_callback_replayed(self):self.data["team_callback_replayed"]=True;self.rejected()
    def test_null_owner_creates_proxy(self):self.data["cases"][2]["native_proxies_added"]=1;self.rejected()
    def test_initial_native_notification_missing(self):self.data["cases"][0]["events"].pop(0);self.rejected()
    def test_no_team_runs_business(self):self.data["cases"][1]["events"][0]["stencil_delta"]=1;self.rejected()
    def test_profile_switch_loses_current_dispatch(self):self.data["cases"][0]["events"][2]["profile"]="BlueprintFallback";self.rejected()
    def test_profile_switch_creates_duplicate_proxy(self):self.data["cases"][0]["profile_switch_did_not_create_proxy"]=False;self.rejected()
    def test_destroyed_actor_still_receives_events(self):self.data["cases"][0]["no_dead_actor_callbacks"]=False;self.rejected()
    def test_production_script_changes_native_proxy_lifetime(self):self.data["production_proxy_cancelled_by_script"]=True;self.rejected()
    def test_test_proxy_leaks(self):self.data["test_owned_proxies_cancelled"]=False;self.rejected()
    def test_original_team_not_restored(self):self.data["original_team_restored"]=False;self.rejected()
    def test_existing_game_proxy_cancelled(self):self.data["original_active_proxies_preserved"]=False;self.rejected()
