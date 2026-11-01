"""Interaction option/indicator/first-option policy with native GAS facilities."""
import unreal_engine as ue
from uep_lyra_abilities.explorer_interact_mixin import LyraExplorerInteractPythonProfile as Presentation
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/ShooterExplorer/Input/Abilities/GA_Interact.GA_Interact_C'


def metrics(ability):
    if not hasattr(ability,'_uep_native_interaction'):ability._uep_native_interaction={p+k:0 for p in ('python_','native_') for k in ('update','trigger')}
    return ability._uep_native_interaction


class InteractionPythonProfile(Presentation):
    K2_ActivateAbility=Presentation.K2_ActivateAbility
    K2_OnEndAbility=Presentation.K2_OnEndAbility
    LookForInteractables=Presentation.LookForInteractables
    InteractPressScan=Presentation.InteractPressScan
    OptionsChanged=Presentation.OptionsChanged
    Pressed=Presentation.Pressed

    def UpdateInteractions(self,InteractiveOptions):
        metrics(self)['python_update']+=1
        manager=self.call_function('UEPGetInteractionIndicatorManager')
        if valid(manager):
            for indicator in list(self.get_property('Indicators')):manager.call_function('RemoveIndicator',indicator)
            self.set_property('Indicators',[])
            for option in InteractiveOptions:
                target=self.call_function('UEPGetInteractionTargetActor',option)
                indicator=ue.new_object(ue.find_class('IndicatorDescriptor'))
                indicator.call_function('SetDataObject',target);indicator.call_function('SetSceneComponent',target.get_property('RootComponent'))
                self.call_function('UEPSetInteractionIndicatorClass',indicator,option,self.call_function('UEPHasInteractionWidget',option))
                manager.call_function('AddIndicator',indicator);self.set_property('Indicators',list(self.get_property('Indicators'))+[indicator])
        self.set_property('CurrentOptions',[option.clone() for option in InteractiveOptions])

    def TriggerInteraction(self):
        metrics(self)['python_trigger']+=1;options=self.get_property('CurrentOptions')
        if options and valid(self.call_function('GetAbilitySystemComponentFromActorInfo')):self.call_function('UEPTriggerInteractionOption',options[0])


class InteractionNativeFallbackProfile(Presentation):
    K2_ActivateAbility=Presentation.K2_ActivateAbility
    K2_OnEndAbility=Presentation.K2_OnEndAbility
    LookForInteractables=Presentation.LookForInteractables
    InteractPressScan=Presentation.InteractPressScan
    OptionsChanged=Presentation.OptionsChanged
    Pressed=Presentation.Pressed

    def UpdateInteractions(self,InteractiveOptions):metrics(self)['native_update']+=1;self.call_mixin_original('UpdateInteractions',InteractiveOptions)
    def TriggerInteraction(self):metrics(self)['native_trigger']+=1;self.call_mixin_original('TriggerInteraction')
