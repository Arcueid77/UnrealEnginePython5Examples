"""Separate native Clear/Give probe; replacement handles are explicitly new."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_network_io import atomic_write
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.auto_respawn_activation_validation import Validation as Natural
from uep_lyra_abilities.auto_respawn_helpers_validation import instances, specs, native_state, DEATH
from uep_lyra_abilities.auto_respawn_helpers_mixin import CLASS
from uep_lyra_abilities.auto_respawn_helpers_contract import require
from uep_lyra_abilities import auto_respawn_activation_mixin as policy, auto_respawn_events_mixin as events, death_damage
from uep_lyra_abilities.auto_respawn_lifecycle_contract import validate, decode_ui_valid

PLAN = ("clear-live", "clear-pending-long", "clear-pending-short")


def delta(module, ability, before):
    after = module.instance_snapshot(ability)
    return {key: after.get(key, 0)-before.get(key, 0) for key in module.snapshot()}


def roots(asc):
    return [row for row in asc.get_property("ActivatableAbilities").Items
        if valid(row.Ability) and row.Ability.get_class().get_path_name() == CLASS]


def ui_probe(ability):
    result = ue.find_class("UIExtensionHandleFunctions").get_cdo().call_function("IsValid", ability.Extension)
    return dict(valid=decode_ui_valid(result), container=type(result).__name__, arity=len(result),
        return_type=type(result[0]).__name__, reference_type=type(result[1]).__name__)


def ui_valid(ability): return ui_probe(ability)["valid"]


class Lifecycle(Natural):
    def __init__(self, result):
        super().__init__(result)
        self.avatar_done = True
        self.report.update(mode="native-test-owned-end-clear-give", cases=[], native_end_ability_called_by_fixture=True,
            activation_natural_regression_only=False, full_auto_respawn_acceptance=False,
            native_clear_ability_called_by_fixture=True, native_give_ability_called_by_fixture=True,
            replacement_handle_claimed_identical=False, callback_replay=False, health_properties_written=False,
            ability_spec_properties_written=False, inventory_properties_written=False, fixture_recoveries=[],
            native_end_cancels_latent_actions=True)

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        ue.set_mixin_profile(self.ability, self.profile)
        spec, = roots(self.asc)
        source = spec.SourceObject
        require(source is None, "native lifecycle Give assumes original null SourceObject; capture/audit before extending")
        self.handle, self.handle_id, self.level, self.input_id = spec.Handle, int(spec.Handle.Handle), int(spec.Level), int(spec.InputID)
        self.baseline = specs(self.asc)
        self.old, self.old_proxy = self.ability, self.ability.get_property(policy.PROXY)
        self.counts_before = policy.instance_snapshot(self.old)
        self.events_before = events.instance_snapshot(self.old)
        self.old_pawn = self.controller.get_controlled_pawn().get_path_name()
        self.row = dict(name=self.name, profile=self.profile, old_handle=self.handle_id, level=self.level, input_id=self.input_id,
            original_source_object_is_null=source is None, old_pawn=self.old_pawn, native_type_preserved=self.old.get_class().get_path_name() == CLASS,
            ability_active_before=bool(self.old.get_property("bIsActive")), ui_before=ui_probe(self.old),
            proxy_active_before=bool(self.old_proxy.call_function("IsActive")), specs_before=copy.deepcopy(self.baseline))
        self.trial_started = self.game_time()
        if self.name == "clear-live": self.clear()
        else:
            death_damage.apply(self.asc, float(self.health.call_function("GetHealth")))
            require(self.health.call_function("GetHealth") == 0 and self.death.get_property("bIsActive"), "native lifecycle lethal damage missing")
            self.enter("wait-clear")

    def clear(self):
        # An instanced-per-actor ability remains valid in its native spec after
        # EndAbility. ClearAbility instead marks it garbage, even if rooted.
        self.old.call_function("K2_EndAbility")
        self.cleared_at = self.game_time()
        self.row.update(native_root_spec_count_after_end=len(roots(self.asc)), native_active_after_end=bool(self.old.get_property("bIsActive")),
            runtime_ended=bool(self.old.get_property(policy.ENDED)), listening_after_end=bool(self.old.IsListeningForReset),
            reflected_proxy_cleared=self.old.get_property(policy.PROXY) is None,
            old_proxy_active_after_end=valid(self.old_proxy) and bool(self.old_proxy.call_function("IsActive")), ui_after_end=ui_probe(self.old),
            health_listener_cleared=self.old.get_property("LastBoundHealthComponent") is None,
            events_at_end=delta(events, self.old, self.events_before))
        self.enter("observe-clear")

    def wait_clear(self):
        age = self.game_time()-self.trial_started
        if self.name == "clear-pending-long" and age > .3: self.clear()
        elif self.name == "clear-pending-short":
            observed = delta(events, self.old, self.events_before)
            long_done = observed["long_continuations"]+observed["fallback_long_continuations"]
            short_done = observed["short_continuations"]+observed["fallback_short_continuations"]
            if long_done:
                require(short_done == 0, "missed native short-delay cancellation window")
                self.clear()

    def observe_clear(self):
        age, since_clear = self.game_time()-self.trial_started, self.game_time()-self.cleared_at
        if self.name == "clear-pending-long" and age < 5.5: return
        if self.name != "clear-pending-long" and since_clear < .3: return
        state = native_state(self.controller)
        self.row.update(after_clear_policy=delta(policy, self.old, self.counts_before), after_clear_events=delta(events, self.old, self.events_before),
            no_new_pawn_before_fixture_recovery=state is None or state["pawn"] == self.old_pawn,
            observation_game_seconds=since_clear, elapsed_game_seconds=age,
            old_instance_valid_at_deadline=valid(self.old), native_root_spec_count_at_deadline=len(roots(self.asc)),
            old_instance_inactive_at_deadline=not bool(self.old.get_property("bIsActive")))
        require(self.row["no_new_pawn_before_fixture_recovery"], "cleared old ability restarted a new Pawn")
        before_remove = policy.snapshot()
        self.asc.call_function("ClearAbility", self.handle)
        after_remove = policy.snapshot()
        self.row["native_root_spec_count_after_clear"] = len(roots(self.asc))
        self.row["after_remove_policy"] = {key: after_remove[key]-before_remove[key] for key in before_remove}
        # OnRemoveAbility marks the old instance garbage. Do not access it or
        # try to keep it alive; only native ASC state/global counters survive.
        self.old = self.old_proxy = None
        self.recovery = dict(native_death_end_called=False, native_gamemode_restart_called=False, native_quickbar_recovery=False)
        if state is None or state["health"] <= 0:
            for death in instances(self.asc, ue.load_class(DEATH)):
                if death.get_property("bIsActive"):
                    death.call_function("K2_EndAbility"); self.recovery["native_death_end_called"] = True
            mode = self.statics.call_function("GetGameMode", self.world)
            mode.call_function("RequestPlayerRestartNextFrame", self.controller, True)
            self.recovery["native_gamemode_restart_called"] = True
        self.enter("recover-pawn")

    def recover_pawn(self):
        state = native_state(self.controller)
        if state is None or state["health"] <= 0 or state["death"] != 0 or not self.respawn_ready(): return
        current = specs(self.asc)
        expected = copy.deepcopy(self.baseline)
        expected["classes"].remove(CLASS)
        expected["persistent"] = [entry for entry in expected["persistent"] if entry[1] != CLASS]
        if current != expected and not self.recovery["native_quickbar_recovery"]:
            quick = self.controller.call_function("GetComponentByClass", ue.find_class("LyraQuickBarComponent"))
            active, empty = int(quick.call_function("GetActiveSlotIndex")), int(quick.call_function("GetNextFreeItemSlot"))
            require(active >= 0 and empty >= 0 and active != empty, "native equipment recovery needs original/empty slots")
            quick.call_function("SetActiveSlotIndex", empty); quick.call_function("SetActiveSlotIndex", active)
            self.recovery["native_quickbar_recovery"] = True
        if specs(self.asc) != expected: return
        require(len(roots(self.asc)) == 0, "unexpected native AutoRespawn root before test-owned grant")
        new_handle = self.asc.call_function("K2_GiveAbility", ue.load_class(CLASS), self.level, self.input_id)
        self.new_handle = int(new_handle.Handle)
        self.enter("recover-ability")

    def recover_ability(self):
        root_specs = roots(self.asc)
        if len(root_specs) != 1: return
        new, = instances(self.asc, ue.load_class(CLASS))
        proxy = new.get_property(policy.PROXY)
        if not (new.get_property("bIsActive") and valid(proxy) and proxy.call_function("IsActive") and ui_valid(new)): return
        restored = specs(self.asc)
        expected = copy.deepcopy(self.baseline)
        expected["persistent"] = sorted([self.new_handle if path == CLASS else handle, path] for handle, path in expected["persistent"])
        self.row.update(new_handle=self.new_handle, native_root_spec_count_after_give=len(root_specs),
            replacement_handle_differs=self.new_handle != self.handle_id, new_root_active=bool(new.get_property("bIsActive")),
            new_root_ui_valid=ui_valid(new), new_root_proxy_active=bool(proxy.call_function("IsActive")),
            new_root_policy=policy.instance_snapshot(new), specs_after=restored, specs_expected_after_native_regrant=expected,
            fixture_recovery=copy.deepcopy(self.recovery))
        require(restored == expected, "native lifecycle class/persistent model not restored with explicit new root handle")
        self.report["cases"].append(copy.deepcopy(self.row)); self.write()
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.enter("ready")

    def tick(self, delta_seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 300, "native clear/give total timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            else:
                require(time.monotonic()-self.phase_started < 30, "native clear/give phase timeout: "+self.phase)
                getattr(self, {"wait-clear": "wait_clear", "observe-clear": "observe_clear", "recover-pawn": "recover_pawn", "recover-ability": "recover_ability"}[self.phase])()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        if error is None:
            try:
                spec, = roots(self.asc)
                self.asc.call_function("ClearAbility", spec.Handle)
                self.report["test_owned_root_removed_before_exit"] = len(roots(self.asc)) == 0
            except Exception: error = traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error,
            fixture_roots=dict(added=0, released=0, active=0))
        self.write(); (ue.log_error if error else ue.log)("UEP_AUTO_RESPAWN_LIFECYCLE_"+("FAILED "+error if error else "DIFFERENTIAL_PASSED"))
        ue.request_exit()

    def finalize(self):
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_AUTO_RESPAWN_LIFECYCLE_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnLifecycleResult=")), None)
if result:
    validation = Lifecycle(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
