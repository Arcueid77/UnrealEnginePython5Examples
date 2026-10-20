"""EQS policy with original world enumeration, native teams and live query writes."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid
from .shooter_ai_mixin import one,SPARE

CLASSES={k:'/ShooterCore/Bot/EQS/'+p+'.'+p.rsplit('/',1)[-1]+'_C' for k,p in (('points','Context/EQS_Context_ControlPoints'),('enemy','Context/EQS_Context_TargetEnemy'),('weapon','Context/EQS_Context_WeaponCheck'),('enemies','Generator/EQS_GetAllEnemy'))}
GATES={k:'UEPShooterEQS'+k.title() for k in CLASSES}
POINT='/ShooterCore/Blueprint/B_ControlPointVolume.B_ControlPointVolume_C'
SPAWNER='/ShooterCore/Blueprint/B_WeaponSpawner.B_WeaponSpawner_C'
ABILITY='/ShooterCore/Blueprint/B_AbilitySpawner.B_AbilitySpawner_C'


def evidence(a):
    if not hasattr(a,'_uep_shooter_eqs'):a._uep_shooter_eqs={p+'_'+k:0 for p in ('python','fallback') for k in GATES};a._uep_shooter_eqs['diagnostic_fallbacks']=0
    return a._uep_shooter_eqs
def mark(a,k):evidence(a)['python_'+k]+=1
def actors(a,cls):return list(one(lib('GameplayStatics').call_function('GetAllActorsOfClass',a,cls)))
def teams(a):return lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',a,ue.find_class('LyraTeamSubsystem'))
def points(a,querier):
    mark(a,'points');system=teams(a);value=native_outputs('LyraTeamSubsystem','FindTeamFromActor',system.call_function('FindTeamFromActor',querier));team=int(value['TeamId']);result=[p for p in actors(a,ue.load_class(POINT)) if int(p.get_property('OwnerTeamID'))!=team];return dict(UseOriginal=False,Actors=result)
def enemy(a,querier):
    mark(a,'enemy');controller=lib('AIBlueprintHelperLibrary').call_function('GetAIController',querier);board=lib('AIBlueprintHelperLibrary').call_function('GetBlackboard',controller)
    if not valid(board):evidence(a)['diagnostic_fallbacks']+=1;return dict(UseOriginal=True,HasResult=False,Location=ue.FVector())
    target=board.call_function('GetValueAsObject',a.get_property('EnemyNameKey'));found=valid(target) and target.is_a(ue.find_class('Actor'));return dict(UseOriginal=False,HasResult=bool(found),Location=target.get_actor_location() if found else ue.FVector())
def weapon(a,querier):
    mark(a,'weapon');result=[]
    if not valid(querier) or not querier.is_a(ue.find_class('Pawn')):return dict(UseOriginal=False,Actors=result)
    controller=querier.call_function('GetController');manager=controller.get_component_by_type(ue.find_class('LyraInventoryManagerComponent')) if valid(controller) else None
    if not valid(manager):return dict(UseOriginal=False,Actors=result)
    ability=ue.load_class(ABILITY)
    for spawner in actors(a,ue.load_class(SPAWNER)):
        if not float(spawner.get_property('CoolDownPercentage'))<.1 or spawner.is_a(ability):continue
        definition=spawner.get_property('WeaponDefinition').get_property('InventoryItemDefinition');item=manager.call_function('FindFirstItemStackByDefinition',definition)
        if not valid(item):result.append(spawner);continue
        count=int(item.call_function('GetStatTagStackCount',GameplayTag(TagName=SPARE)));maximum=int(lib('LyraWeaponSpawner').call_function('GetDefaultStatFromItemDef',definition,GameplayTag(TagName=SPARE)))
        if count<maximum:result.append(spawner)
    return dict(UseOriginal=False,Actors=result)
def enemies(a):
    mark(a,'enemies');candidates=actors(a,ue.find_class('LyraCharacter'));querier=a.call_function('GetQuerier')
    if not valid(querier) or not querier.is_a(ue.find_class('LyraCharacter')):return False
    system=teams(a)
    for actor in candidates:
        comparison=system.call_function('CompareTeams',actor,querier)
        if int(comparison[0])==1 and not actor.get_property('HealthComponent').call_function('IsDeadOrDying'):a.call_function('AddGeneratedActor',actor)
    return False


class LyraShooterEQSPointsPythonProfile:
    def Points(self,QuerierActor):return points(self,QuerierActor)
    Points.override=GATES['points'];Points.uep_named_outputs=True
class LyraShooterEQSEnemyPythonProfile:
    def Enemy(self,QuerierActor):return enemy(self,QuerierActor)
    Enemy.override=GATES['enemy'];Enemy.uep_named_outputs=True
class LyraShooterEQSWeaponPythonProfile:
    def Weapon(self,QuerierActor):return weapon(self,QuerierActor)
    Weapon.override=GATES['weapon'];Weapon.uep_named_outputs=True
class LyraShooterEQSEnemiesPythonProfile:
    def Enemies(self):return enemies(self)
    Enemies.override=GATES['enemies']


def fallback(k,output):
    def invoke(self,*args):
        evidence(self)['fallback_'+k]+=1
        if output is None:return True
        if output=='Location':return dict(UseOriginal=True,HasResult=False,Location=ue.FVector())
        return dict(UseOriginal=True,**{output:[]})
    invoke.override=GATES[k]
    if output:invoke.uep_named_outputs=True
    return invoke
class LyraShooterEQSPointsBlueprintFallbackProfile:Points=fallback('points','Actors')
class LyraShooterEQSEnemyBlueprintFallbackProfile:Enemy=fallback('enemy','Location')
class LyraShooterEQSWeaponBlueprintFallbackProfile:Weapon=fallback('weapon','Actors')
class LyraShooterEQSEnemiesBlueprintFallbackProfile:Enemies=fallback('enemies',None)
