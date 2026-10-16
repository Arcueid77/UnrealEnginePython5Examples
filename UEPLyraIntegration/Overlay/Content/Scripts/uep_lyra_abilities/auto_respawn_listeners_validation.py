"""Actual native listener delivery across clear/rebind, death and Pawn restart."""
import atexit
import sys
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from . import auto_respawn_listeners_mixin as listeners
from .auto_respawn_helpers_validation import Validation as Native
from .auto_respawn_helpers_contract import require
from .auto_respawn_listeners_contract import validate


class ListenerEvidence:
    def __init__(self, *args):
        super().__init__(*args)
        self.listener_observer = None
        self.listener_scopes_created = self.listener_scopes_closed = 0
        self.report.update(death_listener_orchestration_migrated=True, timer_restart_business_migrated=False,
            foreign_native_delegate_delivery_tested=True, synthetic_delegate_broadcast=False)

    def listener_cache(self):
        pawn = self.controller.get_controlled_pawn()
        health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        cached = self.ability.get_property("LastBoundHealthComponent")
        return dict(avatar_matches=self.ability.get_property("LastBoundAvatarActor") == pawn,
            health_matches=cached == health, health_is_null=not valid(cached))

    def query(self):
        return dict(super().query(), listener_cache=self.listener_cache())

    def close_listener_observer(self):
        observer, self.listener_observer = self.listener_observer, None
        if observer is not None:
            observer.close(); self.listener_scopes_closed += 1

    def trial_begin_evidence(self):
        self.listener_events = []
        self.listener_observer = SubscriptionScope(); self.listener_scopes_created += 1
        self.listener_observer.bind_event(self.health, "OnDeathStarted", lambda actor: self.listener_events.append("death"))
        self.listener_observer.bind_event(self.pawn, "OnEndPlay", lambda actor, reason: self.listener_events.append("endplay"))
        was_active = bool(self.ability.get_property("bIsActive"))
        self.ability.call_function("ClearDeathListener")
        cleared = self.listener_cache()
        self.listener_probe = dict(first_clear_health_null=cleared["health_is_null"], first_clear_retains_avatar=cleared["avatar_matches"])
        alternate = "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback"
        ue.set_mixin_profile(self.ability, alternate)
        self.ability.call_function("BindDeathListener")
        self.listener_probe["alternate_bind_matches"] = self.listener_cache() == dict(avatar_matches=True, health_matches=True, health_is_null=False)
        self.ability.call_function("BindDeathListener")
        self.listener_probe["repeat_bind_matches"] = self.listener_cache() == dict(avatar_matches=True, health_matches=True, health_is_null=False)
        ue.set_mixin_profile(self.ability, self.profile)
        self.ability.call_function("ClearDeathListener")
        self.listener_probe["cross_profile_clear_health_null"] = self.listener_cache()["health_is_null"]
        self.ability.call_function("BindDeathListener")
        self.listener_probe["restored_bind_matches"] = self.listener_cache() == dict(avatar_matches=True, health_matches=True, health_is_null=False)
        self.listener_probe["native_lifetime_unchanged"] = bool(self.ability.get_property("bIsActive")) == was_active
        require(all(self.listener_probe.values()), "native clear/rebind/cross-Profile probe failed")
        # Trial counters exclude explicit probe operations. The actual original
        # OnDeathStarted and OnPawnAvatarSet events must produce the next calls.
        self.listener_before = listeners.instance_snapshot(self.ability)

    def trial_end_evidence(self):
        after = listeners.instance_snapshot(self.ability)
        self.close_listener_observer()
        self.row.update(listener_probe=dict(self.listener_probe), listener_foreign_events=list(self.listener_events),
            listener_observer_closed=self.listener_observer is None,
            listener_counters={key: after.get(key, 0)-self.listener_before.get(key, 0) for key in listeners.snapshot()})

    def finish(self, error=None):
        self.close_listener_observer(); super().finish(error)

    def validate_report(self): return validate(self.report)

    def finalize(self):
        self.close_listener_observer()
        self.report["listener_fixture_shutdown"] = dict(created=self.listener_scopes_created,
            closed=self.listener_scopes_closed, active=int(self.listener_observer is not None))
        super().finalize()


class Validation(ListenerEvidence, Native): pass


result = next((value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPAutoRespawnHelpersResult=")), None)
if result and "-UEPAutoRespawnListeners" in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
