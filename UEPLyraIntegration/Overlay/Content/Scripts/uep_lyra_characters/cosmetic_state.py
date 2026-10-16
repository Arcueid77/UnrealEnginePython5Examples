"""Read-only native FastArray/child-actor observations, no part mutation."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid


def path(value): return value.get_path_name() if valid(value) else None


def capture(pawn):
    component = pawn.get_component_by_type(ue.find_class("LyraPawnComponent_CharacterParts"))
    if not valid(component): raise RuntimeError("Native Pawn character-part component missing")
    rows = []
    for entry in component.get_property("CharacterPartList").Entries:
        child = entry.SpawnedComponent
        actor = child.get_property("ChildActor") if valid(child) else None
        rows.append(dict(handle=int(entry.PartHandle), cls=path(entry.Part.PartClass), socket=str(entry.Part.SocketName),
            collision_mode=int(entry.Part.CollisionMode), child=path(child), actor=path(actor),
            actor_class=path(actor.get_class()) if valid(actor) else None,
            actor_collision=bool(actor.call_function("GetActorEnableCollision")) if valid(actor) else None,
            attached_pawn=path(actor.call_function("GetAttachParentActor")) if valid(actor) else None))
    return sorted(rows, key=lambda row: row["handle"])
