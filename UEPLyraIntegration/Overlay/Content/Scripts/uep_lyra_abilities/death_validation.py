"""Real GAS lethal damage, independent event/cue observation and native respawn."""
import atexit
import copy
import json
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_runtime import SubscriptionScope
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import ability_system, valid
from . import death_mixin as policy, death_observation as observation, death_damage
from .death_contract import PLAN, require, validate

RESPAWN = "/ShooterCore/Game/Respawn/GA_AutoRespawn.GA_AutoRespawn_C"


class Validation:
    def __init__(self, result):
        self.path, self.started, self.phase = Path(result), time.monotonic(), "ready"
        self.finished, self.index, self.sides = False, 0, []
        self.source_scope, self.source_task = None, None
        self.report = dict(schema_version=1, status="running", error=None, cases=[], real_lethal_gas_damage=False,
            cue_observer_restored=False, source_scopes_created=0, source_scopes_closed=0,
            full_acceptance=False, network_acceptance=False, packaged_runtime=False, death_event_sent_by_probe=False,
            activation_handler_replayed=False, task_callbacks_replayed=False, health_properties_written=False,
            death_duration_written=False, animation_assets_modified=False)

    def enter(self, phase): self.phase, self.phase_started = phase, time.monotonic()

    def instances(self, cls):
        return [value for spec in self.asc.get_property("ActivatableAbilities").Items
            if valid(spec.Ability) and spec.Ability.get_class() == cls
            for value in list(spec.NonReplicatedInstances)+list(spec.ReplicatedInstances) if valid(value)]

    def game_time(self): return float(self.statics.call_function("GetTimeSeconds", self.world))

    def ready(self):
        self.statics = ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1, 3): continue
            bridge = ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld", world)
            if not valid(bridge): continue
            isolate_bots(self.statics, world, ue.find_class("LyraPlayerBotController"))
            snap = bridge.call_function("CaptureSnapshot")
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bAbilitySystemReady and snap.bHealthReady and
                    not snap.bDamageImmune and snap.Health > 0): continue
            controller = self.statics.call_function("GetPlayerController", world, 0)
            if not self.attach(world, bridge, controller): continue
            self.begin(); return

    def attach(self, world, bridge, controller):
        self.attach_status = dict(waiting="valid native Pawn/ASC")
        self.world, self.bridge, self.controller = world, bridge, controller
        self.pawn = controller.get_controlled_pawn()
        if not valid(self.pawn): return False
        self.asc, self.cls = ability_system(self.pawn), ue.load_class(policy.CLASS)
        if not valid(self.asc): return False
        matches, owners = self.instances(self.cls), self.instances(ue.load_class(RESPAWN))
        self.attach_status = dict(waiting="native Death/respawn instances", death_instances=len(matches), respawn_instances=len(owners),
            respawn_active=bool(owners[0].get_property("bIsActive")) if len(owners) == 1 else None,
            respawn_net_policy=int(owners[0].NetExecutionPolicy) if len(owners) == 1 else None)
        if len(matches) != 1 or len(owners) != 1: return False
        if not getattr(self, "source_observer_uses_death", False) and not owners[0].get_property("bIsActive"): return False
        self.ability, self.source_owner = matches[0], owners[0]
        self.attach_status["death_active"] = bool(self.ability.get_property("bIsActive"))
        if self.ability.get_property("bIsActive"): return False
        self.health = self.pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        self.hero = self.pawn.get_component_by_type(ue.find_class("LyraHeroComponent"))
        if getattr(self, "expected_cues", 1) and not hasattr(self, "cue_cls"):
            self.cue_cls = ue.load_class(observation.CUE)
            require(not any(row["target_class"] == self.cue_cls for row in ue.get_registered_mixins()), "test must not replace a production Cue mixin")
            self.original_cue = self.cue_cls.get_cdo().find_function("OnBurst")
            owner = self
            class ObserveCue:
                def OnBurst(self, Target, Parameters, SpawnResults):
                    try:
                        if observation.path(Target) == owner.old_pawn:
                            owner.cues.append(observation.cue(Target, Parameters))
                    except Exception: owner.observation_errors.append(traceback.format_exc())
                    # Observation must not suppress the original native BP Cue.
                    return self.call_mixin_original("OnBurst", Target, Parameters, SpawnResults)
            ue.register_mixin_profile(self.cue_cls, "UEPDeathCueObserve", ObserveCue, make_default=True)
        return True

    def close_source(self):
        if self.source_scope is not None:
            self.source_scope.close(); self.source_scope = None
            self.report["source_scopes_closed"] += 1
        if valid(self.source_task): self.source_task.call_function("EndTask")
        self.source_task = None

    def begin(self):
        self.name, self.profile = PLAN[self.index//2], ("BlueprintFallback", "Python")[self.index % 2]
        ue.set_mixin_profile(self.ability, self.profile)
        self.sources, self.cues, self.observation_errors, self.intervened = [], [], [], False
        self.old_pawn = self.pawn.get_path_name()
        self.source_scope = SubscriptionScope(); self.report["source_scopes_created"] += 1
        task_owner = observation.source_owner(self.ability, self.source_owner, getattr(self, "source_observer_uses_death", False))
        self.source_delivery_owner_active = []
        self.source_task = ue.find_class("AbilityTask_WaitGameplayEvent").get_cdo().call_function(
            "WaitGameplayEvent", task_owner, GameplayTag(TagName="GameplayEvent.Death"), None, False, True)
        def received(payload):
            self.sources.append(observation.event(payload))
            self.source_delivery_owner_active.append(bool(task_owner.get_property("bIsActive")))
        self.source_scope.bind_event(self.source_task, "EventReceived", received)
        self.source_task.call_function("ReadyForActivation")
        self.before, self.native_started = policy.snapshot(), self.game_time()
        self.row = dict(health_before=float(self.health.call_function("GetHealth")), old_pawn=self.old_pawn,
            original_duration=float(self.ability.Duration), cancel_refused=False, profile_switched=False,
            original_respawn_delay=float(self.source_owner.RespawnDelayDuration),
            source_observer_kind="native_wait_gameplay_event_on_death" if getattr(self, "source_observer_uses_death", False) else "native_wait_gameplay_event_on_respawn")
        # The unchanged production respawn ends Death at five seconds, before
        # Death's original eight-second wait. Test that path separately; only
        # the two timer cases temporarily delay the native respawn fixture.
        delay = self.row["original_duration"]+1. if self.name in ("native-timer", "native-cancel-refused") else self.row["original_respawn_delay"]
        self.row["fixture_respawn_delay"] = delay
        try:
            self.source_owner.set_property("RespawnDelayDuration", delay)
            self._respawn_fixture_pending = True
            death_damage.apply(self.asc, self.row["health_before"])
        except Exception:
            self.restore_respawn_fixture(); raise
        finally:
            if not getattr(self, "hold_respawn_fixture", False): self.restore_respawn_fixture()
        require(self.health.call_function("GetHealth") == 0, "native lethal GE did not reach zero Health")
        self.report["real_lethal_gas_damage"] = True
        self.row["damage_effect"] = death_damage.DAMAGE
        self.row.update(health_after_damage=float(self.health.call_function("GetHealth")),
            native_death_started=int(self.health.call_function("GetDeathState")) == 1,
            native_type_preserved=self.ability.get_class() == self.cls,
            native_cancelable=bool(self.ability.get_property("bIsCancelable")),
            death_camera_matched=self.hero.get_property("AbilityCameraMode") == self.ability.get_property("Camera Mode"))
        require(self.ability.get_property("bIsActive"), "real lethal death did not activate original ability")
        self.enter("death")

    def restore_respawn_fixture(self):
        if getattr(self, "_respawn_fixture_pending", False):
            self.source_owner.set_property("RespawnDelayDuration", self.row["original_respawn_delay"])
            self._respawn_fixture_pending = False
            self.row["respawn_delay_restored"] = float(self.source_owner.RespawnDelayDuration) == self.row["original_respawn_delay"]

    def observe(self):
        require(not self.observation_errors, "native Cue observation failed: "+repr(self.observation_errors))
        elapsed = self.game_time()-self.native_started
        active = bool(self.ability.get_property("bIsActive"))
        if not self.intervened and elapsed > .3 and active and self.name in ("native-cancel-refused", "external-native-end", "active-profile-switch"):
            self.intervened = True
            if self.name == "native-cancel-refused":
                self.ability.call_function("K2_CancelAbility")
                self.row["cancel_refused"] = bool(self.ability.get_property("bIsActive"))
                require(self.row["cancel_refused"], "native Death noncancelable rule was bypassed")
            elif self.name == "external-native-end": self.ability.call_function("K2_EndAbility")
            else:
                ue.set_mixin_profile(self.ability, "Python" if self.profile == "BlueprintFallback" else "BlueprintFallback")
                self.row["profile_switched"] = not self.ability.get_property("bIsActive")
            active = bool(self.ability.get_property("bIsActive"))
        if active:
            if getattr(self, "hold_respawn_fixture", False):
                require(float(self.source_owner.RespawnDelayDuration) == self.row["fixture_respawn_delay"], "authority fixture delay changed during death")
            require(elapsed < self.row["original_duration"]+3., "native death timer did not finish")
            return
        self.restore_respawn_fixture()
        self.row["native_elapsed"] = elapsed
        require(len(self.sources) == 1 and len(self.cues) == getattr(self, "expected_cues", 1),
                "real death source/Cue missing or duplicated: "+repr((self.sources, self.cues)))
        self.row.update(source_events=len(self.sources), cue_deliveries=len(self.cues),
            source_event=self.sources[0], source_delivery_owner_active=self.source_delivery_owner_active,
            cue=self.cues[0] if self.cues else None)
        self.close_source()
        self.enter("respawn")

    def respawn(self):
        pawn = self.controller.get_controlled_pawn()
        if not valid(pawn) or pawn.get_path_name() == self.old_pawn:
            require(time.monotonic()-self.phase_started < 25., "native original respawn did not replace Pawn")
            return
        snap = self.bridge.call_function("CaptureSnapshot")
        if not (snap.bHeroInputReady and snap.bHealthReady and not snap.bDamageImmune and snap.Health > 0): return
        self.row.update(new_pawn=pawn.get_path_name(), respawn_health=float(snap.Health), respawn_input_ready=bool(snap.bHeroInputReady))
        stats = policy.snapshot()
        self.row["counters"] = {key: value-self.before[key] for key, value in stats.items() if type(value) is int and key != "active_count"}
        self.sides.append(copy.deepcopy(self.row))
        if self.index % 2:
            self.report["cases"].append(dict(name=self.name, blueprint=self.sides[0], python=self.sides[1]))
            self.sides = []; ue.log("UEP_DEATH_ABILITY_CASE_PASSED "+self.name)
        self.index += 1
        if self.index == len(PLAN)*2: self.finish()
        else: self.enter("ready")

    def tick(self, delta):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started < 240., "native death total timeout: "+self.phase)
            if hasattr(self, "world"): isolate_bots(self.statics, self.world, ue.find_class("LyraPlayerBotController"))
            if self.phase == "ready": self.ready()
            elif self.phase == "death": self.observe()
            elif self.phase == "respawn": self.respawn()
            return not self.finished
        except Exception: self.finish(traceback.format_exc()); return False

    def finish(self, error=None):
        if self.finished: return
        self.finished = True
        try:
            self.restore_respawn_fixture()
            self.close_source()
            if hasattr(self, "ability") and valid(self.ability): ue.set_mixin_profile(self.ability, "Python")
            if hasattr(self, "cue_cls"):
                require(ue.unregister_mixin(self.cue_cls) and self.cue_cls.get_cdo().find_function("OnBurst") == self.original_cue, "native Cue observer not restored")
                self.report["cue_observer_restored"] = True
        except Exception: error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error)
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log_error if error else ue.log)("UEP_DEATH_ABILITY_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        self.report["policy_shutdown"] = policy.snapshot()
        if self.report["status"] == "awaiting_shutdown":
            try:
                self.report["status"] = "passed"; validate(self.report)
            except Exception: self.report.update(status="failed", error=traceback.format_exc())
        self.path.write_text(json.dumps(self.report, indent=2), encoding="utf-8")
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_DEATH_ABILITY_SHUTDOWN_"+self.report["status"].upper())


if any(value.startswith("-UEPDeathAbilityResult=") for value in sys.argv):
    result = next(value.split("=", 1)[1] for value in sys.argv if value.startswith("-UEPDeathAbilityResult="))
    validation = Validation(result); atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
