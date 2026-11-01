"""Native subscriptions own transport; these profiles own the message rules."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag, LyraVerbMessage
from . import message_rules as rules

CLASSES = {
    'streak':'/ShooterCore/Accolades/B_ElimStreakProcessor.B_ElimStreakProcessor_C',
    'chain':'/ShooterCore/Accolades/B_ElimChainProcessor.B_ElimChainProcessor_C',
    'assist':'/Game/UEPNative/BP_AssistProcessor.BP_AssistProcessor_C',
}
ELIMINATION='UEPHandleElimination'
DAMAGE='UEPHandleDamage'
ADAPTER='/Game/UEPInterop/BP_UEPGameplayMessages.BP_UEPGameplayMessages_C'


def lib(name):return ue.find_class(name).get_cdo()


def state(component):
    if not hasattr(component,'_uep_native_message_history'):
        component._uep_native_message_history={}
    return component._uep_native_message_history


def metrics(component):
    if not hasattr(component,'_uep_native_message_metrics'):
        component._uep_native_message_metrics=dict(python_eliminations=0,python_damage=0,
            native_eliminations=0,native_damage=0,broadcasts=0,end_play=0)
    return component._uep_native_message_metrics


def cast_player(obj):
    return obj if obj is not None and obj.is_a(ue.find_class('PlayerState')) else None


def player_from_object(obj):
    return lib('LyraVerbMessageHelpers').call_function('GetPlayerStateFromObject',obj)


def clock(component):
    game_state=lib('GameplayStatics').call_function('GetGameState',component)
    return float(game_state.call_function('GetServerWorldTimeSeconds')) if game_state is not None else 0.


def broadcast(component, message):
    router=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',component,ue.find_class('GameplayMessageSubsystem'))
    ue.load_class(ADAPTER).get_cdo().call_function('BroadcastVerb',router,message.Verb,message)
    metrics(component)['broadcasts']+=1


def streak(component, payload):
    metrics(component)['python_eliminations']+=1
    for tag,player,count in rules.streak_elimination(state(component),payload.Instigator,payload.Target,
                                                    cast_player,component.get_property('ElimStreakTags')):
        broadcast(component,LyraVerbMessage(Verb=tag,Instigator=player,Magnitude=float(count),
            InstigatorTags=payload.InstigatorTags,ContextTags=payload.ContextTags))


def chain(component, payload):
    metrics(component)['python_eliminations']+=1
    for tag,player,count in rules.chain_elimination(state(component),payload.Instigator,payload.Target,
            cast_player,component.get_property('ElimChainTags'),lambda:clock(component),float(component.get_property('ChainTimeLimit'))):
        broadcast(component,LyraVerbMessage(Verb=tag,Instigator=player,Magnitude=float(count),
            InstigatorTags=payload.InstigatorTags,ContextTags=payload.ContextTags))


def damage(component, payload):
    metrics(component)['python_damage']+=1
    rules.assist_damage(state(component),payload.Instigator,payload.Target,float(payload.Magnitude),player_from_object)


def assist(component, payload):
    metrics(component)['python_eliminations']+=1
    for player,target,total in rules.assist_elimination(state(component),payload.Instigator,payload.Target,cast_player):
        broadcast(component,LyraVerbMessage(Verb=GameplayTag(TagName='Lyra.Assist.Message'),Instigator=player,
            Target=target,Magnitude=float(total),TargetTags=payload.TargetTags,ContextTags=payload.ContextTags))


def teardown(component):
    if hasattr(component,'_uep_native_message_history'):
        component._uep_native_message_history.clear()


def end_play(component, EndPlayReason):
    component.call_mixin_original('ReceiveEndPlay',EndPlayReason)
    teardown(component)
    metrics(component)['end_play']+=1


class StreakPythonProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def UEPHandleElimination(self,Channel,Payload):return streak(self,Payload)


class StreakNativeFallbackProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def UEPHandleElimination(self,Channel,Payload):
        metrics(self)['native_eliminations']+=1
        return self.call_mixin_original(ELIMINATION,Channel,Payload)


class ChainPythonProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def UEPHandleElimination(self,Channel,Payload):return chain(self,Payload)


class ChainNativeFallbackProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def UEPHandleElimination(self,Channel,Payload):
        metrics(self)['native_eliminations']+=1
        return self.call_mixin_original(ELIMINATION,Channel,Payload)


class AssistPythonProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def UEPHandleElimination(self,Channel,Payload):return assist(self,Payload)
    def UEPHandleDamage(self,Channel,Payload):return damage(self,Payload)


class AssistNativeFallbackProfile:
    ReceiveEndPlay=end_play
    __uep_mixin_teardown__=teardown
    def UEPHandleElimination(self,Channel,Payload):
        metrics(self)['native_eliminations']+=1
        return self.call_mixin_original(ELIMINATION,Channel,Payload)
    def UEPHandleDamage(self,Channel,Payload):
        metrics(self)['native_damage']+=1
        return self.call_mixin_original(DAMAGE,Channel,Payload)
