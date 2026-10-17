"""Diagnostic timing controls are not native warmup/network acceptance."""
import importlib
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

control=importlib.import_module("uep_lyra_abilities.melee_warmup_join_control")


class Native:
    def __init__(self,name,calls=None): self.name,self.calls=name,calls or {}
    def is_valid(self): return True
    def call_function(self,name,*args):
        value=self.calls[name]
        return value(*args) if callable(value) else value
    def get_world_type(self): return 1
    def get_name(self): return "L_Expanse"
    def get_path_name(self): return self.name
    def get_controlled_pawn(self): return self.pawn
    def get_component_by_type(self,cls): return self.health


class TestWarmupJoinControl(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.world=Native("world");self.writes=[];self.time=1.
        def set_time(world,value): self.writes.append(value);self.time=value
        self.phases=Native("phases",dict(IsPhaseActive=True))
        self.statics=Native("statics",dict(GetGlobalTimeDilation=lambda world:self.time,SetGlobalTimeDilation=set_time))
        self.subsystems=Native("subsystems",dict(GetWorldSubsystem=self.phases))
        native=types.SimpleNamespace(all_worlds=lambda:[self.world],find_class=lambda name:types.SimpleNamespace(get_cdo=lambda:self.subsystems if name=="SubsystemBlueprintLibrary" else self.statics))
        for item in (patch.object(control,"ue",native),patch.object(control,"valid",lambda value:value is not None),patch.object(control,"GameplayTag",lambda **values:types.SimpleNamespace(**values))):
            item.start();self.addCleanup(item.stop)
        self.value=control.WarmupJoinControl(self.root,"server","run")
        self.addCleanup(self.value.close)
    def beacons(self,run="run",same_owner=False):
        for index,peer in enumerate(control.PEERS):
            control.atomic_write(self.root/(peer+"-warmup-joined.json"),dict(run_id=run,peer=peer,player_id=10 if same_owner else 10+index))
    def test_hold_until_both_real_client_beacons(self):
        self.value.server_poll();self.assertEqual(self.writes,[.1]);self.assertFalse(self.value.released)
        self.beacons();self.value.server_poll()
        self.assertEqual(self.writes,[.1,1.]);self.assertTrue(self.value.report["native_warmup_observed"]);self.assertTrue(self.value.report["restored"])
    def test_server_hold_not_reapplied_after_release(self):
        self.beacons();self.value.server_poll();self.value.server_poll();self.value.close()
        self.assertEqual(self.writes,[.1,1.])
    def test_failure_cleanup_restores_original_time(self):
        self.time=.75;self.value.server_poll();self.value.close();self.value.close()
        self.assertEqual(self.writes,[.1,.75])
    def test_foreign_run_beacon_rejected(self):
        self.beacons(run="foreign")
        with self.assertRaisesRegex(RuntimeError,"foreign"): self.value.server_poll()
    def test_duplicate_player_beacons_rejected(self):
        self.beacons(same_owner=True)
        with self.assertRaisesRegex(RuntimeError,"distinct"): self.value.server_poll()
    def test_no_world_does_not_write_time(self):
        with patch.object(control.ue,"all_worlds",lambda:[]): self.value.server_poll()
        self.assertEqual(self.writes,[])
    def test_missed_warmup_is_not_accepted_as_join_before_reset(self):
        self.phases.calls["IsPhaseActive"]=False;self.beacons()
        with self.assertRaisesRegex(RuntimeError,"did not join"): self.value.server_poll()
    def test_client_beacon_requires_actual_healthy_autonomous_pawn(self):
        health=Native("health",dict(GetHealth=100.));pawn=Native("pawn",dict(GetLocalRole=2));pawn.health=health
        controller=Native("controller");controller.pawn=pawn;controller.PlayerState=types.SimpleNamespace(PlayerId=99)
        self.statics.calls["GetPlayerController"]=controller
        value=control.WarmupJoinControl(self.root,"A","run");value.client_poll();value.client_poll();value.close()
        self.assertEqual(control.read_json(self.root/"A-warmup-joined.json")["pawn"],"pawn");self.assertEqual(self.writes,[])
    def test_unbound_health_never_gets_join_beacon(self):
        health=Native("health",dict(GetHealth=0.));pawn=Native("pawn",dict(GetLocalRole=2));pawn.health=health
        controller=Native("controller");controller.pawn=pawn;self.statics.calls["GetPlayerController"]=controller
        value=control.WarmupJoinControl(self.root,"B0","run");value.client_poll();value.close()
        self.assertFalse(value.report["join_beacon_written"])
