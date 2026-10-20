"""Original interaction order with native scan/input task factories and GAS calls."""
CLASS='/ShooterExplorer/Input/Abilities/GA_Interact.GA_Interact_C'
SCAN='UEPExplorerInteractBeginNativeScan'
WAIT='UEPExplorerInteractBeginNativePressWait'
OPTIONS='UEPExplorerInteractOptionsChanged'
PRESS='UEPExplorerInteractPressed'
AVAILABLE='UEPExplorerInteractPrintAvailable'
UNAVAILABLE='UEPExplorerInteractPrintUnavailable'
PRESSED='UEPExplorerInteractPrintPressed'
def evidence(a):
    if not hasattr(a,'_uep_explorer_interact'):a._uep_explorer_interact={p+'_'+m:0 for p in ('python','fallback') for m in ('activate','end','scan','wait','options','press')};a._uep_explorer_interact.update(last_options=None,last_cancelled=None,trace=[])
    return a._uep_explorer_interact
def activate(a):
    values=evidence(a);values['python_activate']+=1;values['trace'].append('available');a.call_function(AVAILABLE);a.call_function('LookForInteractables');a.call_function('InteractPressScan')
def end(a,cancelled):evidence(a)['python_end']+=1;evidence(a)['last_cancelled']=bool(cancelled);a.call_function(UNAVAILABLE)
def scan(a):evidence(a)['python_scan']+=1;evidence(a)['trace'].append('scan');a.call_function(SCAN)
def wait(a):evidence(a)['python_wait']+=1;evidence(a)['trace'].append('wait');a.call_function(WAIT)
def options(a,InteractiveOptions):evidence(a)['python_options']+=1;evidence(a)['last_options']=len(InteractiveOptions);a.call_function('UpdateInteractions',InteractiveOptions);return False
def press(a):
    values=evidence(a);values['python_press']+=1;values['trace'].append('pressed');a.call_function(PRESSED);a.call_function('TriggerInteraction');values['trace'].append('trigger');a.call_function('InteractPressScan');return False
class LyraExplorerInteractPythonProfile:
    def K2_ActivateAbility(self):activate(self)
    def K2_OnEndAbility(self,bWasCancelled:bool):end(self,bWasCancelled)
    def LookForInteractables(self):scan(self)
    def InteractPressScan(self):wait(self)
    def OptionsChanged(self,InteractiveOptions):return options(self,InteractiveOptions)
    OptionsChanged.override=OPTIONS
    def Pressed(self):return press(self)
    Pressed.override=PRESS
class LyraExplorerInteractBlueprintFallbackProfile:
    def K2_ActivateAbility(self):evidence(self)['fallback_activate']+=1;self.call_mixin_original('K2_ActivateAbility')
    def K2_OnEndAbility(self,bWasCancelled:bool):evidence(self)['fallback_end']+=1;evidence(self)['last_cancelled']=bool(bWasCancelled);self.call_mixin_original('K2_OnEndAbility',bWasCancelled)
    def LookForInteractables(self):evidence(self)['fallback_scan']+=1;self.call_mixin_original('LookForInteractables')
    def InteractPressScan(self):evidence(self)['fallback_wait']+=1;self.call_mixin_original('InteractPressScan')
    def OptionsChanged(self,InteractiveOptions):evidence(self)['fallback_options']+=1;evidence(self)['last_options']=len(InteractiveOptions);return True
    OptionsChanged.override=OPTIONS
    def Pressed(self):evidence(self)['fallback_press']+=1;return True
    Pressed.override=PRESS
