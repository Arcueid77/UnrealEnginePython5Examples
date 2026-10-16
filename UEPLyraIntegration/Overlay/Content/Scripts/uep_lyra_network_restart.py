"""Explicit test-owned old-Pawn retirement, not a death-ability claim."""
import unreal_engine as ue
from uep_lyra_hud.weapon_observer import valid
from uep_lyra_network_protocol import require


def retire_old_pawn(pawn_path):
    pawn = ue.find_object(pawn_path)
    result = {"old_pawn": pawn_path, "fixture_native_destroy_called": False,
              "native_destroy_complete": not valid(pawn), "manual_lifecycle_event": False,
              "death_ability_tested": False}
    if valid(pawn):
        require(bool(pawn.call_function("HasAuthority")), "old-Pawn retirement must execute on server")
        pawn.call_function("K2_DestroyActor")
        result.update(fixture_native_destroy_called=True, native_destroy_complete=not valid(pawn))
    require(result["native_destroy_complete"], "old Pawn did not finish native destruction")
    return result


def retire_client_sources(pawn_path, source_class):
    pawn = ue.find_object(pawn_path)
    sources = list(pawn.call_function("K2_GetComponentsByClass", source_class)) if valid(pawn) else []
    sources = [source for source in sources if valid(source)]
    for source in sources:
        source.call_function("K2_DestroyComponent", source)
    result = {"old_pawn": pawn_path, "native_source_destroy_calls": len(sources),
              "all_sources_destroyed": not any(valid(source) for source in sources), "manual_lifecycle_event": False}
    require(result["all_sources_destroyed"], "client old-Pawn sources survived native destruction")
    return result
