"""Count/name/removal policy; original native controller spawn and destruction stay."""
import unreal_engine as ue
from .message_processors import lib

CLASSES=('/ShooterCore/Bot/B_ShooterBotSpawner.B_ShooterBotSpawner_C',
         '/ShooterCore/ControlPoint/AI/B_ShooterBotSpawner_ControlPoint.B_ShooterBotSpawner_ControlPoint_C')
PERF='/ShooterCore/Bot/B_ShooterBotSpawner_Perf.B_ShooterBotSpawner_Perf_C'


def metrics(component):
    if not hasattr(component,'_uep_native_bot_metrics'):
        component._uep_native_bot_metrics={p+k:0 for p in ('python_','native_') for k in ('create','name','remove')}
    return component._uep_native_bot_metrics


def remaining(component):
    if not hasattr(component,'_uep_native_bot_names'):component._uep_native_bot_names=[]
    return component._uep_native_bot_names


def random_index(minimum,maximum):return int(lib('KismetMathLibrary').call_function('RandomIntegerInRange',minimum,maximum))


def effective_count(component):
    count=int(component.get_property('NumBotsToCreate'))
    if component.call_function('UEPIsEditorBotContext'):
        settings=ue.find_class('LyraDeveloperSettings').get_cdo()
        if settings.get_property('bOverrideBotCount'):count=int(settings.get_property('OverrideNumPlayerBotsToSpawn'))
    mode=lib('GameplayStatics').call_function('GetGameMode',component)
    if mode is not None:count=int(lib('GameplayStatics').call_function('GetIntOption',mode.get_property('OptionsString'),'NumBots',count))
    return count


def teardown(component):
    if hasattr(component,'_uep_native_bot_names'):component._uep_native_bot_names.clear()


def end_play(component,EndPlayReason):
    component.call_mixin_original('ReceiveEndPlay',EndPlayReason);teardown(component)


class BotPythonProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def ServerCreateBots(self):
        metrics(self)['python_create']+=1
        if self.get_property('BotControllerClass') is None:return
        self._uep_native_bot_names=list(self.get_property('RandomBotNames'))
        for _ in range(effective_count(self)):self.call_function('SpawnOneBot')
    def UEPCreateBotName(self,PlayerIndex):
        metrics(self)['python_name']+=1;names=remaining(self)
        if not names:return 'Tinplate '+str(random_index(260,360))
        index=random_index(0,len(names)-1);value=names[index];names[index]=names[-1];names.pop();return value
    def UEPSelectBotToRemove(self,BotCount):
        metrics(self)['python_remove']+=1;return random_index(0,BotCount-1)


class BotNativeFallbackProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def ServerCreateBots(self):
        metrics(self)['native_create']+=1;return self.call_mixin_original('ServerCreateBots')
    def UEPCreateBotName(self,PlayerIndex):
        metrics(self)['native_name']+=1;return self.call_mixin_original('UEPCreateBotName',PlayerIndex)
    def UEPSelectBotToRemove(self,BotCount):
        metrics(self)['native_remove']+=1;return self.call_mixin_original('UEPSelectBotToRemove',BotCount)
