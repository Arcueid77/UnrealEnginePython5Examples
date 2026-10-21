"""Stat decisions with original native Delay, lazy image, FText and GAS APIs."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
CLASS='/TopDownArena/UserInterface/Player/W_Powerup_Stat.W_Powerup_Stat_C'
PREPARE='UEPArenaStatPrepareConfigure'
BIND='UEPBindArenaStatAttribute'
DELAY='UEPArenaStatBeginNativeRetry'
NUMBER='UEPArenaStatSetNumberText'
BOUND='Changed_6B06FAF740140AA3EA4F94AC562674B4'
def lib(name):return ue.find_class(name).get_cdo()
def evidence(widget):
    value=getattr(widget,'_uep_arena_powerup_stat',None)
    if value is None:
        value={p+k:0 for p in ('python_','fallback_') for k in ('configure','update','listen','changed')};value.update(cancels=0,factories=0,activations=0,retries=0,animations=0,payloads=[]);widget._uep_arena_powerup_stat=value
    return value
def query(widget):
    result=lib('AbilitySystemBlueprintLibrary').call_function('GetFloatAttribute',Actor=widget.get_property('Ability Target'),Attribute=widget.get_property('Attribute'))
    if not isinstance(result,tuple) or len(result)!=2 or type(result[1]) is not bool:raise RuntimeError('native GetFloatAttribute output ABI differs')
    return float(result[0]),result[1]

class LyraArenaPowerupStatPythonProfile:
    def PrepareConfigure(self,AbilityTarget,Attribute):
        value=evidence(self);value['python_configure']+=1;old=self.get_property('AsyncAttributeChanged')
        if valid(old):old.call_function('Cancel');value['cancels']+=1
        self.set_property('Ability Target',AbilityTarget);self.set_property('Attribute',Attribute.clone())
        # False joins the original lazy-image node. Its soft reference remains
        # in the native frame; the next original call dispatches ListenFor.
        return False
    PrepareConfigure.override=PREPARE
    def UpdateText(self,Value):
        evidence(self)['python_update']+=1;number=lib('KismetMathLibrary').call_function('Round64',float(Value));self.call_function(NUMBER,number)
    def ListenFor(self):
        value=evidence(self);value['python_listen']+=1
        lib('KismetSystemLibrary').call_function('PrintString',self,'Stat',True,True,ue.FLinearColor(0.,.66,1.,1.),2.,'None')
        number,found=query(self)
        if not found:self.call_function(DELAY);value['retries']+=1;return
        self.call_function('UpdateText',number)
        proxy=lib('AbilityAsync_WaitAttributeChanged').call_function('WaitForAttributeChanged',self.get_property('Ability Target'),self.get_property('Attribute'),False);value['factories']+=1
        self.call_function(BIND,proxy);proxy.call_function('Activate');value['activations']+=1;self.set_property('AsyncAttributeChanged',proxy)
    def ObservedChanged(self,Attribute,NewValue:float,OldValue:float):
        value=evidence(self);value['python_changed']+=1;value['payloads'].append([float(NewValue),float(OldValue)])
        self.call_function('UpdateText',NewValue);self.call_function('PlayAnimation',self.get_property('AnimationUp'),0.,1,0,1.,False);value['animations']+=1
    ObservedChanged.override=BOUND

class LyraArenaPowerupStatBlueprintFallbackProfile:
    def PrepareConfigure(self,AbilityTarget,Attribute):evidence(self)['fallback_configure']+=1;return True
    PrepareConfigure.override=PREPARE
    def UpdateText(self,Value):evidence(self)['fallback_update']+=1;self.call_mixin_original('UpdateText',Value)
    def ListenFor(self):evidence(self)['fallback_listen']+=1;self.call_mixin_original('ListenFor')
    def ObservedChanged(self,Attribute,NewValue:float,OldValue:float):
        value=evidence(self);value['fallback_changed']+=1;value['payloads'].append([float(NewValue),float(OldValue)]);self.call_mixin_original(BOUND,Attribute,NewValue,OldValue)
    ObservedChanged.override=BOUND
