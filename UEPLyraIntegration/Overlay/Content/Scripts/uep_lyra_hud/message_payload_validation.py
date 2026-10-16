"""Real optional-plugin typed messaging, using only compiled VM wildcard calls."""

import json
from pathlib import Path
import sys
import time
import traceback

import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraVerbMessage

from uep_runtime import SubscriptionScope
from .weapon_observer import valid


UI_PATH = "/ShooterCore/Input/Abilities/Struct_UIMessaging.Struct_UIMessaging"
ON = "ON_1_5C60262A40576A9B456771A11BE74887"
CONTROLLER = "Controller_6_18E0704C47A404BDF6B92284D521D293"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


class MessagePayloadValidation:
    def __init__(self, result):
        self.path = Path(result)
        self.started = time.monotonic()
        self.scopes = []
        self.helper = None
        self.other = None
        self.report = {"schema_version": 1, "status": "running", "full_acceptance": False,
                       "wildcard_process_event_called": False, "native_gameplay_input_tested": False,
                       "business_migration_complete": False}

    def run(self, world, controller):
        cls = ue.load_class("/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C")
        self.helper = ue.new_object(cls)
        self.helper.add_to_root()
        router = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function(
            "GetGameInstanceSubsystem", world, ue.find_class("GameplayMessageSubsystem"))
        check(valid(router), "real GameplayMessageSubsystem unavailable")
        ui = ue.load_object(ue.find_class("UserDefinedStruct"), UI_PATH)
        self.other = world.actor_spawn(ue.find_class("PlayerController"))
        signals, messages, verbs, proxies, mismatches, nested = [], [], [], [], [], []
        inside_nested = False

        def make_ui(enabled, owner):
            payload = ui()
            setattr(payload, ON, enabled)
            setattr(payload, CONTROLLER, owner)
            return payload

        def read_ui(proxy):
            payload, success = self.helper.call_function("ReadUI", proxy)
            check(success is True, "typed UI extraction failed: " + repr((payload, success)))
            wrong, wrong_success = self.helper.call_function("ReadVerb", proxy)
            check(wrong_success is False, "mismatched reader accepted UI bytes as native Verb")
            mismatches.append(wrong_success)
            proxies.append(proxy)
            return payload

        def on_ui(channel, payload):
            nonlocal inside_nested
            before = bool(getattr(payload, ON))
            owner = getattr(payload, CONTROLLER)
            messages.append({"on": before, "controller": owner.get_path_name(), "local_owner": owner == controller})
            if before and owner == controller and not inside_nested:
                inside_nested = True
                self.helper.call_function("BroadcastUI", router, GameplayTag(TagName="Gameplay.Message.ADS"), make_ui(False, controller))
                inside_nested = False
                check(getattr(payload, ON) is True, "nested broadcast overwrote owning Python payload copy")
                nested.append(True)

        def read_verb(proxy):
            payload, success = self.helper.call_function("ReadVerb", proxy)
            check(success is True, "native Verb extraction failed")
            return payload

        def on_verb(channel, payload):
            verbs.append({"magnitude": float(payload.Magnitude), "instigator": payload.Instigator.get_path_name(),
                          "target": payload.Target.get_path_name()})

        signal, typed_ui, typed_verb = SubscriptionScope(), SubscriptionScope(), SubscriptionScope()
        self.scopes = [signal, typed_ui, typed_verb]
        signal.listen_gameplay_signal(world, "Gameplay.Message.ADS", lambda channel: signals.append(str(channel.TagName)))
        typed_ui.listen_gameplay_message(world, "Gameplay.Message.ADS", ui, read_ui, on_ui)
        typed_verb.listen_gameplay_message(world, "Lyra.Elimination.Message", ue.find_struct("LyraVerbMessage"), read_verb, on_verb)
        self.helper.call_function("BroadcastUI", router, GameplayTag(TagName="Gameplay.Message.ADS"), make_ui(True, controller))
        self.helper.call_function("BroadcastUI", router, GameplayTag(TagName="Gameplay.Message.ADS"), make_ui(True, self.other))
        check([entry["on"] for entry in messages] == [True, False, True], "UI payload values/order differ")
        check([entry["local_owner"] for entry in messages] == [True, True, False], "typed player identities were lost")
        check(len(signals) == 3 and nested == [True] and mismatches == [False] * 3, "typed/legacy/nested delivery incomplete")
        verb = LyraVerbMessage(Verb=GameplayTag(TagName="Lyra.Elimination.Message"),
                               Instigator=controller, Target=self.other, Magnitude=3.5)
        self.helper.call_function("BroadcastVerb", router, GameplayTag(TagName="Lyra.Elimination.Message"), verb)
        check(verbs == [{"magnitude": 3.5, "instigator": controller.get_path_name(), "target": self.other.get_path_name()}],
              "native Verb payload differs")
        payload, available = self.helper.call_function("ReadUI", proxies[0])
        check(available is False, "payload pointer remained available outside delivery")
        counts = (len(messages), len(signals), len(verbs))
        for scope in self.scopes:
            scope.close()
            scope.close()
        self.helper.call_function("BroadcastUI", router, GameplayTag(TagName="Gameplay.Message.ADS"), make_ui(False, controller))
        self.helper.call_function("BroadcastVerb", router, GameplayTag(TagName="Lyra.Elimination.Message"), verb)
        check((len(messages), len(signals), len(verbs)) == counts, "closed listeners received a later message")
        self.report.update(typed_ui=messages, typed_verb=verbs, legacy_signals=len(signals),
                           nested_payload_copy_preserved=True, wrong_reader_rejected=True,
                           outside_delivery_rejected=True, close_idempotent=True,
                           callbacks_after_close=0, compiled_vm_transport=True)

    def finish(self, error=None):
        try:
            for scope in self.scopes:
                scope.close()
            if valid(self.other):
                self.other.actor_destroy()
            if valid(self.helper):
                self.helper.remove_from_root()
        except Exception:
            error = (error or "") + traceback.format_exc()
        self.report.update(status="failed" if error else "passed", error=error,
                           scopes_closed=all(scope.closed and scope.count == 0 for scope in self.scopes),
                           elapsed_seconds=time.monotonic() - self.started)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_TYPED_MESSAGE_" + ("FAILED " + error if error else "PASSED"))
        ue.request_exit()

    def tick(self, delta):
        try:
            check(time.monotonic() - self.started < 90, "typed message fixture timed out")
            for world in ue.all_worlds():
                if world.get_world_type() not in (1, 3, 5):
                    continue
                check("/Engine/Maps/Entry" in world.get_path_name(), "transport fixture requires Entry")
                controller = ue.find_class("GameplayStatics").get_cdo().call_function("GetPlayerController", world, 0)
                if not valid(controller):
                    continue
                self.run(world, controller)
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


prefix = "-UEPTypedMessageResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = MessagePayloadValidation(result)
ticker = ue.add_ticker(validation.tick)
