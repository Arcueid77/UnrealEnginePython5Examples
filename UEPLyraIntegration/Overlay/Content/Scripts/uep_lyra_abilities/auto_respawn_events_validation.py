"""Independent real native message payload/delivery observations; no replay."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from .auto_respawn_listeners_validation import Validation as ListenerValidation
from . import auto_respawn_events_mixin as events
from .auto_respawn_helpers_contract import require
from . import auto_respawn_helpers_mixin as helpers_policy
from .auto_respawn_helpers_validation import native_state, specs, counters
from .auto_respawn_events_contract import validate


class EventEvidence:
    def __init__(self, *args):
        super().__init__(*args)
        self.event_observer = None
        self.event_scopes_created = self.event_scopes_closed = 0
        self.report.update(death_listener_timer_restart_business_migrated=True, timer_restart_business_migrated=True,
            death_avatar_event_business_migrated=True, original_two_native_delay_nodes_reused=True,
            activation_reset_ui_removal_business_migrated=False, duration_completion_broadcast_by_fixture=False)

    def query(self): return dict(super().query(), should_finish_restart=bool(self.ability.ShouldFinishRestart))

    def open_event_observer(self):
        self.event_messages = []
        self.event_observer = SubscriptionScope(); self.event_scopes_created += 1
        reader = ue.load_class(events.ADAPTER).get_cdo()
        def read(proxy, suffix):
            payload, success = reader.call_function("Read"+suffix, proxy)
            require(success is True, "actual native respawn payload extraction failed")
            return payload
        def received(channel, payload, suffix):
            owner = payload.Instigator
            row = dict(channel=str(channel.TagName), player_id=int(owner.PlayerId) if owner is not None else -1,
                owner_matches=owner == self.controller.PlayerState)
            if suffix == "Duration": row["duration"] = float(payload.Duration)
            else:
                row.update(verb=str(payload.Verb.TagName), magnitude=float(payload.Magnitude), target_is_null=payload.Target is None,
                    instigator_tags=[str(tag.TagName) for tag in payload.InstigatorTags.GameplayTags],
                    target_tags=[str(tag.TagName) for tag in payload.TargetTags.GameplayTags],
                    context_tags=[str(tag.TagName) for tag in payload.ContextTags.GameplayTags])
            self.event_messages.append(row)
        for suffix, channel, struct in (("Duration", events.DURATION, "LyraInteractionDurationMessage"), ("Verb", events.COMPLETED, "LyraVerbMessage")):
            self.event_observer.listen_gameplay_message(self.ability, channel, ue.find_struct(struct),
                lambda proxy, name=suffix: read(proxy, name), lambda channel, payload, name=suffix: received(channel, payload, name))

    def close_event_observer(self):
        observer, self.event_observer = self.event_observer, None
        if observer is not None: observer.close(); self.event_scopes_closed += 1

    def trial_begin_evidence(self):
        super().trial_begin_evidence()
        self.event_before = events.instance_snapshot(self.ability)
        self.open_event_observer()

    def trial_end_evidence(self):
        super().trial_end_evidence()
        after = events.instance_snapshot(self.ability); self.close_event_observer()
        self.row.update(event_messages=copy.deepcopy(self.event_messages), event_observer_closed=True,
            native_player_id=int(self.controller.PlayerState.PlayerId),
            event_counters={key: after.get(key, 0)-self.event_before.get(key, 0) for key in events.snapshot()})

    def foreign_begin_evidence(self): self.open_event_observer()
    def foreign_end_evidence(self, row):
        self.close_event_observer(); row.update(event_messages=copy.deepcopy(self.event_messages), event_observer_closed=True)

    def finish(self, error=None):
        self.close_event_observer(); super().finish(error)

    def validate_report(self): return validate(self.report)

    def finalize(self):
        self.close_event_observer()
        self.report["event_fixture_shutdown"] = dict(created=self.event_scopes_created,
            closed=self.event_scopes_closed, active=int(self.event_observer is not None))
        super().finalize()


class Validation(EventEvidence, ListenerValidation):
    def __init__(self, result):
        super().__init__(result)
        self.avatar_trial = False; self.avatar_done = False; self.avatar_index = 0
        self.report.update(avatar_endplay_cases=[], native_avatar_destroy_called_by_fixture=False)

    def finish(self, error=None):
        if error is None and not self.avatar_done and not self.avatar_trial:
            self.avatar_trial = True; self.enter("ready"); return
        super().finish(error)

    def begin(self):
        if not self.avatar_trial: return super().begin()
        self.name, self.profile = "forced-native-avatar-endplay", ("BlueprintFallback", "Python")[self.avatar_index]
        ue.set_mixin_profile(self.ability, self.profile)
        self.before = helpers_policy.instance_snapshot(self.ability)
        self.trial_begin_evidence()
        self.old_pawn, self.old_death, self.trial_started = self.pawn.get_path_name(), self.death, self.game_time()
        self.row = dict(profile=self.profile, old_pawn=self.old_pawn, health_before=float(self.health.call_function("GetHealth")),
            native_type_preserved=self.ability.get_class().get_path_name() == helpers_policy.CLASS,
            native_auto_respawn_active=bool(self.ability.get_property("bIsActive")),
            native_owner_role=int(self.pawn.call_function("GetLocalRole")), native_death_active_before=bool(self.death.get_property("bIsActive")),
            specs_before=copy.deepcopy(self.original_specs))
        self.pawn.call_function("K2_DestroyActor")
        self.report["native_avatar_destroy_called_by_fixture"] = True
        self.enter("avatar_respawn")

    def observe_avatar(self):
        state = native_state(self.controller)
        if state is None or state["pawn"] == self.old_pawn or state["health"] <= 0 or state["death"] != 0 or not self.respawn_ready(): return
        if "specs_at_restart" not in self.row:
            self.row["specs_at_restart"] = specs(self.asc)
            # Bare K2_DestroyActor bypasses the normal death/inventory path.
            # Preserve that original observation, then restore equipment through
            # native QuickBar RPCs; never write/grant any ability or inventory.
            required = self.row["specs_at_restart"] != self.original_specs
            quickbar = self.controller.call_function("GetComponentByClass", ue.find_class("LyraQuickBarComponent"))
            require(valid(quickbar), "native QuickBar required for Avatar probe cleanup")
            before = [item.get_path_name() if valid(item) else None for item in quickbar.call_function("GetSlots")]
            active = int(quickbar.call_function("GetActiveSlotIndex"))
            recovery = dict(required=required, slot_before=active, slot_after=active, slots_unchanged=True, calls=[])
            if required:
                empty = int(quickbar.call_function("GetNextFreeItemSlot"))
                require(0 <= active < len(before) and before[active] is not None and
                    0 <= empty < len(before) and empty != active and before[empty] is None,
                    "native Avatar cleanup requires its original item and a real empty slot")
                quickbar.call_function("SetActiveSlotIndex", empty)
                quickbar.call_function("SetActiveSlotIndex", active)
                recovery.update(calls=[empty, active], slot_after=int(quickbar.call_function("GetActiveSlotIndex")),
                    slots_unchanged=before == [item.get_path_name() if valid(item) else None for item in quickbar.call_function("GetSlots")])
            self.row["native_quickbar_recovery"] = recovery
        if specs(self.asc) != self.original_specs: return
        self.row.update(new_pawn=state["pawn"], respawn_health=state["health"], native_elapsed=self.game_time()-self.trial_started,
            native_auto_respawn_still_active=bool(self.ability.get_property("bIsActive")),
            native_death_active_after=bool(self.old_death.get_property("bIsActive")), specs_unchanged=specs(self.asc) == self.original_specs,
            specs_after=specs(self.asc),
            delay_unchanged=float(self.ability.RespawnDelayDuration) == self.original_delay, after_query=self.query(),
            counters=counters(self.ability, self.before))
        self.trial_end_evidence()
        self.report["avatar_endplay_cases"].append(copy.deepcopy(self.row)); self.write()
        self.avatar_index += 1
        if self.avatar_index == 2:
            self.avatar_done = True; self.finish()
        else: self.enter("ready")

    def tick(self, delta):
        if self.phase != "avatar_respawn": return super().tick(delta)
        try:
            require(time.monotonic()-self.phase_started < 30, "actual native Avatar EndPlay restart timeout")
            self.observe_avatar(); return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnHelpersResult=")), None)
if result and "-UEPAutoRespawnEvents" in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
