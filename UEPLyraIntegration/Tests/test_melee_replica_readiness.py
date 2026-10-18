"""Read-only snapshot models, not native initialization/replication evidence."""
import importlib
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

observation = importlib.import_module("uep_lyra_abilities.melee_replica_readiness")


class Native:
    def __init__(self, name, fields=None, calls=None): self.name,self.fields,self.calls = name,fields or {},calls or {}
    def is_valid(self): return True
    def get_path_name(self): return self.name
    def get_property(self, name): return self.fields[name]
    def call_function(self, name, *args): return self.calls[name]
    def is_a(self, cls): return self.name == "health-set"
    def get_class(self): return Native("native-character-class")
    def get_component_by_type(self, cls): return self.fields.get("extension")


class TestMeleeReplicaReadiness(unittest.TestCase):
    def setUp(self):
        data = lambda value: types.SimpleNamespace(CurrentValue=value,BaseValue=value)
        self.attributes = Native("health-set",dict(Health=data(100.),MaxHealth=data(100.)))
        self.asc = Native("asc",dict(OwnerActor=Native("state"),AvatarActor=Native("pawn"),SpawnedAttributes=[self.attributes]))
        self.health = Native("component",dict(HealthSet=self.attributes,AbilitySystemComponent=self.asc),dict(GetHealth=100.,GetMaxHealth=100.,GetDeathState=0))
        self.state = Native("state",dict(AbilitySystemComponent=self.asc),dict(GetPawn=Native("pawn")))
        self.extension = Native("extension",dict(AbilitySystemComponent=self.asc,PawnData=Native("pawn-data")),dict(GetFeatureName="PawnExtension",GetInitState=types.SimpleNamespace(TagName="InitState.GameplayReady")))
        self.pawn = Native("pawn",dict(PlayerState=self.state,extension=self.extension,NetDormancy=0,bAlwaysRelevant=False,NetCullDistanceSquared=225000000.,bHidden=False,bTearOff=False,Controller=None,InputComponent=None,PythonMixinProfile="Python"),dict(GetLocalRole=1,IsActorBeingDestroyed=False,GetComponentsByInterface=[self.extension],GetLifeSpan=0.,IsLocallyControlled=False))
        for item in (patch.object(observation,"ue",types.SimpleNamespace(find_class=lambda name:name)),
                patch.object(observation,"ability_system",lambda pawn:self.asc),patch.object(observation,"valid",lambda value:value is not None)):
            item.start(); self.addCleanup(item.stop)
    def test_bound_native_snapshot(self):
        row=observation.snapshot(self.pawn,self.health)
        self.assertEqual(row["health"],100.);self.assertEqual(row["health_asc"]["avatar"],"pawn");self.assertEqual(row["player_state_pawn"],"pawn")
    def test_missing_health_set_not_necessarily_native_death(self):
        self.health.fields.update(HealthSet=None,AbilitySystemComponent=None);self.health.calls.update(GetHealth=0.,GetMaxHealth=0.)
        row=observation.snapshot(self.pawn,self.health)
        self.assertIsNone(row["health_set"]);self.assertIsNone(row["health_asc"]);self.assertEqual(row["death_state"],0);self.assertEqual(row["player_state_asc"]["health_attributes"][0]["health"],100.)
    def test_stale_native_asc_avatar_preserved_as_evidence(self):
        self.asc.fields["AvatarActor"]=Native("another-pawn")
        self.assertEqual(observation.snapshot(self.pawn,self.health)["actor_asc"]["avatar"],"another-pawn")
    def test_unpossessed_old_pawn_is_not_current_ps_pawn(self):
        self.state.calls["GetPawn"]=Native("new-pawn")
        self.assertEqual(observation.snapshot(self.pawn,self.health)["player_state_pawn"],"new-pawn")
    def test_native_health_zero_with_bound_set_is_different(self):
        self.attributes.fields["Health"].CurrentValue=0.;self.health.calls["GetHealth"]=0.
        row=observation.snapshot(self.pawn,self.health)
        self.assertEqual(row["health"],0.);self.assertEqual(row["health_asc"]["health_attributes"][0]["health"],0.)
    def test_missing_extension_state(self):
        self.pawn.fields["extension"]=None
        row=observation.snapshot(self.pawn,self.health);self.assertIsNone(row["extension"]);self.assertIsNone(row["pawn_data"])
    def test_native_feature_state_read_not_advanced(self):
        self.extension.calls["GetInitState"].TagName="InitState.DataAvailable"
        self.assertEqual(observation.snapshot(self.pawn,self.health)["init_features"][0]["state"],"InitState.DataAvailable")
    def test_missing_hero_feature_not_invented(self):
        row=observation.snapshot(self.pawn,self.health)
        self.assertEqual([item["feature"] for item in row["init_features"]],["PawnExtension"])
    def test_reset_lifecycle_not_invented_as_native_death(self):
        self.pawn._uep_character_lifecycle=dict(reset_python=1,death_python=0)
        self.pawn.fields["bHidden"]=True
        row=observation.snapshot(self.pawn,self.health)
        self.assertEqual(row["lifecycle"]["reset_python"],1);self.assertEqual(row["death_state"],0);self.assertTrue(row["hidden"])
    def test_native_tearoff_recorded(self):
        self.pawn.fields["bTearOff"]=True
        self.assertTrue(observation.snapshot(self.pawn,self.health)["tear_off"])
    def test_inventory_wait_native_linkage_evidence_retained_as_pod(self):
        self.pawn._uep_character_inventory_wait=dict(resumes=2,stage_resumes=[0,2,0],pending=[False,True,False])
        row=observation.snapshot(self.pawn,self.health)
        self.assertEqual(row["inventory_wait"]["stage_resumes"],[0,2,0])
        self.pawn._uep_character_inventory_wait["resumes"]=3
        self.assertEqual(row["inventory_wait"]["resumes"],2)
    def test_snapshot_never_mutates_native_health_or_bindings(self):
        text=Path(observation.__file__).read_text(encoding="utf-8")
        for forbidden in ("set_property(","InitializeWithAbilitySystem","UninitializeFromAbilitySystem","SetNumericAttribute", "RemoveLooseGameplayTag"):
            self.assertTrue(forbidden not in text,forbidden)
    def test_wire_identity_clocks_do_not_turn_change_history_into_tick_history(self):
        first=dict(health=100.,network_identity=dict(valid=True,transport="Legacy",wire_id="42",world_seconds=1.,actor_age_seconds=.2))
        second=dict(health=100.,network_identity=dict(valid=True,transport="Legacy",wire_id="42",world_seconds=2.,actor_age_seconds=1.2))
        self.assertEqual(observation.change_fingerprint(first),observation.change_fingerprint(second))
        self.assertEqual(first["network_identity"]["world_seconds"],1.)
    def test_wire_or_binding_change_still_publishes(self):
        first=dict(health=100.,network_identity=dict(valid=True,wire_id="42",world_seconds=1.))
        second=dict(health=0.,network_identity=dict(valid=True,wire_id="42",world_seconds=2.))
        third=dict(health=100.,network_identity=dict(valid=True,wire_id="44",world_seconds=2.))
        self.assertNotEqual(observation.change_fingerprint(first),observation.change_fingerprint(second))
        self.assertNotEqual(observation.change_fingerprint(first),observation.change_fingerprint(third))


