"""Native GAS base clamps plus unchanged two-local-player bomb input/refund."""
import atexit
import copy
from pathlib import Path
import sys
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write
from uep_lyra_abilities import arena_local_input_validation as original
from . import global_policy,rule_policies


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def array(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value


class Validation(original.Validation):
    def __init__(self):
        self.cpp_profile=arg('UEPNativeAttributeProfile');self.cpp_class=ue.load_class(global_policy.CLASS);ue.register_declared_mixin(self.cpp_class)
        self.cpp_cdo=self.cpp_class.get_cdo();self.cpp_original=self.cpp_cdo.get_property('PythonMixinProfile');self.cpp_cdo.set_property('PythonMixinProfile',self.cpp_profile)
        self.clamp_cases=[];self.clamps_done=False;self.cpp_metrics={};self.cpp_restored=False
        super().__init__(result=arg('UEPNativeAttributeResult'),profile='Python')
    def discover_world(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or world.get_name()!='L_TopDown_LocalMultiplayer':continue
            phase=original.drop.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',world,ue.find_class('LyraGamePhaseSubsystem'))
            controller=self.statics.call_function('GetPlayerController',world,0)
            if not original.valid(controller) or not original.valid(controller.get_controlled_pawn()) or not phase.call_function('IsPhaseActive',GameplayTag(TagName='ShooterGame.GamePhase.Playing')):continue
            self.world=world
            self.require(not original.valid(self.statics.call_function('GetPlayerController',world,1)),'fresh attribute lane requires one initial local player')
            before_bombs=self.bombs();before,found=self.attributes.call_function('ReadBombsRemaining',controller.PlayerState)
            self.require(found,'original first-player bomb attribute missing before Slate setup')
            # SceneViewport starts with Handled when its headless extent is zero.
            # Observe gameplay state rather than treating that reply as an action.
            handled=ue.FSlateApplication.process_key_char_event(ue.FCharacterEvent('',False,ue.FModifierKeysState(),1))
            after,found=self.attributes.call_function('ReadBombsRemaining',controller.PlayerState)
            self.require(found and before==after and self.bombs()==before_bombs,'neutral Slate setup changed original gameplay state')
            self.report.update(synthetic_slate_user_bootstrap='NUL character for user index 1 before native CreatePlayer',neutral_slate_reply_handled=bool(handled),neutral_slate_gameplay_unchanged=True)
            self.created=self.statics.call_function('CreatePlayer',world,-1,True)
            self.require(original.valid(self.created),'native CreatePlayer did not create second local player')
            bridge=original.drop.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            self.report.update(map=world.get_name(),native_mode=str(bridge.call_function('CaptureSnapshot').NetMode),local_player_creation='GameplayStatics.CreatePlayer')
            self.rule_host=ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext',self.world)
            self.require(str(ue.get_mixin_profile(self.rule_host))==self.cpp_profile,'native attribute profile was not selected before local-player creation')
            self.enter('players');return
    def discover_players(self):
        super().discover_players()
        if self.phase!='settle' or self.clamps_done:return
        fixture=ue.find_class('UEPNativeRuleFixture').get_cdo();attr_class=ue.find_class('TopDownArenaAttributeSet')
        for index,player in enumerate(self.players):
            sets=[value for value in player['asc'].get_property('SpawnedAttributes') if original.valid(value) and value.is_a(attr_class)]
            self.require(len(sets)==1,'one original Arena attribute set required per local player');attribute_set=sets[0]
            names=('BombCapacity','BombsRemaining','BombRange','MovementSpeed')
            saved={name:float(attribute_set.get_property(name).BaseValue) for name in names}
            attributes={str(value.AttributeName):value for value in array(player['asc'].call_function('GetAllAttributes'))}
            trials=(('BombCapacity',3.,3.),('BombsRemaining',5.,3.),('BombsRemaining',-1.,0.),('BombRange',0.,1.),('MovementSpeed',100.,200.),('MovementSpeed',900.,800.),('BombCapacity',0.,1.),('BombsRemaining',5.,1.))
            try:
                for name,value,expected in trials:
                    actual=float(fixture.call_function('SetAttributeBase',player['asc'],attributes[name],value));self.require(abs(actual-expected)<.00001,'native GAS clamp differs: '+name)
                    self.clamp_cases.append(dict(player=index,attribute=name,input=value,result=actual))
            finally:
                for name in names:fixture.call_function('SetAttributeBase',player['asc'],attributes[name],saved[name])
            self.require(all(abs(float(attribute_set.get_property(name).BaseValue)-saved[name])<.00001 for name in names),'original Arena base values were not restored')
        self.clamps_done=True
    def cleanup(self):
        if hasattr(self,'rule_host'):self.cpp_metrics=copy.deepcopy(rule_policies.metrics(self.rule_host))
        try:super().cleanup()
        finally:
            self.cpp_cdo.set_property('PythonMixinProfile',self.cpp_original);self.cpp_restored=self.cpp_cdo.get_property('PythonMixinProfile')==self.cpp_original
    def finalize(self):
        super().finalize()
        result=dict(status=self.report['status'],error=self.report.get('error'),cpp_profile=self.cpp_profile,native_clamp_base_values_written_by_fixture=True,clamp_cases=self.clamp_cases,base_values_restored_before_input_phase=self.clamps_done,cpp_selector_restored=self.cpp_restored,rule_metrics=self.cpp_metrics,previous_blueprint_python_fixed=True,original_input_phase=copy.deepcopy(self.report),physical_input_tested=False,network_acceptance=False)
        if result['status']=='passed':
            try:
                from .attribute_validation_contract import validate
                validate(result)
            except Exception:result.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,result)
        (ue.log if result['status']=='passed' else ue.log_error)('UEP_NATIVE_ATTRIBUTE_SHUTDOWN_'+result['status'].upper())


validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
