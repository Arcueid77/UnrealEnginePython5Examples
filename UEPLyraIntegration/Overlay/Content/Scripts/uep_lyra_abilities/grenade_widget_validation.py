"""Native Give -> real Pawn replacement twice -> native Clear, not event replay."""
import atexit
import copy
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_network_bots import isolate_bots
from .auto_respawn_helpers_validation import Validation as Ready,instances,specs
from .auto_respawn_lifecycle_validation import ui_probe
from . import grenade_widget_mixin as policy,grenade_widget_observation as observation
from .grenade_widget_contract import require,validate

PROFILES=("BlueprintFallback","Python")


def roots(asc):
    return [item for item in asc.get_property("ActivatableAbilities").Items if valid(item.Ability) and item.Ability.get_class().get_path_name()==policy.CLASS]


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.clone=None;self.target_path=None;self.installed=False;self.cleaned=False
        self.native_events=[];self.observation_errors=[];self.quiet_ticks=0
        self.report=dict(schema_version=1,status="running",error=None,cases=[],observation_errors=self.observation_errors,
            full_acceptance=False,network_acceptance=False,packaged_runtime=False,physical_input_tested=False,
            grenade_throw_projectile_damage_migrated=False,callback_replay=False,health_properties_written=False,
            native_ui_pool_written=False,
            ability_spec_properties_written=False,inventory_properties_written=False,native_give_clear_called_by_fixture=True,
            reset_request_entry="SendGameplayEventToActor(GameplayEvent.RequestReset)")
    def widgets(self):
        if not hasattr(self,"points"):
            cls=ue.find_class("UIExtensionPointWidget")
            self.points=[value for value in self.world.all_objects() if valid(value) and value.is_a(cls) and
                value.call_function("GetOwningPlayer")==self.controller and str(value.get_property("ExtensionPointTag").TagName)==policy.TAG]
            require(bool(self.points),"actual local-player native Grenade UI extension point missing")
        # DynamicEntryBox pools attach entries in Slate, not UPanelWidget Slots.
        # A live UObject or GetParent() is not evidence of pool membership.
        return sorted(value.get_path_name() for point in self.points for value in point.call_function("GetAllEntries") if value.is_a(ue.load_class(policy.WIDGET)))
    def begin(self):
        self.original_specs=specs(self.asc);self.original_grenade_handles=[int(item.Handle.Handle) for item in roots(self.asc)]
        require(len(self.original_grenade_handles)==1,"one actual original Grenade spec required")
        self.original_widgets=self.widgets();require(len(self.original_widgets)==1,"one attached original Grenade cooldown widget required")
        observation.install(self);self.installed=True
        self.report.update(native_mode=str(ue.find_class("UEPLyraBridgeLibrary").get_cdo().call_function("GetBridgeForWorld",self.world).call_function("CaptureSnapshot").NetMode),
            owning_player_state=self.controller.PlayerState.get_path_name(),original_specs=self.original_specs,
            original_grenade_handles=self.original_grenade_handles,original_widgets=self.original_widgets)
        self.enter("grant")
    def grant(self):
        self.native_events=[];self.handle=self.asc.call_function("K2_GiveAbility",ue.load_class(policy.CLASS),1,-1)
        item,=[item for item in roots(self.asc) if int(item.Handle.Handle)==int(self.handle.Handle)]
        values=[value for value in list(item.NonReplicatedInstances)+list(item.ReplicatedInstances) if valid(value)]
        require(len(values)==1,"one real test-owned Grenade primary instance required")
        self.clone=values[0];self.target_path=self.clone.get_path_name();profile=PROFILES[self.index];ue.set_mixin_profile(self.clone,profile)
        require(not ui_probe(self.clone)["valid"] and len(roots(self.asc))==2,"new native Grenade grant must start without UI")
        self.row=dict(profile=profile,native_class=self.clone.get_class().get_path_name(),test_handle=int(self.handle.Handle),
            reset_requests=0,native_callbacks=[],initial_ui_invalid=True,original_handle_preserved=True)
        self.request_reset()
    def request_reset(self):
        self.old_pawn=self.controller.get_controlled_pawn().get_path_name()
        tag=GameplayTag(TagName="GameplayEvent.RequestReset");owner=self.controller.PlayerState
        ue.find_class("AbilitySystemBlueprintLibrary").get_cdo().call_function("SendGameplayEventToActor",owner,tag,GameplayEventData(EventTag=tag,Instigator=owner,Target=owner))
        self.row["reset_requests"]+=1;self.enter("respawn")
    def respawn(self):
        require(time.monotonic()-self.phase_started<30.,"native Grenade UI Pawn replacement timeout")
        pawn=self.controller.get_controlled_pawn()
        if not valid(pawn) or pawn.get_path_name()==self.old_pawn: return
        health=pawn.get_component_by_type(ue.find_class("LyraHealthComponent"))
        if not valid(health) or health.call_function("GetHealth")<=0: return
        if self.asc.call_function("GetGameplayTagCount",GameplayTag(TagName="Gameplay.DamageImmunity"))!=0: return
        self.pawn,self.health=pawn,health
        require(ui_probe(self.clone)["valid"],"native avatar callback did not register Grenade UI")
        widgets=self.widgets();require(len(widgets)==len(self.original_widgets)+1,"native Grenade UI registration duplicate/missing attached widget")
        self.row.setdefault("new_pawns",[]).append(pawn.get_path_name())
        if self.row["reset_requests"]==1:
            self.row["registered_widgets"]=widgets;self.request_reset();return
        require(widgets==self.row["registered_widgets"],"existing-handle avatar callback recreated native UI")
        self.asc.call_function("ClearAbility",self.handle)
        require(not any(int(item.Handle.Handle)==int(self.handle.Handle) for item in roots(self.asc)),"native Clear left test-owned Grenade spec")
        self.clone=None;self.quiet_ticks=0;self.row["native_callbacks"]=copy.deepcopy(self.native_events)
        require(specs(self.asc)==self.original_specs,"native gameplay ability class/persistent spec restoration differs")
        require([int(item.Handle.Handle) for item in roots(self.asc)]==self.original_grenade_handles,"original Grenade handle changed")
        self.enter("quiet")
    def quiet(self):
        require(self.widgets()==self.original_widgets,"native Clear did not remove only the test widget")
        require(self.native_events==self.row["native_callbacks"],"late test-owned Grenade native callback")
        self.quiet_ticks+=1
        if self.quiet_ticks<20: return
        self.row.update(quiet_ticks=self.quiet_ticks,original_widget_restored=True,specs_restored=specs(self.asc)==self.original_specs)
        self.report["cases"].append(copy.deepcopy(self.row));self.index+=1
        if self.index==len(PROFILES): self.finish()
        else: self.enter("grant")
    def cleanup(self):
        if self.cleaned: return
        if hasattr(self,"asc") and hasattr(self,"handle"):
            if any(int(item.Handle.Handle)==int(self.handle.Handle) for item in roots(self.asc)): self.asc.call_function("ClearAbility",self.handle)
            self.clone=None
        self.report["observers_restored"]=observation.restore() if self.installed else True
        if hasattr(self,"original_grenade_handles"):
            self.report["test_owned_specs_removed"]=([int(item.Handle.Handle) for item in roots(self.asc)]==self.original_grenade_handles)
        self.cleaned=True
    def tick(self,seconds):
        if self.finished: return False
        try:
            require(time.monotonic()-self.started<250.,"native Grenade UI total timeout")
            if self.phase=="ready": self.ready()
            else:
                isolate_bots(self.statics,self.world,ue.find_class("LyraPlayerBotController"))
                if self.phase=="grant": self.grant()
                elif self.phase=="respawn": self.respawn()
                elif self.phase=="quiet": self.quiet()
            self.report["phase"]=self.phase;self.write();return not self.finished
        except Exception: self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished: return
        self.finished=True
        try: self.cleanup()
        except Exception: error=(error or "")+traceback.format_exc()
        self.report.update(status="failed" if error else "awaiting_shutdown",error=error);self.write()
        (ue.log_error if error else ue.log)("UEP_GRENADE_WIDGET_DIFFERENTIAL_"+("FAILED "+error if error else "PASSED"));ue.request_exit()
    def finalize(self):
        if self.report["status"]=="awaiting_shutdown":
            try: self.report["status"]="passed";validate(self.report)
            except Exception: self.report.update(status="failed",error=traceback.format_exc())
        self.write();(ue.log if self.report["status"]=="passed" else ue.log_error)("UEP_GRENADE_WIDGET_SHUTDOWN_"+self.report["status"].upper())


result=next((value.split("=",1)[1] for value in sys.argv if value.startswith("-UEPGrenadeWidgetResult=")),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
