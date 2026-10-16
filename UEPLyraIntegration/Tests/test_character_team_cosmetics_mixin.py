"""Original three-way Sequence and opaque device defaults; no hardware proof."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class CharacterTeamCosmeticModels(unittest.TestCase):
    def setUp(self):
        self.calls, self.user_valid, self.team, self.user, self.color = [], True, 3, object(), object()
        self.display = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("display", *args)), get_path_name=lambda: "DisplayAsset")
        engine = types.ModuleType("unreal_engine"); structs = types.ModuleType("unreal_engine.structs")
        structs.ActivateDevicePropertyParams = lambda **kwargs: types.SimpleNamespace(**kwargs)
        engine.FLinearColor = lambda *args: args
        engine.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=lambda *args: self.library(name, *args)))
        engine.load_class = lambda path: path
        native = types.ModuleType("uep_lyra_world.effect_pad_mixin"); native.valid = lambda value: value is not None
        outline = types.ModuleType("uep_lyra_characters.outline_mixin")
        class Parent:
            def ClearInventory(self): pass
            def GetEmoteAudioComponent(self): pass
            def SetEmoteAudioComponent(self, AudioComponent): pass
            def ChangeQuickbarSlot(self, NewSlotIndex, SlotActionTag): pass
            def AddInitialInventory(self): pass
            def CreateOrUpdateOutlineIfNeeded(self, TeamID, OutlineColor): pass
        outline.LyraCharacterOutlinePythonProfile = outline.LyraCharacterOutlineBlueprintFallbackProfile = Parent
        file = Path(__file__).resolve().parents[1]/"Overlay/Content/Scripts/uep_lyra_characters/team_cosmetics_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_characters._team_policy_model", file)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": engine, structs.__name__: structs, native.__name__: native, outline.__name__: outline}):
            spec.loader.exec_module(self.module)
        self.parent, self.python = Parent, self.module.LyraCharacterTeamPythonProfile
        self.actor = types.SimpleNamespace(get_property=lambda name: self.display if name == "TeamDisplayAsset" else self.team,
            call_function=self.actor_call, call_mixin_original=lambda *args: self.calls.append(("original", *args)))
        self.devices = types.SimpleNamespace(call_function=lambda *args: self.calls.append(("devices", *args)))

    def library(self, cls, method, *args):
        self.calls.append((cls, method, *args))
        if cls == "LyraTeamStatics": return self.color
        if cls == "InputDeviceLibrary": return self.user_valid
        if cls == "SubsystemBlueprintLibrary": return self.devices
        raise AssertionError(cls)

    def actor_call(self, *args):
        self.calls.append(("actor", *args)); return self.user if args[0] == "GetPlatformUserId" else None

    def invoke(self): self.python.OnTeamOrCosmeticsChanged(self.actor, self.team, self.display)

    def test_original_sequence_is_color_outline_stencil_then_display_then_devices(self):
        self.invoke()
        self.assertEqual([call[1] for call in self.calls], ["GetTeamColorWithFallback", "CreateOrUpdateOutlineIfNeeded",
            "UpdateCustomStencilFromTeamID", "ApplyToActor", "GetPlatformUserId", "IsValidPlatformId", "GetEngineSubsystem", "ActivateDevicePropertyOfClass"])

    def test_native_color_query_keeps_display_name_and_exact_original_fallback(self):
        self.invoke(); self.assertEqual(self.calls[0], ("LyraTeamStatics", "GetTeamColorWithFallback", self.display, "TeamColor", (.645833, 0., .568715, 1.)))

    def test_outline_receives_native_opaque_color_without_conversion(self):
        self.invoke(); self.assertEqual(self.calls[1], ("actor", "CreateOrUpdateOutlineIfNeeded", 3, self.color))

    def test_stencil_is_a_retained_native_bp_call_not_reimplemented_or_skipped(self):
        self.invoke(); self.assertEqual(self.calls[2], ("actor", "UpdateCustomStencilFromTeamID", 3))

    def test_display_applies_to_self_including_child_actors(self):
        self.invoke(); self.assertEqual(self.calls[3], ("display", "ApplyToActor", self.actor, True))

    def test_missing_display_still_updates_outline_and_stencil_but_skips_apply(self):
        self.display = None; self.invoke(); self.assertEqual(self.calls[0][2], None)
        self.assertFalse(any(call[0] == "display" for call in self.calls)); self.assertEqual(self.module.evidence(self.actor)["outline_calls"], 1)

    def test_invalid_platform_user_stops_before_subsystem_or_device_activation(self):
        self.user_valid = False; self.invoke()
        self.assertEqual(self.calls[-1], ("InputDeviceLibrary", "IsValidPlatformId", self.user))
        self.assertEqual(self.module.evidence(self.actor)["invalid_platform_noops"], 1)

    def test_opaque_platform_user_is_forwarded_to_native_struct_with_other_defaults(self):
        self.invoke(); activate = self.calls[-1]
        self.assertEqual(activate[:3], ("devices", "ActivateDevicePropertyOfClass", self.module.DEVICE))
        self.assertEqual(vars(activate[3]), {"UserId": self.user})

    def test_no_authority_or_local_guard_is_invented_for_shared_display_business(self):
        self.invoke(); self.assertFalse(any(call[1] in ("HasAuthority", "IsLocallyControlled") for call in self.calls))

    def test_repeated_events_preserve_original_native_scheduler_activation_attempts(self):
        self.invoke(); self.invoke(); self.assertEqual(self.module.evidence(self.actor)["device_activation_attempts"], 2)

    def test_fallback_only_replays_original_once(self):
        self.module.LyraCharacterTeamBlueprintFallbackProfile.OnTeamOrCosmeticsChanged(self.actor, self.team, self.display)
        self.assertEqual(self.calls, [("original", "OnTeamOrCosmeticsChanged", self.team, self.display)])

    def test_all_six_accepted_helpers_are_explicit_local_aliases(self):
        for profile in (self.python, self.module.LyraCharacterTeamBlueprintFallbackProfile):
            for name in ("ClearInventory", "GetEmoteAudioComponent", "SetEmoteAudioComponent", "ChangeQuickbarSlot", "AddInitialInventory", "CreateOrUpdateOutlineIfNeeded"):
                self.assertIs(profile.__dict__[name], getattr(self.parent, name))

    def test_per_actor_pod_evidence_does_not_retain_native_activation_handles(self):
        self.invoke(); value = self.module.evidence(self.actor)
        self.assertTrue(all(type(count) is int for key, count in value.items() if key != "last_call"))
        self.assertEqual(value["last_call"], dict(team_id=3, display_asset="DisplayAsset"))
        self.assertEqual(self.module.evidence(types.SimpleNamespace())["device_activation_attempts"], 0)

    def test_real_function_parameters_are_used_not_same_named_actor_fields(self):
        self.actor.get_property = lambda name: self.fail("function parameters are not Actor properties")
        self.team = -1; self.display = None; self.invoke()
        self.assertEqual(self.calls[0][2], None); self.assertEqual(self.calls[1][2], -1)
