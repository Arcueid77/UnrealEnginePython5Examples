"""Read-only native part state and independently owned multicast observation."""
import traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_world.effect_pad_mixin import valid
from .outline_validation import path


def component(actor): return actor.get_property("PawnCosmeticsComponent")


def parts(actor):
    # Copy POD now; never retain a borrowed FastArray struct across mutation.
    values = []
    for entry in component(actor).get_property("CharacterPartList").Entries:
        part = entry.Part
        values.append(dict(cls=path(part.PartClass), socket=str(part.SocketName), collision=int(part.CollisionMode),
            handle=int(entry.PartHandle), component=path(entry.SpawnedComponent)))
    return values


def part_actors(actor): return list(component(actor).call_function("GetCharacterPartActors"))


def query(actor):
    found, number, display = ue.find_class("LyraTeamStatics").get_cdo().call_function("FindTeamFromObject", actor, False)
    return dict(part_of_team=bool(found), team_id=int(number), display_asset=path(display))


def delta(after, before, skip): return {key: value-before[key] for key, value in after.items() if key != skip}


class DelegateObserver:
    def __init__(self, actors, on_delivery=None):
        self.scope, self.deliveries, self.bindings, self.closed_bindings = SubscriptionScope(), {}, 0, 0
        self.on_delivery, self.errors = on_delivery, []
        try:
            for actor in actors:
                key, source = path(actor), component(actor); self.deliveries[key] = []
                def received(value, key=key, expected_source=path(source)):
                    self.deliveries[key].append(dict(component_matches=path(value) == expected_source,
                        owner_matches=valid(value) and path(value.get_owner()) == key))
                    if self.on_delivery is not None:
                        try: self.on_delivery(key)
                        except Exception: self.errors.append(traceback.format_exc())
                self.scope.bind_event(source, "OnCharacterPartsChanged", received); self.bindings += 1
        except Exception:
            self.scope.close(); raise

    def count(self, actor): return len(self.deliveries[path(actor)])

    def since(self, actor, before): return self.deliveries[path(actor)][before:]

    def close(self):
        self.scope.close(); self.closed_bindings = self.bindings

    def snapshot(self):
        return dict(created=1, closed=int(self.scope.closed), bindings_created=self.bindings, bindings_closed=self.closed_bindings,
            active=self.scope.count, deliveries=sum(len(value) for value in self.deliveries.values()), errors=list(self.errors))
