"""One native lethal-GAS authority, owner + foreign replicas, real respawn."""
import atexit
import sys
import traceback
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.jump_network_validation import arg
from uep_lyra_abilities.auto_respawn_helpers_network_validation import token
from uep_lyra_network_io import atomic_write
from .lifecycle_network_validation import Client as LifecycleClient, Server as LifecycleServer
from .death_replication_observation import Witness
from .initial_inventory_contract import CLASS


class Scope:
    def __init__(self, *args):
        super().__init__(*args); self.death_witness = None; self.death_created = self.death_closed = 0
        self.report.update(death_started_business_migrated=True, death_receiver_called_by_fixture=False, death_native_delay_backend="Delay",
            death_python_ticker_or_rooting=False, empty_death_endpoint_retained=True,
            network_death_receiver_ingress_tested=True, foreign_dying_replica_observed=True, ragdoll_physics_replication_tested=False,
            authority_pawns_relocated_for_native_relevancy=True)

    def open_death_witness(self, actor, profile):
        if self.death_witness is not None: raise RuntimeError("overlapping death signal witness")
        self.death_witness = Witness(actor, profile); self.death_created += 1

    def close_death_witness(self, row=None):
        if self.death_witness is not None:
            result = self.death_witness.close(); self.death_witness = None; self.death_closed += 1
            if row is not None: row["death_replication"] = result

    def start_inventory_evidence(self):
        super().start_inventory_evidence(); self.open_death_witness(self.pawn, self.profile)

    def end_inventory_evidence(self, row):
        self.close_death_witness(row); super().end_inventory_evidence(row)

    def tick(self, delta):
        try:
            if self.death_witness is not None: self.death_witness.sample()
        except Exception:
            self.finish(traceback.format_exc()); return False
        return super().tick(delta)

    def finish(self, error=None):
        self.close_death_witness(); return super().finish(error)

    def finalize(self):
        self.close_death_witness()
        self.report["death_replication_fixture_shutdown"] = dict(created=self.death_created, closed=self.death_closed, active=int(self.death_witness is not None))
        super().finalize()
        marker = "UEP_CHARACTER_DEATH_REPLICATION_NETWORK_" if self.report["peer"] == "server" else "UEP_CHARACTER_DEATH_REPLICATION_SHUTDOWN_"
        (ue.log if self.report["status"] == "passed" else ue.log_error)(marker+self.report["status"].upper())


class Client(Scope, LifecycleClient):
    def arm(self, command):
        if command["target"] != self.peer:
            ready = token(self.root, command["target"]+"-ready.json", self.run)
            if ready is None: return
            actors, = self.statics.call_function("GetAllActorsOfClass", self.world, ue.load_class(CLASS))
            matches = [actor for actor in actors if valid(actor.get_property("PlayerState")) and
                int(actor.get_property("PlayerState").PlayerId) == ready["player_id"] and
                actor.get_component_by_type(ue.find_class("LyraHealthComponent")).call_function("GetHealth") > 0]
            diagnostic = dict(run_id=self.run, position=command["position"], target_player_id=ready["player_id"], matches=len(matches),
                observed=[dict(actor=actor.get_path_name(), player_id=int(actor.get_property("PlayerState").PlayerId) if valid(actor.get_property("PlayerState")) else None) for actor in actors])
            if diagnostic != self.report.get("foreign_replica_readiness"):
                self.report["foreign_replica_readiness"] = diagnostic
                atomic_write(self.root/(self.peer+"-death-replica-ready.json"), diagnostic)
            if len(matches) != 1: return
            self.foreign_dying_actor = matches[0]
        super().arm(command)

    def foreign_begin_evidence(self):
        super().foreign_begin_evidence(); self.open_death_witness(self.foreign_dying_actor, self.command["profile"])
        self.foreign_dying_actor = None

    def foreign_end_evidence(self, row):
        self.close_death_witness(row); super().foreign_end_evidence(row)


class Server(Scope, LifecycleServer):
    def __init__(self, *args):
        super().__init__(*args); self.scene_points, self.positioned = None, {}
        self.report["native_relevancy_teleports"] = []

    def prepare(self):
        pawns = {peer: value["controller"].get_controlled_pawn() for peer, value in self.fixture.owners.items()}
        if not all(valid(actor) for actor in pawns.values()): return
        if self.scene_points is None:
            anchor = pawns["A"].get_actor_location()
            self.scene_points = dict(A=anchor, B0=ue.FVector(anchor.x+300., anchor.y, anchor.z))
        for peer, actor in pawns.items():
            if self.positioned.get(peer) == actor.get_path_name(): continue
            # Establish an explicitly nearby native relevance fixture BEFORE
            # per-trial foreign-state baselines and damage. Native collision-
            # checked teleport, normal replication; no relevance/CDO writes.
            success = actor.call_function("K2_TeleportTo", self.scene_points[peer], actor.get_actor_rotation())
            if not success: raise RuntimeError("native death-relevance fixture teleport refused: "+peer)
            actor.call_function("ForceNetUpdate")
            point = actor.get_actor_location(); self.positioned[peer] = actor.get_path_name()
            self.report["native_relevancy_teleports"].append(dict(peer=peer, actor=actor.get_path_name(), position=self.position,
                native_api="K2_TeleportTo", succeeded=True, actual_location=[point.x, point.y, point.z]))
        super().prepare()


if any(value.startswith("-UEPCharacterDeathReplicationNetworkResult=") for value in sys.argv):
    result, peer, run = arg("-UEPCharacterDeathReplicationNetworkResult="), arg("-UEPJumpPeer="), arg("-UEPJumpRun=")
    validation = Server(result, run) if peer == "server" else Client(result, peer, run)
    atexit.register(validation.finalize); ticker = ue.add_ticker(validation.tick)
