"""Test-only native Cue/typed UI observation; always forward the original Cue."""
import copy
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from .death_observation import cue, path
from .dash_tasks_mixin import instance_snapshot, ADAPTER
from .dash_rpc_input_contract import require

CUE = "/ShooterCore/GameplayCues/GCNL_Dash.GCNL_Dash_C"


def delta(after, before): return {key: after.get(key, 0)-before.get(key, 0) for key in set(after)|set(before)}


class Observer:
    def __init__(self, world):
        self.world = world; self.rows, self.messages, self.errors = [], [], []
        self.target = self.ability = None; self.closed = False; self.scope = SubscriptionScope()
        self.dedicated = bool(ue.find_class("KismetSystemLibrary").get_cdo().call_function("IsDedicatedServer", world))
        self.cls = ue.load_class(CUE)
        require(not any(row["target_class"] == self.cls for row in ue.get_registered_mixins()), "do not replace a production Dash Cue mixin")
        self.original = self.cls.get_cdo().find_function("OnBurst")
        owner = self
        class ObserveCue:
            def OnBurst(self, Target, Parameters, SpawnResults):
                try:
                    if path(Target) == owner.target:
                        owner.rows.append(dict(cue(Target, Parameters), game_time=owner.game_time()))
                except Exception: owner.errors.append(traceback.format_exc())
                return self.call_mixin_original("OnBurst", Target, Parameters, SpawnResults)
        ue.register_mixin_profile(self.cls, "UEPDashProducerObserve", ObserveCue, make_default=True)
        try:
            self.reader = ue.load_class(ADAPTER).get_cdo()
            def read(proxy):
                payload, success = self.reader.call_function("ReadDuration", proxy)
                require(success is True, "native Dash typed duration extraction failed"); return payload
            def received(channel, payload):
                try:
                    if path(payload.Instigator) == self.target:
                        self.messages.append(dict(instigator=path(payload.Instigator), duration=float(payload.Duration),
                            native_cooldown=float(self.ability.call_function("GetCooldownTimeRemaining")), game_time=self.game_time()))
                except Exception: self.errors.append(traceback.format_exc())
            self.scope.listen_gameplay_message(world, "Ability.Dash.Duration.Message", ue.find_struct("LyraInteractionDurationMessage"), read, received)
        except Exception:
            self.close(); raise
    def game_time(self): return float(ue.find_class("GameplayStatics").get_cdo().call_function("GetTimeSeconds", self.world))
    def begin(self, pawn, ability):
        self.target, self.ability = path(pawn), ability
        self.before = instance_snapshot(ability); self.start_cue, self.start_ui = len(self.rows), len(self.messages)
    def finish(self):
        return dict(target=self.target, stats=delta(instance_snapshot(self.ability), self.before),
            cues=copy.deepcopy(self.rows[self.start_cue:]), ui=copy.deepcopy(self.messages[self.start_ui:]),
            observer_errors=copy.deepcopy(self.errors), native_dedicated_server=self.dedicated,
            actual_task_scope_closed=getattr(self.ability, "_uep_dash_tasks_scope", None) is None)
    def close(self):
        if self.closed: return
        self.closed = True
        try: self.scope.close()
        finally:
            require(ue.unregister_mixin(self.cls) and self.cls.get_cdo().find_function("OnBurst") == self.original,
                "native Dash Cue observer function did not restore")
        self.ability = None
    def shutdown(self): return dict(scope_closed=self.scope.closed, cue_function_restored=self.cls.get_cdo().find_function("OnBurst") == self.original, errors=copy.deepcopy(self.errors))
