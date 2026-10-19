"""Independent native footprint state, parameter-store and latent evidence gate."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .weapon_actor_helpers_contract import require

PROFILES = ("BlueprintFallback", "Python")
PATHS = ("direct", "blueprint")
CASES = ("cold", "reuse", "right-case", "surface-three", "unsupported-four", "unsupported-sixty-three",
    "disabled", "miss", "zero-normal", "parallel-normal", "tilted-normal", "nonunit-normal",
    "empty-bone", "ignored-inputs", "replace-inactive", "cached-disabled")


def close(a, b):
    if isinstance(a, dict): return a.keys() == b.keys() and all(close(a[k], b[k]) for k in a)
    if isinstance(a, list): return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, float): return abs(a-b) <= 1e-5
    return a == b


def validate(report):
    require(report["status"] == "passed" and report["error"] is None and report["native_mode"] == "Standalone", "native footprint run failed")
    for field in ("full_acceptance", "network_acceptance", "packaged_runtime", "pixels_tested", "audio_playback_tested",
            "timer_properties_written", "latent_callback_replayed", "health_properties_written", "natural_animation_dispatch_tested"):
        require(report[field] is False, "footstep scope overclaim: "+field)
    for field in ("native_warmup_ready", "all_test_actors_destroyed", "original_pawn_health_unchanged", "production_classes_restored", "diagnostic_probe_unrooted", "materials_unrooted"):
        require(report[field] is True, "footstep witness/cleanup missing: "+field)
    rows = report["cases"]
    require(Counter((r["profile"], r["path"], r["name"]) for r in rows) == Counter((p, q, n) for p in PROFILES for q in PATHS for n in CASES), "native footprint matrix incomplete")
    for row in rows:
        require(row["actual_selected_motion_dispatch"] and row["stored_mesh_unchanged"] and row["component_valid"], "motion entry/cache evidence missing")
        allowed = row["name"] not in ("unsupported-four", "unsupported-sixty-three", "disabled", "miss", "cached-disabled")
        if allowed:
            state, store = row["state"], row["parameters"]
            require(store["trigger"] == state["trigger"] and store["side"] == state["side"] and store["surface"] == state["surface_niagara"], "actual Niagara bool/int data differs")
            require(close(store["location"], state["location"]) and close(store["orientation"], state["orientation"]), "actual Niagara location/quaternion differs")
        if row["name"] in ("cold", "replace-inactive"):
            require(not row["same_cached"] and row["state"]["trigger"] and row["attached_to_root"] and row["relative_location"] == [0., 0., 0.] and row["relative_rotation"] == [0., 0., 0.], "native spawn/reset/attachment differs")
        else: require(row["same_cached"], "active native footprint cache was replaced")
        if row["name"] in ("disabled", "miss", "cached-disabled"):
            require(row["state"] == row["before_state"] and row["parameters"] == row["before_parameters"], "disabled/missed event changed footprint state")
        if row["name"].startswith("unsupported-"):
            require(row["state"]["surface"] == row["input_surface"] and all(row["state"][k] == v for k,v in row["before_state"].items() if k not in ("surface", "hit")) and row["parameters"] == row["before_parameters"], "unsupported surface advanced footprint branch")
    for path in PATHS:
        for name in CASES:
            paired = [r for r in rows if r["path"] == path and r["name"] == name]
            require(close(paired[0]["state"], paired[1]["state"]) and close(paired[0]["parameters"], paired[1]["parameters"]), "original/Python native footprint differential: "+path+"/"+name)
    timers = report["timer_cases"]
    require(Counter(r["profile"] for r in timers) == Counter(PROFILES), "native latent profile matrix incomplete")
    for row in timers:
        require(row["native_retrigger_observed"] and row["survived_original_deadline"] and row["destroyed_after_retrigger"] and 4. <= row["destroy_elapsed"] < 5.5, "original retriggerable delay differs")
        require(row["valid_inactive_kept_actor_alive"] and row["native_repeat_cleanup_observed"] and row["destroyed_after_component_removal"], "cleanup used active state instead of validity")
    return dict(status="passed", actual_native_motion_calls=len(rows), paired_native_state_cases=32,
        actual_native_delay_profiles=2, full_acceptance=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--report", required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding="utf-8-sig")))))
