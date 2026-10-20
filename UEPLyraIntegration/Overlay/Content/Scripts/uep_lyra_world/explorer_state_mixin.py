"""Explorer StateTree node policy;native context,AI tasks and latent clocks."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
CLASSES={'eval':'/ShooterExplorer/AI/StateTrees/Evaluators/EV_PlayerPosition.EV_PlayerPosition_C','location':'/ShooterExplorer/AI/StateTrees/Tasks/STT_GetPlayerLocation.STT_GetPlayerLocation_C','follow':'/ShooterExplorer/AI/StateTrees/Tasks/STT_Follow.STT_Follow_C','goto':'/ShooterExplorer/AI/StateTrees/Tasks/STT_GoTo.STT_GoTo_C','delay':'/ShooterExplorer/AI/StateTrees/Tasks/STT_SimpleDebugDelays.STT_SimpleDebugDelays_C'}
METHODS={'eval':('tick',),'location':('tick',),'follow':('enter','success','failed'),'goto':('enter','success','failed'),'delay':('enter','tick','enter_done','tick_done')}
GATES={kind:{m:'UEPExplorerState'+kind.title()+''.join(v.title() for v in m.split('_')) for m in methods} for kind,methods in METHODS.items()}
NATIVE={kind:{m:'UEPExplorerState'+kind.title()+'Native'+''.join(v.title() for v in m.split('_')) for m in methods} for kind,methods in {'eval':('location',),'location':('location',),'follow':('move',),'goto':('move',),'delay':('enter_delay','tick_delay')}.items()}
def evidence(obj,kind):
    if not hasattr(obj,'_uep_explorer_state'):obj._uep_explorer_state={p+'_'+m:0 for p in ('python','fallback') for m in METHODS[kind]}
    return obj._uep_explorer_state
def message(obj,text):lib('KismetSystemLibrary').call_function('PrintString',obj,text,True,True,ue.find_struct('LinearColor')(R=0.,G=.66,B=1.,A=1.),2.,'None')
def wait_message(obj,state):
    value=lib('KismetStringLibrary').call_function('Conv_DoubleToString',float(obj.get_property('Delay')));message(obj,'Wait for '+str(value)+' Seconds In State '+state)
def invoke(obj,kind,m,*args):
    evidence(obj,kind)['python_'+m]+=1
    if kind in ('eval','location'):obj.set_property('PlayerPosition' if kind=='eval' else 'PlayerLocation',obj.call_function(NATIVE[kind]['location']))
    elif kind in ('follow','goto'):
        if m=='enter':obj.call_function(NATIVE[kind]['move'])
        else:obj.call_function('FinishTask',m=='success')
    elif m=='enter':wait_message(obj,'EnterState');obj.set_property('DelayInProgress',True);obj.call_function(NATIVE['delay']['enter_delay'])
    elif m=='tick':
        if not obj.get_property('DelayInProgress'):wait_message(obj,'Tick');obj.set_property('DelayInProgress',True);obj.call_function(NATIVE['delay']['tick_delay'])
    elif m=='enter_done':obj.set_property('DelayInProgress',False);message(obj,'Enter State Done')
    elif m=='tick_done':message(obj,'Tick Done');obj.call_function('FinishTask',True)
    return False
def method(kind,m,fallback):
    def apply(self,*args):
        if fallback:evidence(self,kind)['fallback_'+m]+=1;return True
        return invoke(self,kind,m,*args)
    apply.override=GATES[kind][m];return apply
for kind in METHODS:
    for profile,fallback in (('Python',False),('BlueprintFallback',True)):
        globals()['LyraExplorerState'+kind.title()+profile+'Profile']=type('LyraExplorerState'+kind.title()+profile+'Profile',(),{m:method(kind,m,fallback) for m in METHODS[kind]})
