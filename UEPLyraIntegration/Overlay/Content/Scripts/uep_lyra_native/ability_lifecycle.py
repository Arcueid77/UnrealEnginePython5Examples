"""Jump decisions and death/reset sequencing, with native GAS primitives."""
import copy
import unreal_engine as ue


def metrics(owner):
    if not hasattr(owner,'_uep_native_lifecycle'):owner._uep_native_lifecycle=dict(jump_python=0,jump_native=0,jump_gate=0,jump_start=0,jump_stop=0,death_python=0,death_native=0,death_activate=0,death_end=0,death_start=0,death_finish=0,reset_python=0,reset_native=0,reset_activate=0,trace=[])
    return owner._uep_native_lifecycle


def mark(owner,key,**values):
    m=metrics(owner);m[key]+=1;m['trace'].append(dict(operation=key,**values));del m['trace'][:-128]


class JumpPolicyPython:
    def UEPUsesPythonJumpPolicy(self):mark(self,'jump_python');return True
    def UEPShouldCheckJumpSuper(self,avatar,character,can_jump):mark(self,'jump_gate',avatar=bool(avatar),character=bool(character),can_jump=bool(can_jump));return bool(avatar and character and can_jump)
    def UEPRunJumpStart(self,character,local,pressed):
        mark(self,'jump_start',character=character is not None,local=bool(local),pressed=bool(pressed))
        if character is not None and local and not pressed:character.call_function('UnCrouch',False);character.call_function('Jump')
    def UEPRunJumpStop(self,character,local,pressed):
        mark(self,'jump_stop',character=character is not None,local=bool(local),pressed=bool(pressed))
        if character is not None and local and pressed:character.call_function('StopJumping')


class JumpPolicyNative:
    def UEPUsesPythonJumpPolicy(self):mark(self,'jump_native');return self.call_mixin_original('UEPUsesPythonJumpPolicy')
    def UEPShouldCheckJumpSuper(self,*args):raise AssertionError('Native Jump reached Python gate')
    def UEPRunJumpStart(self,*args):raise AssertionError('Native Jump reached Python start')
    def UEPRunJumpStop(self,*args):raise AssertionError('Native Jump reached Python stop')


class DeathPolicyPython:
    def UEPUsesPythonDeathPolicy(self):mark(self,'death_python');return True
    def UEPDeathActivationPlan(self,auto_start):
        plan=['CancelOthers','MakeUncancelable','BlockAbilities']+(['StartDeath'] if auto_start else [])+['ActivateBlueprint'];mark(self,'death_activate',plan=copy.copy(plan));return plan
    def UEPDeathEndPlan(self):
        plan=['FinishDeath','EndBlueprint'];mark(self,'death_end',plan=copy.copy(plan));return plan
    def UEPShouldStartDeath(self,has_health,state):mark(self,'death_start',has_health=bool(has_health),state=int(state));return bool(has_health and int(state)==0)
    def UEPShouldFinishDeath(self,has_health,state):mark(self,'death_finish',has_health=bool(has_health),state=int(state));return bool(has_health and int(state)==1)


class DeathPolicyNative:
    def UEPUsesPythonDeathPolicy(self):mark(self,'death_native');return self.call_mixin_original('UEPUsesPythonDeathPolicy')
    def UEPDeathActivationPlan(self,*args):raise AssertionError('Native death reached Python plan')
    def UEPDeathEndPlan(self,*args):raise AssertionError('Native death reached Python end')
    def UEPShouldStartDeath(self,*args):raise AssertionError('Native death reached Python start')
    def UEPShouldFinishDeath(self,*args):raise AssertionError('Native death reached Python finish')


class ResetPolicyPython:
    def UEPUsesPythonResetPolicy(self):mark(self,'reset_python');return True
    def UEPResetActivationPlan(self):
        plan=['CancelOthers','MakeUncancelable','ResetCharacter','BroadcastReset','ActivateBlueprint','EndAbility'];mark(self,'reset_activate',plan=copy.copy(plan));return plan


class ResetPolicyNative:
    def UEPUsesPythonResetPolicy(self):mark(self,'reset_native');return self.call_mixin_original('UEPUsesPythonResetPolicy')
    def UEPResetActivationPlan(self):raise AssertionError('Native reset reached Python plan')


def combined(base,policy,name):
    omitted={'__module__','__dict__','__weakref__','__doc__','__qualname__'}
    attributes={key:value for parent in reversed(base.__mro__) if parent is not object for key,value in vars(parent).items() if key not in omitted};attributes.update({k:v for k,v in vars(policy).items() if k not in omitted});attributes['__module__']=__name__
    return type(name,(),attributes)


from uep_lyra_abilities.jump_mixin import LyraJumpPythonProfile
from uep_lyra_abilities.death_mixin import LyraDeathPythonProfile
JumpPythonProfile=combined(LyraJumpPythonProfile,JumpPolicyPython,'JumpPythonProfile')
JumpNativeProfile=combined(LyraJumpPythonProfile,JumpPolicyNative,'JumpNativeProfile')
DeathPythonProfile=combined(LyraDeathPythonProfile,DeathPolicyPython,'DeathPythonProfile')
DeathNativeProfile=combined(LyraDeathPythonProfile,DeathPolicyNative,'DeathNativeProfile')


def install_native_reset(default='Python'):
    cls=ue.find_class('LyraGameplayAbility_Reset')
    if cls.get_cdo().find_function('UEPUsesPythonResetPolicy') is None:return False
    ue.register_mixin_profile(cls,'Python',ResetPolicyPython,make_default=default=='Python');ue.register_mixin_profile(cls,'NativeLifecycleFallback',ResetPolicyNative,make_default=default=='NativeLifecycleFallback');return True
