"""Finalize probe evidence at Python exit, after UEP's Mixin teardown.

No UObject calls are allowed here. The external driver must still wait for a
clean process exit and closed log before accepting this final report.
"""

import atexit
import copy
import json
from pathlib import Path

import unreal_engine as ue

from . import state


COUNTERS = (
    "construct_count",
    "destruct_count",
    "teardown_count",
    "controller_bind_count",
    "controller_unbind_count",
    "health_bind_count",
    "health_unbind_count",
)


def checked_counter(hud, name):
    value = hud.get(name)
    if type(value) is not int or value < 0:
        raise RuntimeError("invalid final HUD counter: " + name)
    return value


def validate_shutdown_snapshot(before, final):
    if final.get("errors") != []:
        raise RuntimeError("HUD shutdown contains presenter errors")
    if (
        checked_counter(final, "active_widget_count") != 0
        or final.get("active_widgets") != []
        or checked_counter(final, "live_widget_reference_count") != 0
    ):
        raise RuntimeError("HUD shutdown retained a presenter or widget reference")
    for name in COUNTERS:
        if checked_counter(final, name) < checked_counter(before, name):
            raise RuntimeError("HUD shutdown lost prior evidence: " + name)
    for prefix in ("controller", "health"):
        if final[prefix + "_bind_count"] != final[prefix + "_unbind_count"]:
            raise RuntimeError("HUD shutdown retained " + prefix + " callbacks")


def finalized_report(pending_report, final_hud):
    """Pure transformation so negative cases need neither Unreal nor a file."""
    result = copy.deepcopy(pending_report)
    result["shutdown"] = {
        "phase": "python_atexit",
        "status": "failed",
        "hud": copy.deepcopy(final_hud),
    }
    try:
        if pending_report.get("status") != "awaiting_shutdown":
            raise RuntimeError("HUD report was not awaiting shutdown")
        validate_shutdown_snapshot(result["hud"], final_hud)
    except Exception as error:
        result["status"] = "failed"
        result["error"] = str(error)
    else:
        result["status"] = "passed"
        result["shutdown"]["status"] = "passed"
    return result


