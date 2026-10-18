"""Actual dedicated-server world/bots,no local player or simulated client."""
import atexit
import sys
import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_network_bots import isolate_bots
from .grenade_begin_validation import Validation as Begin
from .grenade_begin_contract import validate


class Validation(Begin):
    allowed_native_modes=("DedicatedServer",)
    def __init__(self,result):
        super().__init__(result);self.report.update(headless_runtime_requested=True,headless_source="native existing bot Character",actual_clients=0)
        self.health_fingerprint=None;self.health_stable_since=0.
    def ready(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3,5) or "L_Expanse" not in world.get_name(): continue
            isolate_bots(self.statics,world,ue.find_class("LyraPlayerBotController"))
            bridge=ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",world)
            if not valid(bridge): continue
            snapshot=bridge.call_function("CaptureSnapshot")
            phases=ue.find_class("SubsystemBlueprintLibrary").get_cdo().call_function("GetWorldSubsystem",world,ue.find_class("LyraGamePhaseSubsystem"))
            playing=valid(phases) and phases.call_function("IsPhaseActive",GameplayTag(TagName="ShooterGame.GamePhase.Playing"))
            self.report["headless_readiness"]=dict(native_mode=str(snapshot.NetMode),experience=bool(snapshot.bExperienceLoaded),playing=bool(playing))
            if str(snapshot.NetMode)!="DedicatedServer" or not snapshot.bExperienceLoaded or not playing: continue
            self.world=world;health_rows=self.healths()
            if len(health_rows)<3 or any(value["health"]!=100. or value["death"]!=0 for value in health_rows.values()):
                self.health_fingerprint=None;continue
            fingerprint=tuple(sorted((key,value["health"],value["death"]) for key,value in health_rows.items()))
            self.report["headless_readiness"]["native_health_snapshot"]=health_rows
            if fingerprint!=self.health_fingerprint:
                self.health_fingerprint=fingerprint;self.health_stable_since=time.monotonic();continue
            stable=time.monotonic()-self.health_stable_since
            self.report["headless_readiness"]["stable_seconds"]=stable
            if stable<.5: continue
            pawns,=self.statics.call_function("GetAllActorsOfClass",world,ue.find_class("LyraCharacter"))
            for pawn in pawns:
                health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"));asc=ability_system(pawn)
                if not valid(health) or health.call_function("GetHealth")!=100. or not valid(asc): continue
                state=pawn.get_property("PlayerState")
                if not valid(state) or state.call_function("GetPawn")!=pawn or asc.get_property("AvatarActor")!=pawn: continue
                if asc.call_function("GetGameplayTagCount",GameplayTag(TagName="Gameplay.DamageImmunity")): continue
                self.world,self.pawn,self.health,self.asc=world,pawn,health,asc
                players,=self.statics.call_function("GetAllActorsOfClass",world,ue.find_class("LyraPlayerController"))
                self.report["native_local_or_remote_player_controllers"]=len(players)
                self.report["headless_selected_source"]=dict(actor=pawn.get_path_name(),player_state_pawn=state.call_function("GetPawn").get_path_name(),
                    asc_avatar=asc.get_property("AvatarActor").get_path_name(),role=int(pawn.call_function("GetLocalRole")),health=float(health.call_function("GetHealth")))
                self.controller=pawn.get_property("Controller");self.begin();return
    def validate_report(self): return validate(self.report,expected_mode="DedicatedServer",expect_trail=False)
    def finish(self,error=None):
        if error and hasattr(self,"health_before"):
            after=self.healths();before=self.health_before
            self.report["headless_health_diagnostic"]=dict(before=before,after=after,removed=sorted(set(before)-set(after)),added=sorted(set(after)-set(before)),
                changed={key:dict(before=before[key],after=after[key]) for key in set(before)&set(after) if before[key]!=after[key]})
        super().finish(error)


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeBeginResult=")),None)
if result and "-UEPGrenadeHeadless" in sys.argv:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
