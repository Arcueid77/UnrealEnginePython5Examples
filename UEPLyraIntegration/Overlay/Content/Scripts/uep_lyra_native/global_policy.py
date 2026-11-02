"""Blueprint policy carrier shared by native-only gameplay owners."""
from pathlib import Path
import unreal_engine as ue

CLASS='/Game/UEPNative/BP_GlobalGameplayPolicy.BP_GlobalGameplayPolicy_C'


def metrics(owner):
    if not hasattr(owner,'_uep_global_policy'):owner._uep_global_policy=dict(python_routes=0,native_routes=0,reset_plans=0,trace=[])
    return owner._uep_global_policy


class GameplayPolicyPython:
    def UEPUsesPythonPolicy(self,operation):
        m=metrics(self);m['python_routes']+=1;return str(operation) in ('Reset.Activate',)
    def UEPApplyPolicy(self,context):
        operation=str(context.Operation);m=metrics(self)
        if operation=='Reset.Activate':
            actions=['CancelOthers','MakeUncancelable','ResetCharacter','BroadcastReset','ActivateBlueprint','EndAbility'];context.set_property('Actions',actions);m['reset_plans']+=1;m['trace'].append(dict(operation=operation,has_character=bool(context.bHasCharacter),actions=actions));del m['trace'][:-128];context.set_property('bCompleted',True);return
        raise AssertionError('Unsupported native policy operation: '+operation)
    def UEPChooseObject(self,operation,primary,secondary):raise AssertionError('Unsupported object-selection operation: '+str(operation))


class GameplayPolicyNative:
    def UEPUsesPythonPolicy(self,operation):metrics(self)['native_routes']+=1;return self.call_mixin_original('UEPUsesPythonPolicy',operation)
    def UEPApplyPolicy(self,context):raise AssertionError('Native policy reached Python dispatch')
    def UEPChooseObject(self,*args):raise AssertionError('Native policy reached Python object selection')


def register_if_available():
    content=Path(ue.convert_relative_path_to_full(ue.get_content_dir()))
    if not (content/'UEPNative/BP_GlobalGameplayPolicy.uasset').is_file():return False
    cls=ue.load_class(CLASS);ue.register_declared_mixin(cls);return True
