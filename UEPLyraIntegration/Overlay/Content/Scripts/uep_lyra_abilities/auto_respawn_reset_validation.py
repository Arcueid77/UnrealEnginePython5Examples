"""Existing native Reset ability -> typed original listener -> BP/Python policy."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayEventData
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_helpers_validation import Validation as Native, instances, specs, native_state
from .auto_respawn_helpers_mixin import CLASS
from .auto_respawn_helpers_contract import require
from .auto_respawn_events_validation import EventEvidence
from .auto_respawn_lifecycle_validation import ui_valid
from . import auto_respawn_activation_mixin as activation, auto_respawn_events_mixin as events, death_damage
from .auto_respawn_reset_contract import PLAN, RESET_CLASS, CHANNEL, validate

PROBE = "/Game/UEPValidation/BP_AutoRespawnResetProbe.BP_AutoRespawnResetProbe_C"


def counts(module, ability, before):
    after = module.instance_snapshot(ability)
    return {key: after.get(key, 0)-before.get(key, 0) for key in module.snapshot()}


class ResetTrials(EventEvidence, Native):
    def __init__(self, result):
        super().__init__(result)
        self.reset_observer = None; self.observers_created = self.observers_closed = 0
        self.report.update(native_reset_producer_tested=True, reset_broadcast_by_fixture=False,
            full_auto_respawn_acceptance=False)

    def open_observer(self):
        self.open_event_observer()
        self.reset_messages = []; self.reset_observer = SubscriptionScope(); self.observers_created += 1
        reader = ue.load_class(PROBE).get_cdo()
        def read(proxy):
            payload, success = reader.call_function("ReadReset", proxy)
            require(success is True, "native typed Reset probe extraction failed")
            return payload
        def received(channel, payload):
            owner = payload.OwnerPlayerState
            require(valid(owner) and owner.is_a(ue.find_class("LyraPlayerState")), "native Reset payload owner is not a live PlayerState")
            self.reset_messages.append(dict(channel=str(channel.TagName), player_id=int(owner.PlayerId), owner_matches=owner == self.controller.PlayerState))
        self.reset_observer.listen_gameplay_message(self.ability, CHANNEL, ue.find_struct("LyraPlayerResetMessage"), read, received)

    def close_observer(self):
        self.close_event_observer()
        observer, self.reset_observer = self.reset_observer, None
        if observer is not None: observer.close(); self.observers_closed += 1

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        self.begin_reset()

    def begin_reset(self):
        self.prepare_reset()
        if "pending-long" in self.name:
            death_damage.apply(self.asc, self.row["health_before"])
            require(self.health.call_function("GetHealth") == 0 and self.death.get_property("bIsActive"), "real native death required before Reset")
            self.enter("wait-reset")
        else: self.trigger_reset()

    def prepare_reset(self):
        ue.set_mixin_profile(self.ability, self.profile)
        self.activation_before, self.event_before = activation.instance_snapshot(self.ability), events.instance_snapshot(self.ability)
        reset_specs = [item for item in self.asc.get_property("ActivatableAbilities").Items if valid(item.Ability) and item.Ability.get_class().get_path_name() == RESET_CLASS]
        require(len(reset_specs) == 1, "one already granted native Reset spec required")
        self.old_pawn = self.pawn.get_path_name(); self.trial_started = self.game_time()
        self.row = dict(name=self.name, profile=self.profile, player_id=int(self.controller.PlayerState.PlayerId), old_pawn=self.old_pawn,
            health_before=float(self.health.call_function("GetHealth")), specs_before=copy.deepcopy(self.original_specs),
            native_type_preserved=self.ability.get_class().get_path_name() == CLASS,
            native_reset_class=reset_specs[0].Ability.get_class().get_path_name(), native_reset_existing_specs=len(reset_specs),
            auto_active_before=bool(self.ability.get_property("bIsActive")), ui_valid_before=ui_valid(self.ability),
            original_delay_written=False, callbacks_replayed=False)
        self.open_observer()

    def trigger_reset(self):
        if "switch" in self.name: ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
        tag = GameplayTag(TagName="GameplayEvent.RequestReset")
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor", self.controller.PlayerState,
            tag, GameplayEventData(EventTag=tag, Instigator=self.controller.PlayerState, Target=self.controller.PlayerState))
        self.row.update(trigger_entry="SendGameplayEventToActor(GameplayEvent.RequestReset)", native_reset_requests=1)
        self.enter("reset-respawn")

    def observe_reset(self):
        state = native_state(self.controller)
        elapsed = self.game_time()-self.trial_started
        if state is None or state["pawn"] == self.old_pawn or state["health"] <= 0 or state["death"] != 0 or not self.respawn_ready(): return
        if "specs_at_restart" not in self.row:
            self.row["specs_at_restart"] = specs(self.asc)
            # Reset may bypass the equipment re-grant route, exactly as bare
            # Avatar destruction does. Preserve raw model; restore via native UI RPC.
            needed = self.row["specs_at_restart"] != self.original_specs
            self.row["native_quickbar_recovery"] = dict(required=needed, calls=[])
            if needed and getattr(self, "allow_native_equipment_recovery", True):
                quick = self.controller.call_function("GetComponentByClass", ue.find_class("LyraQuickBarComponent"))
                original, empty = int(quick.call_function("GetActiveSlotIndex")), int(quick.call_function("GetNextFreeItemSlot"))
                require(original >= 0 and empty >= 0 and original != empty, "native Reset recovery needs original and empty slots")
                quick.call_function("SetActiveSlotIndex", empty); quick.call_function("SetActiveSlotIndex", original)
                self.row["native_quickbar_recovery"]["calls"] = [empty, original]
        if specs(self.asc) != self.original_specs or elapsed < (5.7 if "pending-long" in self.name else .3): return
        self.close_observer()
        proxy = self.ability.get_property(activation.PROXY)
        self.row.update(new_pawn=state["pawn"], health_after=state["health"], death_after=state["death"], elapsed_game_seconds=elapsed,
            specs_after=specs(self.asc), auto_active_after=bool(self.ability.get_property("bIsActive")),
            final_profile=str(ue.get_mixin_profile(self.ability)), runtime_ended=bool(self.ability.get_property(activation.ENDED)),
            reset_proxy_active=valid(proxy) and bool(proxy.call_function("IsActive")), ui_valid_after=ui_valid(self.ability),
            delay_unchanged=float(self.ability.RespawnDelayDuration) == self.original_delay,
            reset_messages=copy.deepcopy(self.reset_messages), event_messages=copy.deepcopy(self.event_messages), observer_closed=True,
            activation_counters=counts(activation, self.ability, self.activation_before), event_counters=counts(events, self.ability, self.event_before))
        self.complete_reset()

    def complete_reset(self):
        self.report["cases"].append(copy.deepcopy(self.row)); self.write(); self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.enter("ready")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 260, "native Reset total timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "wait-reset":
                if self.game_time()-self.trial_started >= .3: self.trigger_reset()
            elif self.phase == "reset-respawn":
                require(time.monotonic()-self.phase_started < 30, "native Reset restart timeout")
                self.observe_reset()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.close_observer(); self.finished = True
        try:
            if hasattr(self, "original_profile") and valid(self.ability):
                ue.set_mixin_profile(self.ability, self.original_profile)
                self.report["original_profile_restored"] = str(ue.get_mixin_profile(self.ability)) == self.original_profile
                self.report["original_specs_restored"] = specs(self.asc) == self.original_specs
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write(); (ue.log_error if error else ue.log)("UEP_AUTO_RESPAWN_RESET_"+("FAILED "+error if error else "DIFFERENTIAL_PASSED"))
        ue.request_exit()

    def finalize(self):
        self.close_observer()
        self.report["observer_shutdown"] = dict(created=self.observers_created, closed=self.observers_closed, active=int(self.reset_observer is not None))
        if self.report["status"] == "awaiting_shutdown":
            try: self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_AUTO_RESPAWN_RESET_SHUTDOWN_"+self.report["status"].upper())


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnResetResult=")), None)
if result:
    validation = ResetTrials(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