class EndPlayActor:
    def __init__(self): self.callbacks=[];self.events={};self.delegate_exists=True;self.unbound=0
    def is_valid(self): return True
    def get_path_name(self): return "pawn"
    def get_class(self): return self
    def call_function(self,name):
        if name!="GetLocalRole": raise AssertionError(name)
        return 1
    def bind_event(self,event,callback): self.callbacks.append(callback);self.events.setdefault(event,[]).append(callback)
    def unbind_event(self,event,callback):
        if not self.delegate_exists: raise RuntimeError("unable to find event property OnEndPlay")
        self.callbacks.remove(callback);self.events[event].remove(callback);self.unbound+=1
    def end_play(self):
        for callback in list(self.events.get("OnEndPlay",[])): callback(self,0)
        self.delegate_exists=False
    def destroyed(self):
        for callback in list(self.events.get("OnDestroyed",[])): callback(self)
        self.delegate_exists=False


class TestEarlyWatchLifetime(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        # Other policy models install a minimal uep_runtime module during test
        # discovery. This lifetime regression must exercise the real cleanup.
        spec=importlib.util.spec_from_file_location("_melee_readiness_scope",Path(__file__).resolve().parents[3]/"Content/Scripts/uep_runtime/subscriptions.py")
        scope_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope_module)
        scope_patch=patch.object(observation,"SubscriptionScope",scope_module.SubscriptionScope)
        scope_patch.start();self.addCleanup(scope_patch.stop)
        self.watch=observation.EarlyWatch(Path(temporary.name),"server","model")
        self.addCleanup(self.watch.close)
    def test_end_play_detaches_before_native_delegate_disappears(self):
        pawn=EndPlayActor();self.watch.watch(pawn,"pawn")
        pawn.end_play();self.watch.close()
        self.assertEqual(pawn.unbound,1);self.assertEqual(self.watch.scopes,{})
        self.assertEqual(len(self.watch.files),1)
    def test_shutdown_detaches_only_still_live_actors(self):
        old,new=EndPlayActor(),EndPlayActor()
        self.watch.watch(old,"old");self.watch.watch(new,"new");old.end_play()
        self.watch.close();self.watch.close()
        self.assertEqual((old.unbound,new.unbound),(1,1))
    def test_closed_watcher_never_publishes_late_end_play(self):
        pawn=EndPlayActor();self.watch.watch(pawn,"pawn");self.watch.close()
        self.watch.ended("pawn",0)
        self.assertEqual(self.watch.files,[])
    def test_one_cleanup_error_does_not_skip_other_live_actors(self):
        broken,live=EndPlayActor(),EndPlayActor()
        self.watch.watch(broken,"broken");self.watch.watch(live,"live")
        broken.delegate_exists=False
        with self.assertRaisesRegex(RuntimeError,"listener cleanup failed"): self.watch.close()
        self.assertEqual(live.unbound,1);self.assertTrue(self.watch.closed)
    def test_construction_captures_destroy_without_actor_begin_or_end(self):
        pawn=EndPlayActor();self.watch.constructed(pawn);pawn.destroyed();self.watch.close()
        rows=[json.loads((self.watch.root/name).read_text(encoding="utf-8")) for name in self.watch.files]
        self.assertEqual([row["kind"] for row in rows],["native-construction","native-destroyed-before-end-play"])
        self.assertEqual(pawn.unbound,2);self.assertTrue(rows[-1]["data"]["python_stack"])
    def test_constructed_actor_end_detaches_destroy_listener_before_native_teardown(self):
        pawn=EndPlayActor();self.watch.constructed(pawn);pawn.end_play();pawn.destroyed()
        rows=[json.loads((self.watch.root/name).read_text(encoding="utf-8")) for name in self.watch.files]
        self.assertEqual([row["kind"] for row in rows],["native-construction","native-end-play"])
        self.assertEqual(pawn.unbound,2)
    def test_repeated_construction_does_not_duplicate_native_listeners(self):
        pawn=EndPlayActor();self.watch.constructed(pawn);self.watch.constructed(pawn);self.watch.close()
        self.assertEqual(pawn.unbound,2)


if __name__ == "__main__": unittest.main()
