"""Lobby catalog/random/loading-task policy;native async/stream/delegate IO."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
CLASS='/Game/Environments/B_LoadRandomLobbyBackground.B_LoadRandomLobbyBackground_C'
METHODS=('construct','begin','catalog','asset_ready','instance_result','loaded','shown','show','hide','release')
GATES={m:'UEPLobbyBackground'+''.join(v.title() for v in m.split('_')) for m in METHODS}
NATIVE={m:'UEPLobbyBackgroundNative'+m.title() for m in ('catalog','asset','level','bind','delay','unregister')}
REASON='Loading Cosmetic Background'
def evidence(actor):
    if not hasattr(actor,'_uep_lobby_background'):actor._uep_lobby_background={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return actor._uep_lobby_background
def print_message(actor,message):lib('KismetSystemLibrary').call_function('PrintString',actor,message,False,True,ue.find_struct('LinearColor')(R=0.,G=.66,B=1.,A=1.),2.,'None')
def invoke(actor,m,*args):
    evidence(actor)['python_'+m]+=1
    if m=='construct':actor.get_property('EditorOnlyBox').call_function('SetBoxExtent',actor.get_property('BoxExtents'),False)
    elif m=='begin':
        if lib('LyraDevelopmentStatics').call_function('ShouldLoadCosmeticBackgrounds'):actor.call_function(NATIVE['catalog'])
    elif m=='catalog':
        ids=list(args[0])
        if ids:
            index=int(lib('KismetMathLibrary').call_function('RandomIntegerInRange',0,len(ids)-1));actor.set_property('BackgroundToLoad',ids[index]);actor.call_function('ShowLoadingScreen');actor.call_function(NATIVE['asset'])
        else:print_message(actor,'No lobby backgrounds found')
    elif m=='asset_ready':actor.call_function(NATIVE['level'])
    elif m=='instance_result':
        if bool(args[0]):actor.call_function(NATIVE['bind'])
        else:print_message(actor,'Level instance load failed');actor.call_function('HideLoadingScreen')
    elif m=='loaded':print_message(actor,'Lobby background loaded')
    elif m=='shown':print_message(actor,'Lobby background shown');actor.call_function('HideLoadingScreen')
    elif m=='show':actor.set_property('LoadingScreenTask',lib('LoadingProcessTask').call_function('CreateLoadingScreenProcessTask',actor,REASON))
    elif m=='hide':actor.call_function(NATIVE['delay'])
    elif m=='release':actor.call_function(NATIVE['unregister'])
    return False
def method(m,fallback):
    def apply(self,*args):
        if m in ('shown','hide','release'):evidence(self)[m+'_game_time']=float(lib('GameplayStatics').call_function('GetTimeSeconds',self))
        if m=='instance_result':evidence(self)['last_instance']=args[1];evidence(self)['last_instance_success']=bool(args[0])
        if m=='asset_ready':evidence(self)['loaded_background']=args[0]
        if fallback:evidence(self)['fallback_'+m]+=1;return True
        return invoke(self,m,*args)
    apply.override=GATES[m];return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraLobbyBackground'+profile+'Profile']=type('LyraLobbyBackground'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
