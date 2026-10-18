"""Bounded native Reset inputs while real owners join; never state repair."""
import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_lyra_world.effect_pad_mixin import valid
from . import network_identity as wire
RESET_CLASS="/Script/LyraGame.LyraGameplayAbility_Reset"


def reset_count(pawn):
    value=getattr(pawn,"_uep_character_lifecycle",{})
    return int(value.get("reset_python",0))+int(value.get("reset_fallback",0))


class JoinResetStress:
    def __init__(self,root,run):
        self.root,self.run=root,run;self.started=time.monotonic();self.owners={};self.done=False
        self.report=dict(enabled=True,requests=[],eligibility={},worlds=[],completed=False,callback_replay=False,health_or_asc_written=False,
            entry="SendGameplayEventToActor(GameplayEvent.RequestReset)",requests_per_owner=2)
    def consider(self,controller,seconds):
        state=controller.get_property("PlayerState");pawn=controller.get_controlled_pawn()
        if not valid(state) or not valid(pawn) or pawn.call_function("IsActorBeingDestroyed"): return
        player_id=int(state.PlayerId)
        if player_id<=0: return
        pending=dict(actor=pawn.get_path_name(),reason="native-reset-spec",reset_specs=0)
        self.report["eligibility"][str(player_id)]=pending
        record=self.owners.setdefault(player_id,dict(count=0,last_actor=None,last_time=-1.))
        if record["count"]>=2 or seconds-record["last_time"]<.15: return
        actor=pawn.get_path_name()
        if actor==record["last_actor"]: return
        asc=state.get_property("AbilitySystemComponent")
        if not valid(asc): return
        specs=[item for item in asc.get_property("ActivatableAbilities").Items if valid(item.Ability) and item.Ability.get_class().get_path_name()==RESET_CLASS]
        pending["reset_specs"]=len(specs)
        if len(specs)!=1: return
        identity=wire.read(pawn)
        pending.update(reason="mapped-native-identity",network_identity=identity)
        if wire.key(identity) is None: return
        if identity["local_role"]!=3: raise RuntimeError("join Reset input must remain on native authority")
        if len(self.owners)>2 or len(self.report["requests"])>=4: raise RuntimeError("bounded join Reset input owner/request budget exceeded")
        row=dict(player_id=player_id,old_actor=actor,old_network_identity=identity,server_seconds=seconds,
            native_reset_class=RESET_CLASS,native_reset_existing_specs=1,request_number=record["count"]+1)
        tag=GameplayTag(TagName="GameplayEvent.RequestReset")
        before=reset_count(pawn)
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor",state,tag,GameplayEventData(EventTag=tag,Instigator=state,Target=state))
        row["native_reset_callback_delta"]=reset_count(pawn)-before
        if row["native_reset_callback_delta"]!=1: raise RuntimeError("native join Reset input did not execute exactly one Character Reset callback")
        self.report["requests"].append(row);record.update(count=record["count"]+1,last_actor=actor,last_time=seconds)
        pending["reason"]="native-reset-requested"
    def poll(self):
        if self.done: return
        if time.monotonic()-self.started>=120.: raise RuntimeError("native join Reset stress did not reach its two-owner input budget")
        statics=ue.find_class("GameplayStatics").get_cdo()
        self.report["worlds"]=[]
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3,5) or "L_Expanse" not in world.get_name(): continue
            controllers,=statics.call_function("GetAllActorsOfClass",world,ue.find_class("LyraPlayerController"))
            self.report["worlds"].append(dict(name=world.get_name(),kind=world.get_world_type(),controllers=len(controllers)))
            seconds=float(statics.call_function("GetTimeSeconds",world))
            for controller in controllers: self.consider(controller,seconds)
        if len(self.owners)==2 and all(value["count"]==2 for value in self.owners.values()):
            self.done=True;self.report["completed"]=True
