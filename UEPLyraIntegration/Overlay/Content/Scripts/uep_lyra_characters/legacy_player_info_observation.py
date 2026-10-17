"""Typed legacy helper calls; native teams/proxies stay untouched."""
import copy
import unreal_engine as ue
from .team_observer_observation import Context as ObserverContext, proxies, query, delta
from .team_cosmetics_validation import visual
from .outline_validation import gc, rgba
from . import legacy_player_info_mixin as policy, team_cosmetics_mixin as team_policy
from .team_observer_contract import require


class Context(ObserverContext):
    probe_path = "/Game/UEPValidation/BP_CharacterLegacyPlayerInfoProbe.BP_CharacterLegacyPlayerInfoProbe_C"

    def produce(self, key, profile, calls):
        actor = self.actors[key]; ue.set_mixin_profile(actor, profile)
        self.key, self.profile, self.calls, self.properties = key, profile, calls, []
        self.before, self.team_before = copy.deepcopy(policy.evidence(actor)), copy.deepcopy(team_policy.evidence(actor))
        self.native_query, self.proxy_paths = query(actor), set(proxies())
        for _ in range(calls):
            marker = self.devices.marker(); self.caller.call_function("Refresh", actor)
            self.properties.extend(self.devices.collect(marker))
        require(set(proxies()) == self.proxy_paths, "legacy helper unexpectedly created/cancelled native team observers")

    def complete(self):
        actor = self.actors[self.key]
        require(query(actor) == self.native_query, "legacy helper changed native team state")
        gc()
        return dict(profile=str(ue.get_mixin_profile(actor)), typed_bp_refresh_calls=self.calls,
            counters={key: value-self.before[key] for key, value in policy.evidence(actor).items()},
            team_counters=delta(team_policy.evidence(actor), self.team_before, "last_call"),
            helper_payload=copy.deepcopy(team_policy.evidence(actor)["last_call"]), native_team_query=self.native_query,
            visual=visual(actor), native_role=int(actor.call_function("GetLocalRole")), native_team_state_unchanged=True,
            expected_outline_color=rgba(ue.FLinearColor(*team_policy.FALLBACK)),
            native_device_properties_created=len(self.properties), native_device_properties=self.devices.rows(self.properties), native_scheduler_removed_owned_properties=True)

    def settle_collection(self, row):
        row.update(native_collection_checked_after_engine_ticks=True, native_listener_proxy_set_unchanged=set(proxies()) == self.proxy_paths)
        return row
