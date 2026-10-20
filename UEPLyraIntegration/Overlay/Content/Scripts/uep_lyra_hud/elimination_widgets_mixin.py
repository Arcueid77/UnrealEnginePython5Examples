"""Feed/item presentation with native subscription, list delegates and 6s clock."""
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import ESlateVisibility,EUMGSequencePlayMode
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from .elimination_feed_relay_contract import FIELDS

BASE='/ShooterCore/UserInterface/Notifications/EliminationFeed/'
CLASSES={k:BASE+n+'.'+n+'_C' for k,n in (('feed','W_EliminationFeed'),('entry','W_EliminationFeedEntryWidget'),('item','ElimFeedEntry'))}
GATES=dict(message='UEPElimFeedMessage',remove='UEPElimFeedRemove',visibility='UEPElimFeedVisibility',colors='UEPElimEntryColors',text='UEPElimEntryText',assign='UEPElimEntryAssign',expire='UEPElimEntryExpire')
START='UEPElimEntryStartNativeTimer';EMIT='UEPElimEntryEmitExpired'
ICONS=('Pistol','Rifle','Shotgun','Grenade','Melee','SelfElimination')


def evidence(w):
    if not hasattr(w,'_uep_elimination_widgets'):w._uep_elimination_widgets={p+'_'+n:0 for p in ('python','fallback') for n in GATES};w._uep_elimination_widgets.update(diagnostic_fallbacks=0)
    return w._uep_elimination_widgets
def mark(w,n):evidence(w)['python_'+n]+=1
def diagnostic(w):evidence(w)['diagnostic_fallbacks']+=1;return True


def visibility(w):
    mark(w,'visibility');view=w.get_property('ToastListWidget');overlay=w.get_property('FeedVisibilityOvr')
    if not valid(view) or not valid(overlay):return diagnostic(w)
    overlay.call_function('SetVisibility',ESlateVisibility.Visible if view.call_function('GetNumItems')>0 else ESlateVisibility.Collapsed);return False
def message(w,payload):
    mark(w,'message');view=w.get_property('ToastListWidget')
    if not valid(view):return diagnostic(w)
    item=ue.new_object(ue.load_class(CLASSES['item']),w);item.set_property('Message',payload);view.call_function('AddItem',item);w.call_function('UpdateDisplayVisibility');return False
def remove(w,item):
    mark(w,'remove');view=w.get_property('ToastListWidget')
    if not valid(view):return diagnostic(w)
    view.call_function('RemoveItem',item);w.call_function('UpdateDisplayVisibility');return False
def colors(w):
    mark(w,'colors');attacker=int(w.get_property('AttackerTeamId'));attackee=int(w.get_property('AttackeeTeamId'))
    if attacker not in (0,1,2) or attackee not in (0,1,2):return diagnostic(w)
    controls=[w.get_property(n) for n in ('AttackerName','AttackerGlow',*ICONS,'WeaponGlow','AttackeeName','AttackeeGlow')]
    if not all(valid(c) for c in controls):return diagnostic(w)
    # The BP expands multi-target setters: preserve getter/setter execution order.
    font=controls[0].call_function('GetDynamicFontMaterial');glow=controls[1].call_function('GetDynamicMaterial')
    for material in (glow,font):material.call_function('SetScalarParameterValue','Animate_ActiveToInactive',float(attacker==1))
    materials={name:w.get_property(name).call_function('GetDynamicMaterial') for name in ('Shotgun','Rifle','Pistol','Grenade','Melee','SelfElimination','WeaponGlow')}
    for name in ('Grenade','Shotgun','Rifle','Pistol','WeaponGlow','Melee','SelfElimination'):materials[name].call_function('SetScalarParameterValue','Animate_ActiveToInactive',float(attacker==1))
    font=w.get_property('AttackeeName').call_function('GetDynamicFontMaterial');glow=w.get_property('AttackeeGlow').call_function('GetDynamicMaterial')
    for material in (glow,font):material.call_function('SetScalarParameterValue','Animate_ActiveToInactive',float(attackee==1))
    return False
def text(w,attacker,attackee,tags):
    mark(w,'text');controls={n:w.get_property(n) for n in ('AttackerName','AttackeeName','WeaponIconSwitcher',*ICONS)}
    if not all(valid(c) for c in controls.values()):return diagnostic(w)
    controls['AttackerName'].call_function('SetText',attacker);controls['AttackeeName'].call_function('SetText',attackee);selected='SelfElimination'
    for name in ICONS[:-1]:
        if lib('BlueprintGameplayTagLibrary').call_function('HasTag',tags,GameplayTag(TagName='GameplayEffect.DamageType.'+name),False):selected=name;break
    controls['WeaponIconSwitcher'].call_function('SetActiveWidget',controls[selected]);return False
def assign(w,item):
    mark(w,'assign');payload=item.get_property('Message');w.set_property('AttackerTeamId',int(getattr(payload,FIELDS['AttackerTeamID'])));w.set_property('AttackeeTeamId',int(getattr(payload,FIELDS['AttackeeTeamID'])));w.call_function('SetTeamColors');w.call_function('SetWeaponIconAndNameText',getattr(payload,FIELDS['Attacker']),getattr(payload,FIELDS['Attackee']),getattr(payload,FIELDS['InstigatorTags']));w.call_function('PlayAnimation',w.get_property('IntroWithTimedOutro'),0.,1,EUMGSequencePlayMode.Forward,1.,False);w.call_function(START);return False
def expire(w):
    mark(w,'expire');item=lib('UserObjectListEntryLibrary').call_function('GetListItemObject',w);w.call_function(EMIT,item);return False


class LyraEliminationListPythonProfile:
    def Message(self,Payload):return message(self,Payload)
    Message.override=GATES['message']
    def Remove(self,ItemPtr):return remove(self,ItemPtr)
    Remove.override=GATES['remove']
    def Visibility(self):return visibility(self)
    Visibility.override=GATES['visibility']
class LyraEliminationEntryPythonProfile:
    def Colors(self):return colors(self)
    Colors.override=GATES['colors']
    def Text(self,AttackerName,AttackeeName,InstigatorTags):return text(self,AttackerName,AttackeeName,InstigatorTags)
    Text.override=GATES['text']
    def Assign(self,Item):return assign(self,Item)
    Assign.override=GATES['assign']
    def Expire(self):return expire(self)
    Expire.override=GATES['expire']
def fallback(name):
    def invoke(self,*args):evidence(self)['fallback_'+name]+=1;return True
    invoke.override=GATES[name];return invoke
class LyraEliminationListBlueprintFallbackProfile:
    Message=fallback('message');Remove=fallback('remove');Visibility=fallback('visibility')
class LyraEliminationEntryBlueprintFallbackProfile:
    Colors=fallback('colors');Text=fallback('text');Assign=fallback('assign');Expire=fallback('expire')
