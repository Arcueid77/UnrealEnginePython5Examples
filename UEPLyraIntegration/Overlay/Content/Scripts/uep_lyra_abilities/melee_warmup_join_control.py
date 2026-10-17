"""Diagnostic scheduling only: both clients join before native warmup ends."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write, read_json
from uep_lyra_world.effect_pad_mixin import valid

PEERS=("A","B0")


class WarmupJoinControl:
    def __init__(self,root,peer,run):
        self.root,self.peer,self.run=root,peer,run
        self.world=None;self.original=None;self.closed=False;self.released=False
        self.report=dict(enabled=True,server_time_dilation_written=False,health_written=False,
            native_warmup_observed=False,join_beacon_written=False,restored=False)
    def client_poll(self):
        if self.report["join_beacon_written"] or self.closed: return
        statics=ue.find_class("GameplayStatics").get_cdo()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or "L_Expanse" not in world.get_name(): continue
            controller=statics.call_function("GetPlayerController",world,0)
            if not valid(controller): continue
            pawn=controller.get_controlled_pawn()
            if not valid(pawn) or int(pawn.call_function("GetLocalRole"))!=2: continue
            health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
            if not valid(health) or float(health.call_function("GetHealth"))<=0: continue
            row=dict(run_id=self.run,peer=self.peer,pawn=pawn.get_path_name(),
                player_id=int(controller.PlayerState.PlayerId),native_role=2,
                health=float(health.call_function("GetHealth")))
            atomic_write(self.root/(self.peer+"-warmup-joined.json"),row)
            self.report.update(join_beacon_written=True,join=row);return
    def server_poll(self):
        if self.released or self.closed: return
        statics=ue.find_class("GameplayStatics").get_cdo()
        if self.world is None:
            worlds=[world for world in ue.all_worlds() if world.get_world_type() in (1,3,5) and "L_Expanse" in world.get_name()]
            if not worlds: return
            self.world=worlds[0]
            self.original=float(statics.call_function("GetGlobalTimeDilation",self.world))
            statics.call_function("SetGlobalTimeDilation",self.world,.1)
            self.report.update(server_time_dilation_written=True,original_time_dilation=self.original,
                held_time_dilation=float(statics.call_function("GetGlobalTimeDilation",self.world)))
        phases=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",self.world,ue.find_class("LyraGamePhaseSubsystem"))
        active=valid(phases) and bool(phases.call_function("IsPhaseActive",GameplayTag(TagName="ShooterGame.GamePhase.Warmup")))
        if active:
            self.report["native_warmup_observed"]=True
        rows=[read_json(self.root/(peer+"-warmup-joined.json")) for peer in PEERS]
        if not all(rows): return
        if not active: raise RuntimeError("controlled clients did not join native warmup")
        if any(row["run_id"]!=self.run or row["peer"]!=peer for peer,row in zip(PEERS,rows)): raise RuntimeError("foreign warmup join beacon")
        if len({row["player_id"] for row in rows})!=2: raise RuntimeError("warmup clients are not distinct")
        self.report.update(joined_clients=rows,native_warmup_active_at_release=True)
        self.restore_time();self.released=True
    def restore_time(self):
        if self.world is not None and self.original is not None:
            statics=ue.find_class("GameplayStatics").get_cdo()
            statics.call_function("SetGlobalTimeDilation",self.world,self.original)
            self.report["restored"]=float(statics.call_function("GetGlobalTimeDilation",self.world))==self.original
            if not self.report["restored"]: raise RuntimeError("native diagnostic time dilation not restored")
    def close(self):
        if not self.closed:
            if self.peer=="server" and not self.released: self.restore_time()
            self.closed=True
