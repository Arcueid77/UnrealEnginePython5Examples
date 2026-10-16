"""Original full-magazine reload -> native GAS -> production failure UI.

No failure/message callback replay, native cost mutation or stat/property write.
The hidden same-class original BP comparator receives the same native message.
"""
import sys
import time
import traceback
import unreal_engine as ue
from .ability_failure_validation import AbilityFailureValidation, state, animations
from . import ability_failure_mixin as failure
from .ability_failure_native_contract import CASES, FOREIGN_CASE, FALSE_CLAIMS, require, validate
from .weapon_observer import valid
from uep_lyra_world.inventory_pad_network_state import capture, services, path
from uep_lyra_world.effect_pad_mixin import ability_system

RELOAD = "/Game/Weapons/Pistol/GA_Weapon_Reload_Pistol.GA_Weapon_Reload_Pistol_C"


class NativeFailure(AbilityFailureValidation):
    def __init__(self, result):
        super().__init__(result)
        self.report = dict(schema_version=1, status="running", error=None, cases=[], images=[],
            native_ability_producer_tested=False, native_source_verified=False,
            original_inventory_unchanged=False, original_health_unchanged=False)
        self.report.update({field: False for field in FALSE_CLAIMS})
        self.report.update(real_foreign_controller_tested=False, native_secondary_player_removed=False,
                           secondary_inventory_health_unchanged=False)
        self.second_controller = None
        self.test_foreign = "-UEPAbilityFailureRealForeignOwner" in sys.argv

    def setup(self):
        self.pawn = self.controller.get_controlled_pawn()
        self.asc = ability_system(self.pawn)
        self.ability_class = ue.load_class(RELOAD)
        self.original_inventory = capture(self.controller)
        require(self.original_inventory is not None and "/Pistol/ID_Pistol" in self.original_inventory["definition"] and
                self.original_inventory["magazine"] == 12, "native producer requires original fully loaded starting Pistol")
        inventory, quickbar = services(self.controller)
        self.item = quickbar.call_function("GetActiveSlotItem")
        self.fingerprint = sorted(path(item) for item in inventory.call_function("GetAllItems"))
        matches = [spec for spec in self.asc.get_property("ActivatableAbilities").Items
                   if valid(spec.Ability) and spec.Ability.get_class() == self.ability_class]
        require(len(matches) == 1 and valid(matches[0].SourceObject) and
                matches[0].SourceObject.is_a(ue.find_class("LyraRangedWeaponInstance")) and
                matches[0].SourceObject.call_function("GetInstigator") == self.item,
                "native reload lacks actual equipped ranged SourceObject")
        self.report["native_source_verified"] = True
        self.health = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        self.original_health = float(self.health.call_function("GetHealth"))
        self.baseline.call_function("SetRenderOpacity", 0.)
        # The parent differential's synthetic foreign Actor is not used as
        # evidence of a real LocalPlayer/Controller. Remove that test-only Actor.
        if valid(self.foreign):
            self.foreign.actor_destroy()
            self.foreign = None
        self.enter("native-first")

    def start_secondary(self):
        self.instance = self.statics.call_function("GetGameInstance", self.world)
        self.local_players_before = len(self.instance.get_property("LocalPlayers"))
        # Native CommonUI expects a Slate user before its next focus tick.
        # A harmless, unhandled native character event establishes the same
        # process-local user registration as a real input event, without
        # pretending that hardware input or a gameplay key was exercised.
        require(ue.FCharacterEvent("\x01", False).get_user_index() == 0, "legacy character-event default changed")
        event = ue.FCharacterEvent("\x01", False, ue.FSlateApplication.get_modifier_keys(), self.local_players_before)
        require(event.get_user_index() == self.local_players_before, "native character-event user index lost")
        ue.FSlateApplication.process_key_char_event(event)
        self.report["synthetic_native_slate_user_bootstrap"] = True
        self.report["native_slate_user_index"] = event.get_user_index()
        self.second_controller = self.statics.call_function("CreatePlayer", self.world, -1, True)
        require(valid(self.second_controller) and self.second_controller != self.controller and
                self.second_controller.call_function("IsLocalPlayerController"), "native secondary LocalPlayer creation failed")
        require(len(self.instance.get_property("LocalPlayers")) == self.local_players_before+1, "native LocalPlayers did not grow")
        require(self.statics.call_function("GetPlayerControllerID", self.second_controller) == self.report["native_slate_user_index"],
                "native local player input index differs from the registered Slate user")
        self.enter("native-secondary-ready")

    def secondary_ready(self):
        controller = self.second_controller
        pawn = controller.get_controlled_pawn()
        inventory = capture(controller) if valid(pawn) else None
        if inventory is None or inventory["magazine"] != 12:
            return
        cls = self.candidate.get_class()
        widgets, = ue.find_class("WidgetBlueprintLibrary").get_cdo().call_function("GetAllWidgetsOfClass", self.world, [], cls, False)
        matches = [widget for widget in widgets if widget.call_function("GetOwningPlayer") == controller]
        if len(matches) != 1:
            return
        target = matches[0]
        require(ue.get_mixin_profile(target) == "Python", "secondary real production failure UI is not Python")
        self.secondary_inventory = inventory
        self.secondary_health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        self.secondary_health_before = float(self.secondary_health.call_function("GetHealth"))
        asc = ability_system(pawn)
        _, quickbar = services(controller)
        item = quickbar.call_function("GetActiveSlotItem")
        specs = [spec for spec in asc.get_property("ActivatableAbilities").Items if valid(spec.Ability) and spec.Ability.get_class() == self.ability_class]
        if len(specs) != 1 or not valid(specs[0].SourceObject):
            return
        require(specs[0].SourceObject.call_function("GetInstigator") == item, "secondary reload source is not actual equipped item")
        before, original = state(self.candidate), state(self.baseline)
        deliveries, foreign = self.candidate._uep_failure_messages, self.candidate._uep_failure_foreign
        target_before = target._uep_failure_messages
        accepted = asc.call_function("TryActivateAbilityByClass", self.ability_class, False)
        first_id = int(self.controller.PlayerState.call_function("GetPlayerId"))
        second_id = int(controller.PlayerState.call_function("GetPlayerId"))
        self.report["cases"].append(dict(name=FOREIGN_CASE, native_second_local_player=True,
            native_player_ids_distinct=first_id != second_id, native_asc_accepted=accepted,
            target_native_deliveries=target._uep_failure_messages-target_before,
            first_owner_deliveries=self.candidate._uep_failure_messages-deliveries,
            first_owner_foreign_deliveries=self.candidate._uep_failure_foreign-foreign,
            first_owner_state_unchanged=state(self.candidate) == before, first_original_bp_state_unchanged=state(self.baseline) == original,
            native_payload_owner_correct=target._uep_failure_payload is not None and target._uep_failure_payload.PlayerController == controller))
        self.report["real_foreign_controller_tested"] = True
        self.enter("native-secondary-observe")

    def remove_secondary(self):
        if not valid(self.second_controller):
            return
        if hasattr(self, "secondary_inventory"):
            self.report["secondary_inventory_health_unchanged"] = capture(self.second_controller) == self.secondary_inventory and float(
                self.secondary_health.call_function("GetHealth")) == self.secondary_health_before
        self.statics.call_function("RemovePlayer", self.second_controller, True)
        self.report["native_secondary_player_removed"] = len(self.instance.get_property("LocalPlayers")) == self.local_players_before
        require(self.report["native_secondary_player_removed"], "native secondary LocalPlayer did not leave")
        self.second_controller = None

    def arm_cleanup(self):
        require(self.asc.call_function("TryActivateAbilityByClass", self.ability_class, False) is False,
                "native full-magazine cleanup request accepted")
        self.old_scope, self.old_proxy = self.candidate._uep_failure_scope, self.baseline.UEPOriginalFailureProxy
        ue.set_mixin_profile(self.candidate, "BlueprintFallback")
        ue.set_mixin_profile(self.baseline, "Python")
        # Capture cancellation while the UObject still exists. Native GC may
        # collect a successfully cancelled proxy before the later idle check.
        self.original_proxy_cancelled = not valid(self.old_proxy) or not self.old_proxy.call_function("IsActive")
        self.cancelled = [state(widget) for widget in self.widgets]
        self.enter("native-cleanup")

    def request(self, name):
        before = self.candidate._uep_failure_messages
        intros = failure.snapshot()["intros"]
        accepted = self.asc.call_function("TryActivateAbilityByClass", self.ability_class, False)
        require(accepted is False, "original full-magazine reload was not rejected")
        payload = self.candidate._uep_failure_payload
        require(payload is not None, "native GAS did not produce failure payload")
        equal = self.helper.call_function("SameFailureText", self.baseline.FailureReasonTextWidget, payload)
        require(type(equal) is tuple and len(equal) == 1 and type(equal[0]) is bool, "native text helper output differs")
        tags = [str(tag.TagName) for tag in payload.FailureTags.GameplayTags]
        row = dict(name=name, native_asc_accepted=accepted, native_deliveries=self.candidate._uep_failure_messages-before,
            same_class=self.candidate.get_class() == self.baseline.get_class(), native_opaque_text_equal=equal[0],
            native_payload_owner_correct=payload.PlayerController == self.controller, native_failure_tags=tags,
            python=state(self.candidate), blueprint=state(self.baseline), python_intros_delta=failure.snapshot()["intros"]-intros)
        require(row["native_deliveries"] == 1 and row["python"] == row["blueprint"] and equal[0], "native failure delivery/text differs")
        self.report["cases"].append(row)
        self.report["native_ability_producer_tested"] = True
        self.write()

    def tick(self, delta):
        if self.finished:
            return False
        try:
            require(time.monotonic()-self.started < 200., "native failure total timeout")
            if self.phase == "ready":
                self.ready()
                if self.phase != "ready":
                    self.setup()
                return True
            elapsed = time.monotonic()-self.phase_started
            require(elapsed < (35. if self.phase == "native-secondary-ready" else 12.), "native failure phase timeout: "+self.phase)
            if self.phase == "native-first" and elapsed > .25:
                self.first_request = time.monotonic()
                self.request(CASES[0])
                self.enter("native-repeat")
            elif self.phase == "native-repeat" and elapsed > .1:
                self.request(CASES[1])
                self.delay_before = failure.snapshot()["native_delay_callbacks"]
                self.enter("native-expiry")
            elif self.phase == "native-expiry":
                if elapsed > .25 and not self.report["images"]:
                    image = str(self.path.parent/"native-reload-failure.png")
                    self.report["images"].append(image)
                    ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                        'Shot SHOWUI -nosuffix filename="'+image+'"', self.controller)
                if all(state(widget)["visibility"] == 1 for widget in self.widgets):
                    self.report["cases"].append(dict(name=CASES[2], python=state(self.candidate), blueprint=state(self.baseline),
                        native_delay_callbacks=failure.snapshot()["native_delay_callbacks"]-self.delay_before,
                        elapsed_seconds=time.monotonic()-self.first_request))
                    if self.test_foreign:
                        self.start_secondary()
                    else:
                        self.arm_cleanup()
            elif self.phase == "native-secondary-ready":
                self.secondary_ready()
            elif self.phase == "native-secondary-observe" and elapsed > .35:
                image = str(self.path.parent/"native-real-foreign-controller.png")
                self.report["images"].append(image)
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="'+image+'"', self.controller)
                self.enter("native-secondary-remove")
            elif self.phase == "native-secondary-remove" and elapsed > .2:
                self.remove_secondary()
                self.arm_cleanup()
            elif self.phase == "native-cleanup" and elapsed > 1.25:
                self.report["cases"].append(dict(name=CASES[3], state_unchanged=[state(widget) for widget in self.widgets] == self.cancelled,
                    no_pending_animations=not any(any(animations(widget).values()) for widget in self.widgets),
                    old_python_scope_closed=self.old_scope.closed, original_proxy_inactive=self.original_proxy_cancelled and
                    (not valid(self.old_proxy) or not self.old_proxy.call_function("IsActive"))))
                self.finish()
                return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        try:
            self.remove_secondary()
            if hasattr(self, "original_inventory"):
                inventory, _ = services(self.controller)
                self.report["original_inventory_unchanged"] = capture(self.controller) == self.original_inventory and self.fingerprint == sorted(
                    path(item) for item in inventory.call_function("GetAllItems"))
                self.report["original_health_unchanged"] = float(self.health.call_function("GetHealth")) == self.original_health
            self.cleanup()
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
                           elapsed_seconds=time.monotonic()-self.started)
        self.write()
        (ue.log_error if error else ue.log)("UEP_FAILURE_NATIVE_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["shutdown"] = failure.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"
                validate(self.report)
            except Exception:
                self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_FAILURE_NATIVE_SHUTDOWN_"+self.report["status"].upper())


prefix = "-UEPAbilityFailureResult="
result = next(value[len(prefix):] for value in sys.argv if value.startswith(prefix))
validation = NativeFailure(result)
ticker = ue.add_ticker(validation.tick)
