"""Retain the legacy OnRep helper's literal defaults, not current-team inference."""
from .team_listener_mixin import LyraCharacterTeamListenerPythonProfile as ListenerPython, LyraCharacterTeamListenerBlueprintFallbackProfile as ListenerBlueprint


def evidence(actor):
    value = getattr(actor, "_uep_character_legacy_player_info", None)
    if value is None:
        value = dict(python_calls=0, fallback_calls=0, team_forwards=0)
        actor._uep_character_legacy_player_info = value
    return value


class LyraCharacterLegacyPlayerInfoPythonProfile:
    def OnRep_PlayerInfo(self):
        counts = evidence(self); counts["python_calls"] += 1
        self.call_function("OnTeamOrCosmeticsChanged", 0, None); counts["team_forwards"] += 1


class LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile:
    def OnRep_PlayerInfo(self):
        evidence(self)["fallback_calls"] += 1
        self.call_mixin_original("OnRep_PlayerInfo")


# The native collector reads only the local dictionary. Copy raw objects from
# that dictionary, including descriptors; normal class access unwraps them.
for profile, parent in ((LyraCharacterLegacyPlayerInfoPythonProfile, ListenerPython),
                        (LyraCharacterLegacyPlayerInfoBlueprintFallbackProfile, ListenerBlueprint)):
    for name, method in parent.__dict__.items():
        if not name.startswith("__"):
            setattr(profile, name, method)
