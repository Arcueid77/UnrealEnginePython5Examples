"""Policy tests, not proof of native collision, teleport or audio playback."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_inventory_pad_mixin import Object
from test_launcher_mixin import vector


class TeleporterPolicy(unittest.TestCase):
    def setUp(self):
        native = types.ModuleType("unreal_engine")
        native.FVector = vector
        native.find_class = native.load_class = lambda name: name
        native.load_object = lambda cls, path: "sound"
        dependency = types.ModuleType("uep_lyra_world.effect_pad_mixin")
        dependency.valid = lambda value: value is not None and value.is_valid()
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_world/teleporter_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_world._teleporter_policy", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "uep_lyra_world.effect_pad_mixin": dependency}):
            spec.loader.exec_module(self.module)
        self.libraries, self.authority, self.teleport_ok, self.local = [], True, True, False
        self.module.library = lambda cls: Object(cls, lambda name, *args, **kwargs: self.library(cls, name, *args, **kwargs))
        self.actor = Object("teleporter", self.actor_call)
        self.actor.set_property = lambda name, value: setattr(self.actor, name, value)
        self.actor.get_property = lambda name: getattr(self.actor, name)
        self.actor.DefaultSceneRoot1 = Object("root", lambda name: vector(0., 0., 0.) if name == "K2_GetComponentLocation" else vector(1., 0., 0.))
        self.actor.Niagara, self.actor.Box = Object("niagara"), Object("box")
        for key, value in dict(TeleporterEdgeWidth=10., TeleporterWidth=400., TeleporterHeight=800.,
            TeleporterSpread=100., TeleporterPhase=5., TeleporterBrigtness=1., TeleporterNumPlanes=500,
            TeleporterInwardMotion=True, ReceiverOnly=False, KeepReleativeEntryUponExit=False,
            bForceDirection=True, LaunchOnTeleport=True, LaunchMultiplier=1250., GameplayCueTag="tag").items():
            setattr(self.actor, key, value)
        self.target = Object("target")
        self.target.set_property = lambda name, value: setattr(self.target, name, value)
        self.exit = Object("exit", lambda name: vector(1000., 500., 200.) if name == "K2_GetComponentLocation" else vector(0., 1., 0.))
        self.target.get_property = lambda name: self.exit
        self.actor.TeleportingTarget = [self.target]
        self.mesh = Object("mesh", lambda name: vector(30., 40., 50.))
        self.controller = Object("controller")
        self.pawn = Object("pawn", self.pawn_call)
        self.pawn.is_a = lambda cls: cls == "Character"
        self.pawn.Mesh = self.mesh

    def library(self, cls, name, *args, **kwargs):
        self.libraries.append((name, args, kwargs))
        return 0 if name == "RandomInteger" else (kwargs if name == "MakeGameplayCueParameters" else "rotation")

    def actor_call(self, name, *args):
        if name == "HasAuthority":
            return self.authority
        if name == "Set Teleporter Destination":
            return self.module.destination(self.actor)
        if name == "Teleport Audio for Pawn":
            return self.module.sound(self.actor, args[0], True)
        if name == "Teleport Audio for Grenade":
            return self.module.sound(self.actor, args[0], False)

    def pawn_call(self, name, *args):
        return {"GetController": self.controller, "IsLocallyViewed": self.local, "K2_TeleportTo": self.teleport_ok}.get(name)

    def test_construction_and_receiver_only_match_original(self):
        self.assertFalse(self.module.LyraTeleporterPythonProfile.Construction(self.actor))
        self.assertIn(("SetVariableInt", "SystemEntered", 0), self.actor.Niagara.calls)
        self.assertIn(("SetVariableFloat", "Brightness", 1.), self.actor.Niagara.calls)
        self.assertEqual(self.actor.Box.calls, [])
        self.actor.ReceiverOnly = True
        self.module.construct(self.actor)
        self.assertEqual(self.actor.Box.calls, [("K2_DestroyComponent", self.actor)])

    def test_destination_uses_ue_rng_and_empty_is_none(self):
        self.module.destination(self.actor)
        self.assertIs(self.actor.TeleporterDestination, self.target)
        self.assertEqual(self.libraries[0], ("RandomInteger", (1,), {}))
        self.actor.TeleportingTarget = []
        self.module.destination(self.actor)
        self.assertIsNone(self.actor.TeleporterDestination)
        self.assertEqual(len(self.libraries), 1)

    def test_world_space_offset_projection_and_upper_lower_clamp(self):
        self.actor.KeepReleativeEntryUponExit = True
        exit_location = vector(1000., 500., 200.)
        result = self.module.offset_location(self.actor, exit_location, self.mesh)
        self.assertEqual((result.x, result.y, result.z), (1000., 540., 250.))
        self.mesh.callback = lambda name: vector(30., 40., 900.)
        self.assertEqual(self.module.offset_location(self.actor, exit_location, self.mesh).z, 900.)
        self.mesh.callback = lambda name: vector(30., 40., -900.)
        self.assertEqual(self.module.offset_location(self.actor, exit_location, self.mesh).z, 200.)

    def test_remote_still_selects_destination_audio_cue_and_control_not_teleport(self):
        self.authority = False
        self.module.begin(self.actor, self.pawn)
        self.assertIs(self.target.ReceivingPawn, self.pawn)
        self.assertFalse(any(c[0] in ("K2_TeleportTo", "LaunchCharacter") for c in self.pawn.calls))
        self.assertEqual(self.controller.calls, [("SetControlRotation", "rotation")])
        self.assertEqual(self.module.snapshot()["pawn_audio"], 1)

    def test_authority_teleport_then_override_launch_and_force_rotation(self):
        self.module.begin(self.actor, self.pawn)
        methods = [c[0] for c in self.pawn.calls]
        self.assertLess(methods.index("K2_TeleportTo"), methods.index("LaunchCharacter"))
        launch = next(c for c in self.pawn.calls if c[0] == "LaunchCharacter")
        self.assertEqual((launch[1].x, launch[1].y, launch[1].z), (0., 1250., 0.))
        self.assertEqual(launch[2:], (True, True))
        self.assertEqual(self.module.snapshot()["teleports"], 1)

    def test_failed_native_teleport_never_launches_but_keeps_rotation_sequence(self):
        self.teleport_ok = False
        self.module.begin(self.actor, self.pawn)
        self.assertFalse(any(c[0] == "LaunchCharacter" for c in self.pawn.calls))
        self.assertEqual(self.controller.calls, [("SetControlRotation", "rotation")])

    def test_launch_and_direction_flags_are_independent(self):
        self.actor.LaunchOnTeleport = self.actor.bForceDirection = False
        self.module.begin(self.actor, self.pawn)
        self.assertTrue(any(c[0] == "K2_TeleportTo" for c in self.pawn.calls))
        self.assertFalse(any(c[0] == "LaunchCharacter" for c in self.pawn.calls))
        self.assertEqual(self.controller.calls, [])

    def test_local_and_remote_audio_preserve_volume_locations_and_ui_flag(self):
        setattr(self.actor, "Overlapping Pawn", self.pawn)
        self.local = True
        self.module.sound(self.actor, "exit", True)
        self.assertEqual(self.libraries[-1][0], "PlaySound2D")
        self.assertIs(self.libraries[-1][2]["bIsUISound"], False)
        self.libraries.clear(); self.local = False
        self.module.sound(self.actor, "exit", True)
        self.assertEqual([row[0] for row in self.libraries], ["PlaySoundAtLocation"]*2)
        self.assertTrue(all(row[2]["VolumeMultiplier"] == .7 for row in self.libraries))

    def test_invalid_destination_fails_closed_not_fallback(self):
        self.actor.TeleportingTarget = []
        with self.assertRaisesRegex(RuntimeError, "valid destination"):
            self.module.LyraTeleporterPythonProfile.Begin(self.actor, self.pawn)
        self.assertEqual(self.module.snapshot()["errors"], ["teleporter requires a valid destination"])
        self.assertFalse(any(c[0] == "K2_TeleportTo" for c in self.pawn.calls))

    def test_grenade_uses_native_existing_callee_without_authority_filter(self):
        self.pawn.is_a = lambda cls: "B_Grenade_C" in cls
        self.authority = False
        self.module.begin(self.actor, self.pawn)
        self.assertEqual(self.pawn.calls[-1][0], "Teleport Grenade")
        self.assertFalse(any(c[0] == "HasAuthority" for c in self.actor.calls))
        self.assertEqual(self.module.snapshot()["grenade_entries"], 1)
