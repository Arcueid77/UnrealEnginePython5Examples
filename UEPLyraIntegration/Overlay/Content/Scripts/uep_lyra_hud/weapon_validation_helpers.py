"""Test-only native inventory input setup, shared by isolated HUD fixtures."""

from unreal_engine.structs import GameplayTag


def set_stat(item, tag, value):
    key = GameplayTag(TagName=tag)
    current = item.call_function("GetStatTagStackCount", key)
    if current:
        item.call_function("RemoveStatTagStack", key, current)
    if value:
        item.call_function("AddStatTagStack", key, value)
