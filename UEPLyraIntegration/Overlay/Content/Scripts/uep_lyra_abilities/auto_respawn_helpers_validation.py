"""Real lethal GAS -> original AutoRespawn BP -> three routed Python helpers."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import auto_respawn_helpers_mixin as policy, death_damage
from .auto_respawn_helpers_contract import PLAN, require, validate, spec_model

DEATH = "/Game/Characters/Heroes/Abilities/GA_Hero_Death.GA_Hero_Death_C"


def instances(asc, cls):
    return [value for spec in asc.get_property("ActivatableAbilities").Items
        if valid(spec.Ability) and spec.Ability.get_class() == cls
        for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]


def specs(asc):
    return spec_model([(int(spec.Handle.Handle), spec.Ability.get_class().get_path_name())
        for spec in asc.get_property("ActivatableAbilities").Items if valid(spec.Ability)])


def native_state(controller):
    pawn = controller.get_controlled_pawn()
    if not valid(pawn): return None
    health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
    if not valid(health): return None
    return dict(pawn=pawn.get_path_name(), health=float(health.call_function("GetHealth")),
        death=int(health.call_function("GetDeathState")), player_id=int(controller.PlayerState.PlayerId))


def counters(ability, before):
    after = policy.instance_snapshot(ability)
    return {key: after.get(key, 0)-before.get(key, 0) for key in policy.snapshot()}


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.index, self.sides, self.finished = 0, [], False
        self.report = dict(schema_version=1, status="running", error=None, cases=[],
            full_acceptance=False, network_acceptance=False, packaged_runtime=False, physical_input_tested=False,
            death_listener_timer_restart_business_migrated=False, original_delay_written=False,
            ability_granted_by_probe=False, death_event_sent_by_probe=False, helper_end_called_by_probe=False,
            health_properties_written=False, callback_replay=False, real_lethal_gas_damage=False,
            original_profile_restored=False, original_specs_restored=False)
        self.statics = ue.find_class("GameplayStatics").get_cdo()

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()
    def write(self): atomic_write(self.path, self.report)
    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))

    def attach(self, world, controller):
        pawn = controller.get_controlled_pawn()
        if not valid(pawn): return False
        asc = ability_system(pawn)
        if not valid(asc): return False
        found, deaths = instances(asc, ue.load_class(policy.CLASS)), instances(asc, ue.load_class(DEATH))
        self.report["attach_readiness"] = dict(auto_respawn_instances=len(found), death_instances=len(deaths),
            require_auto_active=getattr(self, "require_auto_active", True))
        if len(found) != 1 or len(deaths) != 1 or deaths[0].get_property("bIsActive"): return False
        if getattr(self, "require_auto_active", True) and not found[0].get_property("bIsActive"): return False
        health = pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if not valid(health) or health.call_function("IsDeadOrDying") or health.call_function("GetHealth") <= 0: return False
        self.world, self.controller, self.pawn, self.asc, self.health = world, controller, pawn, asc, health
        self.ability, self.death = found[0], deaths[0]
        if not hasattr(self, "original_profile"):
            self.original_profile, self.original_specs = str(ue.get_mixin_profile(self.ability)), specs(asc)
            self.original_delay = float(self.ability.RespawnDelayDuration)
        return True

    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            snap = bridge.call_function("CaptureSnapshot")
            self.report["last_readiness"] = dict(experience=bool(snap.bExperienceLoaded), input=bool(snap.bHeroInputReady),
                ability_system=bool(snap.bAbilitySystemReady), health_ready=bool(snap.bHealthReady),
                immune=bool(snap.bDamageImmune), health=float(snap.Health),
                require_local_playing_phase=getattr(self, "require_local_playing_phase", True))
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bAbilitySystemReady and
                snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): continue
            if getattr(self, "require_local_playing_phase", True):
                phases = ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem", world, ue.find_class("LyraGamePhaseSubsystem"))
                active = valid(phases) and phases.call_function("IsPhaseActive", GameplayTag(TagName="ShooterGame.GamePhase.Playing"))
                self.report["last_readiness"]["local_playing"] = bool(active)
                if not active: continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if self.attach(world, controller): self.begin(); return

    def query(self):
        owner = self.ability.call_function("GetOwningPlayerState")
        dead, = self.ability.call_function(policy.DEAD_QUERY)
        return dict(owner_matches=owner == self.asc.call_function("GetOwner") == self.controller.PlayerState,
            dead=dead)

    def trial_begin_evidence(self): pass
    def trial_end_evidence(self): pass
    def foreign_begin_evidence(self): pass
    def foreign_end_evidence(self, row): pass
    def validate_report(self): return validate(self.report)

    def authority_state(self):
        # K2_HasAuthority reads CurrentActivationInfo, not the Pawn's net role.
        # Observe both without activating the ability or changing either value.
        return dict(ability_authority=bool(self.ability.call_function("K2_HasAuthority")),
            activation_mode=int(self.ability.get_property("CurrentActivationInfo").ActivationMode),
            pawn_role=int(self.controller.get_controlled_pawn().call_function("GetLocalRole")),
            game_mode_available=valid(self.statics.call_function("GetGameMode", self.world)))

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        ue.set_mixin_profile(self.ability, self.profile)
        self.before, self.trial_started = policy.instance_snapshot(self.ability), self.game_time()
        self.old_pawn, self.old_death = self.pawn.get_path_name(), self.death
        self.switched, self.paused, self.unpaused = False, False, False
        self.trial_begin_evidence()
        self.row = dict(living_query=self.query(), old_pawn=self.old_pawn,
            health_before=float(self.health.call_function("GetHealth")), original_delay=float(self.ability.RespawnDelayDuration),
            native_type_preserved=self.ability.get_class().get_path_name() == policy.CLASS,
            native_auto_respawn_active=bool(self.ability.get_property("bIsActive")),
            native_net_policy=int(self.ability.NetExecutionPolicy), native_security_policy=int(self.ability.NetSecurityPolicy),
            native_owner_role=int(self.pawn.call_function("GetLocalRole")), profile_switched=False, native_pause_observed=False,
            specs_before=copy.deepcopy(self.original_specs), native_authority_before=self.authority_state())
        death_damage.apply(self.asc, self.row["health_before"])
        require(self.health.call_function("GetHealth") == 0 and self.death.get_property("bIsActive"), "native lethal death not observed")
        self.row.update(health_after_damage=float(self.health.call_function("GetHealth")), dead_query=self.query(),
            native_death_active_observed=True, native_authority_at_death=self.authority_state())
        self.report["real_lethal_gas_damage"] = True
        self.enter("respawn")

    def observe(self):
        elapsed = self.game_time()-self.trial_started
        if self.name == "profile-switch-during-death" and not self.switched and elapsed > .3:
            ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
            self.switched = True; self.row["profile_switched"] = True
            require(bool(self.ability.get_property("bIsActive")) == self.row["native_auto_respawn_active"] and
                self.old_death.get_property("bIsActive"), "helper-only Profile switch changed native lifecycle")
        if self.name == "paused-world-time" and not self.paused and elapsed > .3:
            require(self.statics.call_function("SetGamePaused", self.world, True), "native pause refused")
            self.paused, self.pause_started, self.pause_game_time = True, time.monotonic(), self.game_time()
            return
        if self.paused and not self.unpaused:
            require(abs(self.game_time()-self.pause_game_time) < .02 and self.old_death.get_property("bIsActive"), "native delay advanced during pause")
            if time.monotonic()-self.pause_started < .3: return
            require(self.statics.call_function("SetGamePaused", self.world, False), "native unpause refused")
            self.unpaused = True; self.row["native_pause_observed"] = True
        current = native_state(self.controller)
        if current is None or current["pawn"] == self.old_pawn or current["health"] <= 0 or current["death"] != 0: return
        if not self.respawn_ready(): return
        self.row.update(new_pawn=current["pawn"], respawn_health=current["health"], native_elapsed=elapsed,
            native_death_ended=not self.old_death.get_property("bIsActive"),
            native_auto_respawn_still_active=bool(self.ability.get_property("bIsActive")),
            native_authority_after=self.authority_state(),
            after_query=self.query(), delay_unchanged=float(self.ability.RespawnDelayDuration) == self.original_delay,
            specs_unchanged=specs(self.asc) == self.original_specs, specs_after=specs(self.asc), counters=counters(self.ability, self.before))
        self.trial_end_evidence()
        self.complete_trial()

    def respawn_ready(self):
        snap = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", self.world).call_function("CaptureSnapshot")
        return bool(snap.bHeroInputReady and not snap.bDamageImmune)

    def complete_trial(self):
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1]))
            self.sides = []; ue.log("UEP_AUTO_RESPAWN_HELPERS_CASE_PASSED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.enter("ready")
        self.write()

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 220, "native AutoRespawn helper total timeout: "+self.phase)
            if self.phase == "ready": self.ready()
            elif self.phase == "respawn":
                require(time.monotonic()-self.phase_started < 30, "native AutoRespawn restart timeout")
                self.observe()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            if getattr(self, "paused", False) and not self.unpaused: self.statics.call_function("SetGamePaused", self.world, False)
            if hasattr(self, "original_profile") and valid(self.ability):
                ue.set_mixin_profile(self.ability, self.original_profile)
                self.report["original_profile_restored"] = str(ue.get_mixin_profile(self.ability)) == self.original_profile
                self.report["original_specs_restored"] = specs(self.asc) == self.original_specs
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.write(); (ue.log_error if error else ue.log)("UEP_AUTO_RESPAWN_HELPERS_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; self.validate_report()
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.write(); (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_AUTO_RESPAWN_HELPERS_SHUTDOWN_"+self.report["status"].upper())


result = next((v.split("=", 1)[1] for v in sys.argv if v.startswith("-UEPAutoRespawnHelpersResult=")), None)
if result and "-UEPAutoRespawnListeners" not in sys.argv:
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
