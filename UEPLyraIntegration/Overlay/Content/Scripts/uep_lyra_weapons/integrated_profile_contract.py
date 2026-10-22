"""Opt-in original/Python weapon policies through native travel and rejoin."""
PROFILES = ("BlueprintFallback", "Python")
FAMILIES = ("fire", "reload", "autoreload", "quickslot")


def require(value, message):
    if not value: raise RuntimeError(message)


def validate(report, profile):
    require(profile in PROFILES and report["selected_profile"] == profile, "wrong integrated gameplay Profile")
    require(report["selectors_restored"] and report["owned_roots_released"] and not report["gameplay_state_written"],
        "integrated policy selector/root ownership was not restored")
    require(report["observations"] and set(report["class_families"]) == set(FAMILIES), "missing native gameplay policy witnesses")
    for row in report["observations"]:
        require(row["profile"] == profile and row["family"] in FAMILIES and row["world_token"] and row["pawn"] and
            row["ability"] and row["native_class"] and row["controller"], "mixed/ambiguous native gameplay policy")
        require(row["authority"] is (report["peer"] == "server"), "gameplay policy authority mismatch")
    require(set(row["family"] for row in report["observations"]) == set(FAMILIES), "incomplete integrated ability family coverage")
    selected = "activations" if profile == "Python" else "fallback_activations"
    foreign = "fallback_activations" if profile == "Python" else "activations"
    firing = [row["fire_counts"] for row in report["observations"] if row["family"] == "fire" and row.get("fire_counts")]
    require(firing and any(value[selected] > 0 for value in firing) and all(value[foreign] == 0 for value in firing),
        "integrated native firing did not exclusively reach the selected policy")
    worlds = {row["world_token"] for row in report["observations"]}
    require(len(worlds) >= (1 if report["peer"] == "B1" else 3), "gameplay Profile did not survive both native travels")
    final = report["shutdown"]
    require(set(final) == {"reload", "autoreload", "quickslot"}, "missing native gameplay task shutdown evidence")
    for stats in final.values():
        require(stats["active_count"] == 0 and stats["scopes_created"] == stats["scopes_closed"] and not stats["errors"],
            "native gameplay task scopes survived interpreter shutdown")
    if profile == "Python" and report["peer"] != "B1":
        require(final["reload"]["activations"] > 0 and final["reload"]["authority_reloads"] > 0 if report["peer"] == "server"
            else final["reload"]["activations"] > 0, "integrated Python reload policy was bypassed")
    return dict(status="passed", profile=profile, native_world_generations=len(worlds), ability_witnesses=len(report["observations"]))
