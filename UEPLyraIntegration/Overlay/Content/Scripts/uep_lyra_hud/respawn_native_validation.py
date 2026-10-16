"""Original GA_AutoRespawn/native GAS -> messages -> Python UI -> native restart."""
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, GameplayEventData
from .respawn_timer_validation import RespawnValidation, state, check
from . import respawn_timer_mixin as respawn
from .weapon_observer import valid

CASES = ("native-death-started", "native-respawn-duration", "native-player-restarted")


class NativeRespawnValidation(RespawnValidation):
    def __init__(self, result):
        super().__init__(result)
        self.report.update(mode="native-gas-auto-respawn", synthetic_local_messages=False,
                           native_respawn_producer_tested=False, native_player_restart_tested=False,
                           lethal_damage_tested=False, ability_or_health_properties_written=False,
                           duration_or_completion_broadcast_called_by_fixture=False)

    def finish(self, error=None):
        try:
            self.cleanup()
        except Exception:
            error = (error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown", error=error, elapsed_seconds=time.monotonic()-self.started)
        self.write()
        (ue.log_error if error else ue.log)("UEP_RESPAWN_NATIVE_"+("FAILED "+error if error else "PASSED"))
        ue.request_exit()

    def finalize(self):
        final = respawn.snapshot()
        self.report["shutdown"] = final
        pool = final["pool_lifetime"]
        if (final["active_count"] or final["scopes_created"] != final["scopes_closed"] or final["errors"] or
                pool["active_count"] or pool["ticker_active"] or pool["registered"] != pool["unregistered"] or pool["errors"]):
            self.report.update(status="failed", error="native respawn scopes survived exit")
        if self.report["status"] == "awaiting_shutdown":
            self.report["status"] = "passed"
        self.write()
        (ue.log if self.report["status"] == "passed" else ue.log_error)("UEP_RESPAWN_NATIVE_SHUTDOWN_"+self.report["status"].upper())

    def tick(self, delta):
        try:
            check(time.monotonic()-self.started < 200, "native respawn total timeout")
            if self.phase == "ready":
                self.ready()
                return True
            elapsed = time.monotonic()-self.phase_started
            check(elapsed < 35, "native respawn phase timeout: "+self.phase)
            if self.phase == "initial" and elapsed > 0.5:
                self.old_pawn = self.pawn.get_path_name()
                self.before_duration = self.candidate._uep_respawn_duration_messages
                self.before_completed = self.candidate._uep_respawn_completed_messages
                health = ue.find_class("LyraHealthComponent").get_cdo().call_function("FindHealthComponent", self.pawn)
                tag = GameplayTag(TagName="GameplayEvent.Death")
                ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor", self.pawn, tag,
                    GameplayEventData(EventTag=tag, Instigator=self.pawn, Target=self.pawn))
                check(health.call_function("IsDeadOrDying") is True, "native death did not start")
                self.report["cases"].append({"name": "native-death-started", "death_state": int(health.call_function("GetDeathState"))})
                self.report["trigger_entry"] = "native AbilitySystemBlueprintLibrary.SendGameplayEventToActor(GameplayEvent.Death)"
                self.enter("duration")
            elif self.phase == "duration" and elapsed > 0.4:
                self.compare("native-respawn-duration")
                check(self.candidate._uep_respawn_duration_messages == self.before_duration+1, "native duration missing/duplicate")
                current = state(self.candidate)
                check(current["duration"] > 0 and current["respawning"] and current["visibility"] == 0 and
                      current["audio_valid"] and current["timer_active"], "native respawn did not show timer/audio")
                self.report["native_respawn_producer_tested"] = True
                self.report["native_duration_seconds"] = current["duration"]
                self.report["image"] = str(self.path.parent/"respawn-timer.png")
                ue.find_class("KismetSystemLibrary").get_cdo().call_function("ExecuteConsoleCommand", self.world,
                    'Shot SHOWUI -nosuffix filename="'+self.report["image"]+'"', self.controller)
                self.enter("restart")
            elif self.phase == "restart":
                pawn = self.controller.get_controlled_pawn()
                if valid(pawn) and pawn.get_path_name() != self.old_pawn and elapsed > 0.4:
                    health = ue.find_class("LyraHealthComponent").get_cdo().call_function("FindHealthComponent", pawn)
                    if not valid(health) or health.call_function("IsDeadOrDying") or health.call_function("GetHealth") <= 0:
                        return True
                    actual, original = state(self.candidate), state(self.baseline)
                    self.report["restart_observation"] = {"python": actual, "blueprint": original, "elapsed": elapsed,
                                                           "new_pawn": pawn.get_path_name(),
                                                           "completion_deliveries": self.candidate._uep_respawn_completed_messages-self.before_completed}
                    if not (actual["visibility"] == original["visibility"] == 1 and not actual["timer_active"] and not original["timer_active"]):
                        self.write()
                        return True  # Native restart/animation/completion needn't share one frame.
                    check(self.candidate._uep_respawn_completed_messages > self.before_completed, "native completion not delivered")
                    self.report["cases"].append({"name": "native-player-restarted", "old_pawn": self.old_pawn,
                                                 "new_pawn": pawn.get_path_name(), "health": float(health.call_function("GetHealth")),
                                                 "python": actual, "blueprint": original,
                                                 "native_completion_deliveries": self.candidate._uep_respawn_completed_messages-self.before_completed})
                    self.report["native_player_restart_tested"] = True
                    check([case["name"] for case in self.report["cases"]] == list(CASES), "native respawn cases incomplete")
                    self.finish()
                    return False
            return True
        except Exception:
            self.finish(traceback.format_exc())
            return False


result = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("-UEPRespawnNativeResult=")), None)
if result:
    _validation = NativeRespawnValidation(result)
    _ticker = ue.add_ticker(_validation.tick, 0.0)
