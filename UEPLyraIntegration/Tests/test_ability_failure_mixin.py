"""Host policy/lifetime checks, not native UI/animation/message acceptance."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class Payload:
    def __init__(self, owner, token):
        self.PlayerController, self.token = owner, token

    @property
    def UserFacingReason(self):
        raise AssertionError("policy converted native FText to a Python string")

    def clone(self):
        return Payload(self.PlayerController, self.token)


class FailurePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls, self.clock, self.dead = [], 100.0, False
        self.owner, self.pawn, self.other = object(), object(), object()
        self.health = types.SimpleNamespace(call_function=lambda name: self.dead)
        self.ticker_callbacks, self.ticker_handles = [], []
        self.scope_fail = False

        class Scope:
            def __init__(scope):
                scope.closed = False

            def listen_gameplay_message(scope, *args):
                if self.scope_fail:
                    raise RuntimeError("synthetic listen failure")
                self.read, self.deliver = args[-2:]

            def close(scope):
                if not scope.closed:
                    self.calls.append(("close",))
                scope.closed = True

        def helper_call(name, *args):
            self.calls.append((name,) + args)
            if name == "CopyFailureText":
                args[0].text = args[1].token  # Emulates native opaque FText copy.
            if name == "SameFailureText":
                return (args[0].text == args[1].token,)
            if name == "ReadFailure":
                return self.payload, True

        self.helper = types.SimpleNamespace(call_function=helper_call,
            add_to_root=lambda: self.calls.append(("root",)), remove_from_root=lambda: self.calls.append(("unroot",)))
        native = types.ModuleType("unreal_engine")
        native.new_object = lambda cls: self.helper
        native.find_struct = lambda name: name
        native.find_class = lambda name: types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(
            call_function=lambda func, *args: self.clock if func == "GetTimeSeconds" else self.health))

        def add_ticker(callback):
            handle = object()
            self.ticker_callbacks.append(callback)
            self.ticker_handles.append(handle)
            return handle

        native.add_ticker, native.remove_ticker = add_ticker, lambda handle: self.calls.append(("untick", handle))
        structs = types.ModuleType("unreal_engine.structs")
        structs.LatentActionInfo = lambda **values: types.SimpleNamespace(**values)
        def native_class(name):
            def call(func, *args):
                self.calls.append((func,) + args)
                return self.clock if func == "GetTimeSeconds" else self.health
            return types.SimpleNamespace(get_cdo=lambda: types.SimpleNamespace(call_function=call))
        native.find_class = native_class
        runtime = types.ModuleType("uep_runtime")
        runtime.SubscriptionScope = Scope
        observer = types.ModuleType("uep_lyra_hud.weapon_observer")
        observer.valid = lambda obj: obj is not None
        path = Path(__file__).resolve().parents[1] / "Overlay/Content/Scripts/uep_lyra_hud/ability_failure_mixin.py"
        spec = importlib.util.spec_from_file_location("uep_lyra_hud._failure_contract", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal_engine": native, "unreal_engine.structs": structs, "uep_runtime": runtime, "uep_lyra_hud.weapon_observer": observer}):
            spec.loader.exec_module(self.module)
        self.widget = self.module.LyraAbilityFailurePythonProfile()
        self.widget.PythonMessageAdapterClass = object()
        self.widget.Intro, self.widget.Outro = object(), object()
        self.widget.FailureReasonTextWidget = types.SimpleNamespace(text="initial")
        self.visibility = 1

        def widget_call(name, *args):
            self.calls.append((name,) + args)
            if name == "GetOwningPlayer":
                return self.owner
            if name == "GetOwningPlayerPawn":
                return self.pawn
            if name == "GetVisibility":
                return self.visibility
            if name == "SetVisibility":
                self.visibility = args[0]

        self.widget.call_function = widget_call
        self.widget.call_mixin_original = lambda *args: self.calls.append(("original",) + args)
        self.widget.get_path_name = lambda: "test-widget"

    def activate(self):
        self.widget.OnInitialized()

    def send(self, token="reason-a", owner=None):
        self.module.received(self.widget, Payload(owner or self.owner, token))

    def test_initialize_construct_resume_are_idempotent(self):
        self.activate()
        self.widget.Construct()
        self.widget.ResumeObservation()
        self.assertEqual(len(self.ticker_handles), 0)
        self.assertEqual(self.module.snapshot()["scopes_created"], 1)
        self.assertEqual(self.visibility, 1)

    def test_hidden_message_uses_opaque_text_native_animation_and_game_time(self):
        self.activate()
        self.send()
        self.assertEqual(self.widget.FailureReasonTextWidget.text, "reason-a")
        self.assertEqual(self.visibility, 3)
        self.assertTrue(self.widget._uep_failure_delay_pending)
        self.assertIn(("PlayAnimationForward", self.widget.Intro, 1.0, False), self.calls)

    def test_same_reason_does_not_retrigger_delay_or_animation(self):
        self.activate()
        self.send()
        self.clock = 100.75
        self.send()
        self.assertTrue(self.widget._uep_failure_delay_pending)
        self.assertEqual(self.module.snapshot()["intros"], 1)
        self.assertEqual(self.module.snapshot()["outros"], 0)

    def test_different_reason_waits_for_native_outro_completion(self):
        self.activate()
        self.send()
        self.send("reason-b")
        self.assertEqual(self.widget.FailureReasonTextWidget.text, "reason-a")
        self.widget.OnAnimationFinished(self.widget.Outro)
        self.assertEqual(self.widget.FailureReasonTextWidget.text, "reason-b")
        self.assertEqual(self.visibility, 3)

    def test_comparison_rejects_non_tuple_or_non_boolean_output(self):
        self.activate()
        self.send()
        for malformed in (False, ("False",), (False, True), ()):
            original = self.helper.call_function
            self.helper.call_function = lambda name, *args: malformed if name == "SameFailureText" else original(name, *args)
            with self.assertRaisesRegex(RuntimeError, "comparison output"):
                self.send("reason-b")
            self.helper.call_function = original

    def test_foreign_owner_does_not_start_presentation(self):
        self.activate()
        self.send(owner=self.other)
        self.assertEqual(self.visibility, 1)
        self.assertFalse(self.widget._uep_failure_delay_pending)
        self.assertEqual(self.module.snapshot()["foreign_messages"], 1)

    def test_invalid_or_dead_health_rejects(self):
        for missing in (False, True):
            self.setUp()
            self.activate()
            if missing:
                self.health = None
            else:
                self.dead = True
            self.send()
            self.assertEqual(self.visibility, 1)
            self.assertEqual(self.module.snapshot()["health_rejections"], 1)

    def test_native_latent_request_has_explicit_callback_target_uuid_and_linkage(self):
        self.activate()
        self.send()
        request = next(call for call in self.calls if call[0] == "RetriggerableDelay")
        self.assertEqual(request[1:3], (self.widget, 1.0))
        info = request[3]
        self.assertEqual((info.Linkage, info.UUID, info.ExecutionFunction), (0, self.module.DELAY_UUID, self.module.DELAY_COMPLETE))
        self.assertIs(info.CallbackTarget, self.widget)
        self.assertFalse(self.ticker_callbacks)

    def test_intro_completion_is_not_outro_completion(self):
        self.activate()
        self.send()
        self.widget.OnAnimationFinished(self.widget.Intro)
        self.assertEqual(self.visibility, 3)
        self.assertEqual(self.module.snapshot()["completions"], 0)

    def test_expiry_outro_then_native_finish_collapses(self):
        self.activate()
        self.send()
        self.widget.DelayComplete(0)
        self.assertEqual(self.visibility, 3)
        self.widget.OnAnimationFinished(self.widget.Outro)
        self.assertEqual(self.visibility, 1)

    def test_duplicate_native_completion_does_not_replay_outro(self):
        self.activate()
        self.send()
        self.widget.DelayComplete(0)
        self.widget.DelayComplete(0)
        self.assertEqual(self.module.snapshot()["outros"], 1)
        self.assertEqual(self.module.snapshot()["native_delay_callbacks"], 1)

    def test_wrong_native_linkage_is_rejected(self):
        self.activate()
        self.send()
        with self.assertRaisesRegex(RuntimeError, "continuation"):
            self.widget.DelayComplete(99)
        self.assertEqual(self.module.snapshot()["outros"], 0)

    def test_deferred_latest_payload_matches_audited_bp_frame_model(self):
        self.activate()
        self.send()
        self.send("reason-b")
        self.send("foreign-latest", self.other)
        self.widget.OnAnimationFinished(self.widget.Outro)
        self.assertEqual(self.widget.FailureReasonTextWidget.text, "foreign-latest")
        # This is an audited hypothesis, NOT native BP runtime confirmation.

    def test_typed_reader_clones_payload_without_reading_its_text(self):
        self.activate()
        self.payload = Payload(self.owner, "native-text-token")
        cloned = self.read(object())
        self.assertIsNot(cloned, self.payload)
        self.assertEqual(cloned.token, self.payload.token)

    def test_close_disarms_ticker_callbacks_and_releases_roots_once(self):
        self.activate()
        self.send()
        self.widget.__uep_mixin_teardown__()
        self.widget.__uep_mixin_teardown__()
        self.widget.DelayComplete(0)
        final = self.module.snapshot()
        self.assertEqual((final["scopes_created"], final["scopes_closed"], final["tickers_created"], final["tickers_closed"]), (1, 1, 0, 0))
        self.assertEqual(final["active_count"], 0)
        self.assertEqual(self.calls.count(("unroot",)), 1)

    def test_construct_rearms_after_native_destruct(self):
        self.activate()
        self.widget.Destruct()
        self.widget.Construct()
        self.assertEqual(self.module.snapshot()["scopes_created"], 2)
        self.send()
        self.assertEqual(self.visibility, 3)

    def test_failed_listen_releases_reader_root(self):
        self.scope_fail = True
        with self.assertRaisesRegex(RuntimeError, "listen failure"):
            self.activate()
        self.assertIsNone(self.widget._uep_failure_scope)
        self.assertEqual(self.calls.count(("unroot",)), 1)
        self.assertEqual(self.module.snapshot()["scopes_created"], 0)

    def test_close_failure_still_releases_reader_and_disarms_state(self):
        self.activate()
        self.widget._uep_failure_scope.close = lambda: (_ for _ in ()).throw(RuntimeError("close failure"))
        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            self.widget.__uep_mixin_teardown__()
        self.assertIsNone(self.widget._uep_failure_scope)
        self.assertEqual(self.calls.count(("unroot",)), 1)
        self.assertEqual(len(self.module.snapshot()["errors"]), 1)

    def test_original_cancel_failure_does_not_skip_other_owned_cleanup(self):
        fallback = self.module.LyraAbilityFailureBlueprintFallbackProfile()
        fallback.UEPOriginalFailureProxy = types.SimpleNamespace(
            call_function=lambda *args: (_ for _ in ()).throw(RuntimeError("cancel failure")))
        fallback.Intro = fallback.Outro = None
        fallback.call_function = lambda *args: self.calls.append(args)
        with self.assertRaisesRegex(RuntimeError, "original failure UI cleanup failed"):
            fallback.__uep_mixin_teardown__()
        self.assertEqual(self.calls, [("CancelLatentActions",), ("UEPRemoveOriginalFailureBindings",)])

    def test_fallback_cleanup_targets_only_widget_latents_and_exact_delegates(self):
        fallback = self.module.LyraAbilityFailureBlueprintFallbackProfile()
        fallback.UEPOriginalFailureProxy = types.SimpleNamespace(call_function=lambda *args: self.calls.append(args))
        fallback.Intro, fallback.Outro = None, None
        fallback.call_function = lambda *args: self.calls.append(args)
        fallback.__uep_mixin_teardown__()
        self.assertEqual(self.calls, [("Cancel",), ("CancelLatentActions",), ("UEPRemoveOriginalFailureBindings",)])


if __name__ == "__main__":
    unittest.main()
