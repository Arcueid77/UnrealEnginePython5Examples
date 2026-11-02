"""Numeric cost policy; native context extraction, GAS ordering and writes remain."""
from unreal_engine.structs import UEPTagStackCostCheckResult

OWNERS=(
    ('/Game/Weapons/GA_Weapon_Fire.GA_Weapon_Fire_C','/Game/UEPMixins/DA_WeaponAbilityFireMixin.DA_WeaponAbilityFireMixin','Weapon'),
    ('/ShooterCore/Items/HealthPickup_Unused/GA_HealPickup.GA_HealPickup_C','/Game/UEPMixins/DA_HealAbilityMixin.DA_HealAbilityMixin','Heal'),
    ('/ShooterCore/Weapons/NetShooter_PROTO/GA_WeaponNetShooter.GA_WeaponNetShooter_C','/Game/UEPMixins/DA_NetShooterAbilityMixin.DA_NetShooterAbilityMixin','Net'),
)


def metrics(ability):
    if not hasattr(ability,'_uep_tag_stack_costs'):ability._uep_tag_stack_costs=dict(python_routes=0,native_routes=0,checks=0,applications=0,contexts=[])
    return ability._uep_tag_stack_costs


def record(ability,context,operation):
    metrics(ability)['contexts'].append(dict(operation=operation,player=bool(context.bPlayerStack),authority=bool(context.bAuthority),has_target=bool(context.bHasTarget),quantity=int(context.Quantity),available=int(context.Available),failure_output=bool(context.bHasFailureTagOutput)))
    if len(metrics(ability)['contexts'])>128:del metrics(ability)['contexts'][:-128]


class CostPythonProfile:
    def UEPUsesPythonTagStackCosts(self,player):metrics(self)['python_routes']+=1;return True
    def UEPCheckTagStackCost(self,context):
        metrics(self)['checks']+=1;record(self,context,'check');can_pay=bool(context.bHasTarget) and int(context.Available)>=int(context.Quantity)
        valid_failure=str(context.FailureTag.TagName) not in ('','None')
        return UEPTagStackCostCheckResult(bCanPay=can_pay,bAddFailureTag=not can_pay and bool(context.bHasTarget) and not bool(context.bPlayerStack) and bool(context.bHasFailureTagOutput) and valid_failure)
    def UEPApplyTagStackCost(self,context):metrics(self)['applications']+=1;record(self,context,'apply');return int(context.Quantity)


class CostNativeFallbackProfile:
    def UEPUsesPythonTagStackCosts(self,player):metrics(self)['native_routes']+=1;return self.call_mixin_original('UEPUsesPythonTagStackCosts',player)
    def UEPCheckTagStackCost(self,context):raise AssertionError('Native cost selected before Python evaluation')
    def UEPApplyTagStackCost(self,context):raise AssertionError('Native cost selected before Python mutation')


def combined(base,cost,name):
    # The mixin registry inspects local attributes, so explicitly flatten the
    # previously accepted Python class before adding the three cost methods.
    attributes={key:value for parent in reversed(base.__mro__) for key,value in vars(parent).items() if not key.startswith('__')}
    attributes.update({key:value for key,value in vars(cost).items() if not key.startswith('__')});return type(name,(),attributes)


from uep_lyra_weapons.weapon_ability_fire_mixin import LyraWeaponAbilityFirePythonProfile
from uep_lyra_world.heal_ability_mixin import LyraHealAbilityPythonProfile
from uep_lyra_weapons.netshooter_ability_mixin import LyraNetShooterAbilityPythonProfile
for _name,_base in (('Weapon',LyraWeaponAbilityFirePythonProfile),('Heal',LyraHealAbilityPythonProfile),('Net',LyraNetShooterAbilityPythonProfile)):
    globals()[_name+'CostPythonProfile']=combined(_base,CostPythonProfile,_name+'CostPythonProfile')
    globals()[_name+'CostNativeFallbackProfile']=combined(_base,CostNativeFallbackProfile,_name+'CostNativeFallbackProfile')