def _finalize(result_path, pending_report):
    # UEP unregisters routers in OnEnginePreExit before Py_Finalize calls atexit.
    # Captured state contains only metadata; this path never queries dead UObjects.
    report = finalized_report(pending_report, state.snapshot())
    if "weapon_observer" in pending_report:
        from . import weapon_observer
        final_weapon = weapon_observer.snapshot()
        report["shutdown"]["weapon_observer"] = final_weapon
        if (final_weapon["active_count"] != 0 or final_weapon["ticker_active"]
                or final_weapon["subscribed"] != final_weapon["unsubscribed"] or final_weapon["errors"]
                or final_weapon["active_scopes"] != 0 or final_weapon["scope_created"] != final_weapon["scope_closed"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Weapon observers survived shutdown or reported errors"
    if "weapon_reticle_observers" in pending_report:
        from . import weapon_reticle_mixin
        final_reticles = weapon_reticle_mixin.snapshot()
        report["shutdown"]["weapon_reticle_observers"] = final_reticles
        if (final_reticles["active_count"] != 0 or final_reticles["scopes_created"] != final_reticles["scopes_closed"]
                or final_reticles["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production reticle scopes survived shutdown"
    if "reticle_host_observers" in pending_report:
        from . import reticle_host_mixin
        final_hosts = reticle_host_mixin.snapshot()
        report["shutdown"]["reticle_host_observers"] = final_hosts
        if (final_hosts["active_count"] != 0 or final_hosts["scopes_created"] != final_hosts["scopes_closed"]
                or final_hosts["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production reticle host scopes survived shutdown"
    if "ability_progress_observers" in pending_report:
        from . import ability_progress_mixin
        final_progress = ability_progress_mixin.snapshot()
        report["shutdown"]["ability_progress_observers"] = final_progress
        if (final_progress["active_count"] != 0 or final_progress["scopes_created"] != final_progress["scopes_closed"]
                or final_progress["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production ability progress scopes survived shutdown"
    if "heal_ability_observers" in pending_report:
        from uep_lyra_world import heal_ability_mixin
        final_heal = heal_ability_mixin.snapshot()
        report["shutdown"]["heal_ability_observers"] = final_heal
        if (final_heal["active_count"] or final_heal["scopes_created"] != final_heal["scopes_closed"] or
                final_heal["timers_created"] != final_heal["timers_cleared"] or final_heal["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production heal ability scopes/timers survived shutdown"
    if "action_touch_observers" in pending_report:
        from . import action_touch_mixin
        final_touch = action_touch_mixin.snapshot()
        report["shutdown"]["action_touch_observers"] = final_touch
        if (final_touch["active_count"] or final_touch["scopes_created"] != final_touch["scopes_closed"] or final_touch["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production action touch scopes survived shutdown"
    if "ability_failure_observers" in pending_report:
        from . import ability_failure_mixin
        final_failure = ability_failure_mixin.snapshot()
        report["shutdown"]["ability_failure_observers"] = final_failure
        if (final_failure["active_count"] != 0 or final_failure["scopes_created"] != final_failure["scopes_closed"] or final_failure["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production failure feedback scopes survived shutdown"
    if "dash_cooldown_observers" in pending_report:
        from . import dash_cooldown_mixin
        final_dash = dash_cooldown_mixin.snapshot()
        report["shutdown"]["dash_cooldown_observers"] = final_dash
        if (final_dash["active_count"] != 0 or final_dash["scopes_created"] != final_dash["scopes_closed"] or
                final_dash["health_binds"] != final_dash["health_unbinds"] or final_dash["errors"] or
                final_dash["pool_lifetime"]["active_count"] or final_dash["pool_lifetime"]["ticker_active"] or
                final_dash["pool_lifetime"]["registered"] != final_dash["pool_lifetime"]["unregistered"] or
                final_dash["pool_lifetime"]["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production Dash scopes survived shutdown"
    if "respawn_timer_observers" in pending_report:
        from . import respawn_timer_mixin
        final_respawn = respawn_timer_mixin.snapshot()
        report["shutdown"]["respawn_timer_observers"] = final_respawn
        pool = final_respawn["pool_lifetime"]
        if (final_respawn["active_count"] or final_respawn["scopes_created"] != final_respawn["scopes_closed"] or
                final_respawn["errors"] or pool["active_count"] or pool["ticker_active"] or
                pool["registered"] != pool["unregistered"] or pool["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production respawn scopes survived shutdown"
    if "quickbar_slot_observers" in pending_report:
        from . import quickbar_slot_mixin
        final_slots = quickbar_slot_mixin.snapshot()
        report["shutdown"]["quickbar_slot_observers"] = final_slots
        pool = final_slots["pool_lifetime"]
        if (final_slots["active_count"] or final_slots["scopes_created"] != final_slots["scopes_closed"] or
                final_slots["errors"] or pool["active_count"] or pool["ticker_active"] or
                pool["registered"] != pool["unregistered"] or pool["errors"]):
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Production quickbar scopes survived shutdown"
    if "nameplate_observers" in pending_report:
        from . import nameplate_source_mixin, nameplate_manager_mixin, nameplate_mixin
        from uep_lyra_nameplate_protocol import validate_scopes as validate_nameplate_scopes
        final_nameplates = {"sources": nameplate_source_mixin.snapshot(), "managers": nameplate_manager_mixin.snapshot(),
                            "widgets": nameplate_mixin.snapshot(),
                            "native_placement": copy.deepcopy(pending_report["nameplate_observers"]["native_placement"])}
        report["shutdown"]["nameplate_observers"] = final_nameplates
        try:
            validate_nameplate_scopes(final_nameplates, report["peer"])
        except Exception as error:
            report["status"] = report["shutdown"]["status"] = "failed"
            report["error"] = "Nameplate shutdown: " + str(error)
    Path(result_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] == "passed":
        if report["gameplay_slice"]["enabled"]:
            ue.log("UEP_LYRA_GAMEPLAY_SLICE_PASSED")
        ue.log("UEP_LYRA_PYTHON_HUD_PASSED")
        ue.log("UEP_LYRA_HUD_SHUTDOWN_PASSED")
        ue.log("UEP_LYRA_SMOKE_PASSED")
    else:
        ue.log_error("UEP_LYRA_HUD_SHUTDOWN_FAILED " + report["error"])


def defer_until_shutdown(report, result_path):
    """Arm only the automation probe, not ordinary interactive play."""
    report["status"] = "awaiting_shutdown"
    report["shutdown"] = {"status": "pending", "phase": "python_atexit"}
    # Freeze the pre-quit proof: later callbacks must not rewrite its counters.
    atexit.register(_finalize, str(result_path), copy.deepcopy(report))
