"""Collect/sit event order with original native cue/pickup/message/montage payloads."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
CLASSES={k:'/ShooterExplorer/Interact/'+n+'.'+n+'_C' for k,n in (('collect','GA_Interaction_Collect'),('sit','GA_Interaction_Sit'))}
PREP='UEPExplorerInteractionPrepareNativeEvent'
PICKUP='UEPExplorerInteractionNativePickup'
DURATION='UEPExplorerInteractionNativeDurationMessage'
MONTAGE='UEPExplorerInteractionBeginNativeMontage'
ENDED='UEPExplorerInteractionMontageEnded'
def evidence(a):
    if not hasattr(a,'_uep_explorer_actions'):a._uep_explorer_actions=dict(python_activate=0,fallback_activate=0,python_end=0,fallback_end=0,authority=0,client=0,invalid_instigator=0,native_pickups=0,native_duration_messages=0,native_montages=0,trace=[])
    return a._uep_explorer_actions
def activate(a,kind,data):
    counts=evidence(a);counts['python_activate']+=1;a.call_function(PREP,data);counts['trace'].append('prepare')
    if a.call_function('K2_HasAuthority'):
        counts['authority']+=1;instigator=data.Instigator
        if not valid(instigator) or not instigator.is_a(ue.find_class('Pawn')):counts['invalid_instigator']+=1;a.call_function('K2_EndAbility');counts['trace'].append('invalid-end');return
        if kind=='collect':a.call_function(PICKUP,instigator,data.Target);counts['native_pickups']+=1;counts['trace'].append('pickup')
    else:a.call_function(DURATION,data.Instigator);counts['native_duration_messages']+=1;counts['client']+=1;counts['trace'].append('duration')
    a.call_function(MONTAGE);counts['native_montages']+=1;counts['trace'].append('montage')
def ended(a):evidence(a)['python_end']+=1;a.call_function('K2_EndAbility');return False
ended.override=ENDED
def profile(kind,fallback):
    def start(self,EventData):
        if fallback:evidence(self)['fallback_activate']+=1;self.call_mixin_original('K2_ActivateAbilityFromEvent',EventData)
        else:activate(self,kind,EventData)
    def finish(self):
        if fallback:evidence(self)['fallback_end']+=1;return True
        return ended(self)
    finish.override=ENDED
    return dict(K2_ActivateAbilityFromEvent=start,MontageEnded=finish)
for kind in CLASSES:
    for name,fallback in (('Python',False),('BlueprintFallback',True)):
        cls='LyraExplorer'+kind.title()+name+'Profile';globals()[cls]=type(cls,(),profile(kind,fallback))
