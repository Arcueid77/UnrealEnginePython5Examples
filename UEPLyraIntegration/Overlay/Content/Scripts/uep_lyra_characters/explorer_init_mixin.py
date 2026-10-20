"""Original per-character async symbols, named delegates and native wait clocks."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
from .explorer_helpers_mixin import CLASSES
from .explorer_callbacks_mixin import LyraExplorerCallbacksPythonProfile as CallbacksPython,LyraExplorerCallbacksBlueprintFallbackProfile as CallbacksFallback
from . import inventory_wait_mixin as waiting,inventory_ready_mixin as ready

TEAM_BIND='UEPBindCharacterTeamObserver'
EXPERIENCE_BIND='UEPBindCharacterExperienceReady'

def resolve(cls,kind):
    prefix={'team':'OnTeamChanged_','experience':'OnReady_'}[kind]
    values=[name for name in cls.functions() if name.startswith(prefix) and ue.describe_function(cls,name)['owner']==cls.get_path_name()]
    if len(values)!=1:raise RuntimeError('one original Explorer async callback required: '+repr((cls.get_path_name(),kind,values)))
    return values[0]

class OriginalCallback:
    def __init__(self,actor_kind,callback_kind,function):self.actor_kind,self.callback_kind,self.function,self.__wrapped__=actor_kind,callback_kind,function,function
    @property
    def override(self):
        cls=ue.find_class(CLASSES[self.actor_kind])
        if cls is None:raise RuntimeError('original Explorer class must be loaded before registration')
        return resolve(cls,self.callback_kind)
    def __call__(self,*args,**kwargs):return self.function(*args,**kwargs)
    def __get__(self,instance,owner):return self.function.__get__(instance,owner)

def evidence(actor):
    if not hasattr(actor,'_uep_explorer_init'):actor._uep_explorer_init=dict(python_listen=0,fallback_listen=0,team_factories=0,team_binds=0,team_activations=0,python_observed=0,fallback_observed=0,team_updates=0,no_team_noops=0,python_possessed=0,fallback_possessed=0,authority_noops=0,experience_factories=0,experience_binds=0,experience_activations=0,null_factories=0,last_team=None,last_controller=None)
    return actor._uep_explorer_init

def listen(actor):
    counts=evidence(actor);counts['python_listen']+=1;proxy=ue.find_class('AsyncAction_ObserveTeamColors').get_cdo().call_function('ObserveTeamColors',actor)
    if not valid(proxy):counts['null_factories']+=1;return
    counts['team_factories']+=1;actor.call_function(TEAM_BIND,proxy);counts['team_binds']+=1;proxy.call_function('Activate');counts['team_activations']+=1
def listen_fallback(actor):evidence(actor)['fallback_listen']+=1;actor.call_mixin_original('ListenForTeam')
def observed(actor,bTeamSet:bool,TeamId:int,DisplayAsset):
    counts=evidence(actor);counts['python_observed']+=1;counts['last_team']=dict(assigned=bool(bTeamSet),team=int(TeamId),display=DisplayAsset.get_path_name() if valid(DisplayAsset) else None)
    if bTeamSet:actor.call_function('OnTeamOrCosmeticsChanged',TeamId,DisplayAsset);counts['team_updates']+=1
    else:counts['no_team_noops']+=1
def observed_fallback(actor,bTeamSet:bool,TeamId:int,DisplayAsset):
    counts=evidence(actor);counts['fallback_observed']+=1;counts['last_team']=dict(assigned=bool(bTeamSet),team=int(TeamId),display=DisplayAsset.get_path_name() if valid(DisplayAsset) else None);actor.call_mixin_original(resolve(actor.get_class(),'team'),bTeamSet,TeamId,DisplayAsset)
def possessed(actor,NewController):
    counts=evidence(actor);counts['python_possessed']+=1;counts['last_controller']=NewController.get_path_name() if valid(NewController) else None
    if not actor.call_function('HasAuthority'):counts['authority_noops']+=1;return
    proxy=ue.find_class('AsyncAction_ExperienceReady').get_cdo().call_function('WaitForExperienceReady',actor)
    if not valid(proxy):counts['null_factories']+=1;return
    counts['experience_factories']+=1;actor.call_function(EXPERIENCE_BIND,proxy);counts['experience_binds']+=1;proxy.call_function('Activate');counts['experience_activations']+=1
def possessed_fallback(actor,NewController):evidence(actor)['fallback_possessed']+=1;actor.call_mixin_original('ReceivePossessed',NewController)
def experience(actor):
    counts=ready.evidence(actor);counts['python_calls']+=1;reason=waiting.advance(actor,0)
    if reason is None:counts['immediate_grants']+=1
    else:counts[reason]+=1
def experience_fallback(actor):ready.evidence(actor)['fallback_calls']+=1;actor.call_mixin_original(resolve(actor.get_class(),'experience'))
def resume(actor,Linkage:int):waiting.resume(actor,Linkage)
def resume_fallback(actor,Linkage:int):
    if Linkage not in (0,1,2):raise ValueError('invalid native Explorer readiness linkage')
    values=waiting.evidence(actor);values['pending'][Linkage]=False;values['fallback_resumes']+=1;actor.call_mixin_original(resolve(actor.get_class(),'experience'))
resume.override=resume_fallback.override=waiting.RESUME

for actor_kind in CLASSES:
    for profile,parent,is_fallback in (('Python',CallbacksPython,False),('BlueprintFallback',CallbacksFallback,True)):
        methods={name:fn for name,fn in vars(parent).items() if not name.startswith('__')}
        methods.update(ListenForTeam=listen_fallback if is_fallback else listen,ReceivePossessed=possessed_fallback if is_fallback else possessed,PythonObservedTeamChanged=OriginalCallback(actor_kind,'team',observed_fallback if is_fallback else observed),PythonExperienceReady=OriginalCallback(actor_kind,'experience',experience_fallback if is_fallback else experience),PythonInventoryWaitResume=resume_fallback if is_fallback else resume)
        globals()['LyraExplorerInit'+actor_kind.title()+profile+'Profile']=type('LyraExplorerInit'+actor_kind.title()+profile+'Profile',(),methods)
