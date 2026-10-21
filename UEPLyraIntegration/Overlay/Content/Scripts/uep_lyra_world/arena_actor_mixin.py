"""Arena avatar, death and pickup intent; original parents/tasks/delegates remain."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEffectContextHandle
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid
HERO='/TopDownArena/Game/B_Hero_Arena.B_Hero_Arena_C'
DEATH='/TopDownArena/Game/GA_ArenaHero_Death.GA_ArenaHero_Death_C'
PICKUP='/TopDownArena/Game/Pickups/B_TopDownArena_Pickup.B_TopDownArena_Pickup_C'
SELECTOR='UEPArenaHeroMixinProfile'
TEAM='On Team or Cosmetics Changed'
TEAM_EVENT='OnTeamChanged_BE127F834A7CBFE12C02FD836BDABEA2'
PARTS_EVENT='BndEvt__B_Hero_Arena_B_MannequinPawnCosmetics_K2Node_ComponentBoundEvent_4_LyraSpawnedCharacterPartsChanged__DelegateSignature'
HERO_BEGIN='UEPArenaHeroAfterParentBegin'
HERO_SHOW='UEPArenaHeroAfterNativeShowWait'
TEAM_BIND='UEPBindArenaHeroTeam'
REGISTER='UEPArenaRegisterVisibilityReady'
DEATH_WAIT='UEPArenaDeathNativeWait'
DEATH_BEGIN='UEPArenaDeathActivate'
DEATH_AFTER='UEPArenaDeathAfterNativeWait'
PICKUP_OVERLAP='UEPArenaPickupOverlap'
UNARMED='/Game/Characters/Heroes/Mannequin/Animations/Locomotion/Unarmed/ABP_UnarmedAnimLayers.ABP_UnarmedAnimLayers_C'
def lib(n):return ue.find_class(n).get_cdo()
def evidence(a):
    value=getattr(a,'_uep_arena_actor',None)
    if value is None:
        value={p+k:0 for p in ('python_','fallback_') for k in ('begin','listen','team','display','parts','show','death','finish','change','rep','overlap')};value.update(applies=0,cues=0,waits=0,ends=0,assets=0,consumptions=0);a._uep_arena_actor=value
    return value
class LyraArenaHeroPythonProfile:
    def AfterParentBegin(self):
        evidence(self)['python_begin']+=1;self.call_function('ListenForTeam');self.call_function('SetActorHiddenInGame',True);self.call_function(REGISTER,self.get_property('PawnExtComponent'),GameplayTag(TagName='InitState.GameplayReady'),True);return False
    AfterParentBegin.override=HERO_BEGIN
    def ListenForTeam(self):
        evidence(self)['python_listen']+=1;action=lib('AsyncAction_ObserveTeamColors').call_function('ObserveTeamColors',self)
        if valid(action):self.call_function(TEAM_BIND,action);action.call_function('Activate')
    def ObservedTeam(self,bTeamSet:bool,TeamId:int,DisplayAsset):
        evidence(self)['python_team']+=1
        if bTeamSet:self.call_function(TEAM,TeamId,DisplayAsset)
    ObservedTeam.override=TEAM_EVENT
    def Display(self,TeamId:int,TeamDisplayAsset):
        value=evidence(self);value['python_display']+=1
        if valid(TeamDisplayAsset):TeamDisplayAsset.call_function('ApplyToActor',self,True);value['applies']+=1
    Display.override=TEAM
    def Parts(self,ComponentWithChangedParts):
        evidence(self)['python_parts']+=1;self.get_property('Mesh').call_function('LinkAnimClassLayers',ue.load_class(UNARMED));result=native_outputs('LyraTeamStatics','FindTeamFromObject',lib('LyraTeamStatics').call_function('FindTeamFromObject',self,False))
        if result['bIsPartOfTeam']:self.call_function(TEAM,result['TeamId'],result['DisplayAsset'])
    Parts.override=PARTS_EVENT
    def Show(self):evidence(self)['python_show']+=1;self.call_function('SetActorHiddenInGame',False);return False
    Show.override=HERO_SHOW
class LyraArenaDeathPythonProfile:
    def Activate(self):
        value=evidence(self);value['python_death']+=1;self.call_function('K2_ExecuteGameplayCue',GameplayTag(TagName='GameplayCue.Character.Death'),GameplayEffectContextHandle());value['cues']+=1;self.call_function(DEATH_WAIT);value['waits']+=1;return False
    Activate.override=DEATH_BEGIN
    def AfterWait(self):
        value=evidence(self);value['python_finish']+=1;value['ends']+=1;self.call_function('K2_EndAbility');return False
    AfterWait.override=DEATH_AFTER
def pickup_vfx(a,rep):
    value=evidence(a);value['python_rep' if rep else 'python_change']+=1;data=lib('AbilitySystemBlueprintLibrary').call_function('GetGameplayEffectUIData',a.get_property('GameplayEffectToApply'),ue.find_class('TopDownArenaPickupUIData'))
    if not valid(data):return
    fx=data.get_property('PickupVFX')
    if valid(fx) and bool(a.call_function('HasAuthority'))!=bool(rep):a.get_property('VFX').call_function('SetAsset',fx,True);value['assets']+=1
class LyraArenaPickupPythonProfile:
    def ChangePickupEffect(self):pickup_vfx(self,False)
    def OnRep_GameplayEffectToApply(self):pickup_vfx(self,True)
    def Overlap(self,OtherActor):
        value=evidence(self);value['python_overlap']+=1;asc=lib('AbilitySystemBlueprintLibrary').call_function('GetAbilitySystemComponent',OtherActor)
        if valid(asc) and self.call_function('HasAuthority'):asc.call_function('BP_ApplyGameplayEffectToSelf',self.get_property('GameplayEffectToApply'),0.,GameplayEffectContextHandle());value['consumptions']+=1;self.call_function('K2_DestroyActor')
        return False
    Overlap.override=PICKUP_OVERLAP
def forward(method,key):
    def call(a,*args):evidence(a)['fallback_'+key]+=1;return a.call_mixin_original(method,*args)
    call.override=method;return call
def gate(name,key):
    def call(a,*args):evidence(a)['fallback_'+key]+=1;return True
    call.override=name;return call
class LyraArenaHeroBlueprintFallbackProfile:
    AfterParentBegin=gate(HERO_BEGIN,'begin');ListenForTeam=forward('ListenForTeam','listen');ObservedTeam=forward(TEAM_EVENT,'team');Display=forward(TEAM,'display');Parts=forward(PARTS_EVENT,'parts');Show=gate(HERO_SHOW,'show')
class LyraArenaDeathBlueprintFallbackProfile:
    Activate=gate(DEATH_BEGIN,'death');AfterWait=gate(DEATH_AFTER,'finish')
class LyraArenaPickupBlueprintFallbackProfile:
    ChangePickupEffect=forward('ChangePickupEffect','change');OnRep_GameplayEffectToApply=forward('OnRep_GameplayEffectToApply','rep');Overlap=gate(PICKUP_OVERLAP,'overlap')
