"""Shooter controller and BT decisions; native async/delegates/BT/GAS remain."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .effect_pad_mixin import valid

CLASSES={k:'/ShooterCore/'+p+'.'+p.rsplit('/',1)[-1]+'_C' for k,p in (('controller','Bot/B_AI_Controller_LyraShooter'),('passive','Bot/B_AI_Controller_LyraShooter_Passive'),('cp','ControlPoint/AI/B_AI_Controller_LyraShooter_ControlPoint'),('allowed','Bot/BT/BTDecorator_AllowedToFire'),('ammo','Bot/Services/BTS_CheckAmmo'),('reload','Bot/Services/BTS_ReloadWeapon'),('focus','Bot/Services/BTS_SetFocus'),('shoot','Bot/Services/BTS_Shoot'))}
GATES={k:'UEPShooterAI'+v for k,v in dict(ready='Ready',possess='Possess',death='Death',team='Team',allowed='Allowed',ammo='Ammo',reload='Reload',focus='Focus',shoot='Shoot',weapon='Weapon').items()}
BACKENDS=dict(bind='UEPShooterAINativeBindDeath',observe='UEPShooterAINativeObserveTeam')
MAGAZINE='Lyra.ShooterGame.Weapon.MagazineAmmo'
SPARE='Lyra.ShooterGame.Weapon.SpareAmmo'
FIRE='InputTag.Weapon.Fire'
RELOAD='InputTag.Weapon.Reload'
SLOT='InputTag.Ability.Quickslot.SelectSlot'


def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def evidence(a):
    if not hasattr(a,'_uep_shooter_ai'):a._uep_shooter_ai={p+'_'+k:0 for p in ('python','fallback') for k in GATES};a._uep_shooter_ai['diagnostic_fallbacks']=0
    return a._uep_shooter_ai
def mark(a,k):evidence(a)['python_'+k]+=1
def diagnostic(a):evidence(a)['diagnostic_fallbacks']+=1
def inventory(controller):return controller.get_component_by_type(ue.find_class('LyraInventoryManagerComponent')) if valid(controller) else None
def items(manager):return list(one(manager.call_function('GetAllItems')))
def stacks(item,tag):return int(item.call_function('GetStatTagStackCount',GameplayTag(TagName=tag)))
def total(item):return lib('KismetMathLibrary').call_function('Add_IntInt',stacks(item,SPARE),stacks(item,MAGAZINE))
def blackboard_bool(a,value):lib('BTFunctionLibrary').call_function('SetBlackboardValueAsBool',a,a.get_property('OutOfAmmo'),bool(value))
def send(pawn,tag,magnitude=None):
    payload=GameplayEventData() if magnitude is None else GameplayEventData(EventMagnitude=float(magnitude));lib('AbilitySystemBlueprintLibrary').call_function('SendGameplayEventToActor',pawn,GameplayTag(TagName=tag),payload)


def ready(a):mark(a,'ready');a.call_function('RunBehaviorTree',a.get_property('BTAsset'));a.call_function(BACKENDS['bind']);return False
def possess(a):
    mark(a,'possess');brain=a.get_property('BrainComponent')
    if valid(brain):brain.call_function('StartLogic')
    a.call_function(BACKENDS['observe']);return False
def death(a):
    mark(a,'death');board=lib('AIBlueprintHelperLibrary').call_function('GetBlackboard',a);brain=a.get_property('BrainComponent')
    if not valid(board) or not valid(brain):diagnostic(a);return True
    board.call_function('ClearValue',a.get_property('EnemyNameKey'));brain.call_function('StopLogic','Dead');return False
def team(a):mark(a,'team');a.get_property('AIPerception').call_function('RequestStimuliListenerUpdate');return False
def allowed(a):mark(a,'allowed');return dict(UseOriginal=False,Allowed=bool(lib('LyraDevelopmentStatics').call_function('CanPlayerBotsAttack')))
def ammo(a,controller):
    mark(a,'ammo');manager=inventory(controller)
    if not valid(manager):diagnostic(a);return True
    a.set_property('TotalAmmo',0)
    for item in items(manager):a.set_property('TotalAmmo',lib('KismetMathLibrary').call_function('Add_IntInt',total(item),int(a.get_property('TotalAmmo'))))
    blackboard_bool(a,int(a.get_property('TotalAmmo'))<=0);return False
def reload(a,pawn):mark(a,'reload');send(pawn,RELOAD);return False
def focus(a,controller):
    mark(a,'focus')
    if a.get_property('SetFocus'):
        target=lib('BTFunctionLibrary').call_function('GetBlackboardValueAsActor',a,a.get_property('TargetEnnemy'));owner=lib('AIBlueprintHelperLibrary').call_function('GetAIController',controller);owner.call_function('K2_SetFocus',target)
    else:controller.call_function('K2_ClearFocus')
    return False
def weapon(a,pawn,controller):
    mark(a,'weapon');result=dict(UseOriginal=False,CanShoot=False)
    if not valid(pawn):return result
    equipment=pawn.get_component_by_type(ue.find_class('LyraEquipmentManagerComponent'))
    if not valid(equipment):diagnostic(a);return dict(UseOriginal=True,CanShoot=False)
    equipped=one(equipment.call_function('GetFirstInstanceOfType',ue.find_class('LyraWeaponInstance')))
    if not valid(equipped):return result
    current=equipped.call_function('GetInstigator')
    if not valid(current) or not current.is_a(ue.find_class('LyraInventoryItemInstance')):return result
    if total(current)>0:result['CanShoot']=True;return result
    if stacks(current,SPARE)>0 and stacks(current,MAGAZINE)<=0:return result
    manager=inventory(controller)
    if not valid(manager):diagnostic(a);return dict(UseOriginal=True,CanShoot=False)
    for index,item in enumerate(items(manager)):
        if item!=current and total(item)>0:
            send(pawn,SLOT,index);result['CanShoot']=True;return result
    blackboard_bool(a,True);return result
def shoot(a,controller,pawn):
    mark(a,'shoot')
    if valid(pawn) and bool(one(a.call_function('GetCurrentWeapon',pawn,controller))):send(pawn,FIRE)
    return False


class LyraShooterControllerPythonProfile:
    def Ready(self):return ready(self)
    Ready.override=GATES['ready']
    def Possess(self):return possess(self)
    Possess.override=GATES['possess']
    def Death(self):return death(self)
    Death.override=GATES['death']
    def Team(self):return team(self)
    Team.override=GATES['team']
class LyraShooterAllowedPythonProfile:
    def Allowed(self):return allowed(self)
    Allowed.override=GATES['allowed'];Allowed.uep_named_outputs=True
class LyraShooterAmmoPythonProfile:
    def Ammo(self,OwnerController):return ammo(self,OwnerController)
    Ammo.override=GATES['ammo']
class LyraShooterReloadPythonProfile:
    def Reload(self,ControlledPawn):return reload(self,ControlledPawn)
    Reload.override=GATES['reload']
class LyraShooterFocusPythonProfile:
    def Focus(self,OwnerController):return focus(self,OwnerController)
    Focus.override=GATES['focus']
class LyraShooterShootPythonProfile:
    def Shoot(self,OwnerController,ControlledPawn):return shoot(self,OwnerController,ControlledPawn)
    Shoot.override=GATES['shoot']
    def Weapon(self,Pawn,Controller):return weapon(self,Pawn,Controller)
    Weapon.override=GATES['weapon'];Weapon.uep_named_outputs=True


def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return True
    invoke.override=GATES[k];return invoke
def output_fallback(k,name):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return dict(UseOriginal=True,**{name:False})
    invoke.override=GATES[k];invoke.uep_named_outputs=True;return invoke
class LyraShooterControllerBlueprintFallbackProfile:
    Ready=fallback('ready');Possess=fallback('possess');Death=fallback('death');Team=fallback('team')
class LyraShooterAllowedBlueprintFallbackProfile:Allowed=output_fallback('allowed','Allowed')
class LyraShooterAmmoBlueprintFallbackProfile:Ammo=fallback('ammo')
class LyraShooterReloadBlueprintFallbackProfile:Reload=fallback('reload')
class LyraShooterFocusBlueprintFallbackProfile:Focus=fallback('focus')
class LyraShooterShootBlueprintFallbackProfile:
    Shoot=fallback('shoot');Weapon=output_fallback('weapon','CanShoot')
