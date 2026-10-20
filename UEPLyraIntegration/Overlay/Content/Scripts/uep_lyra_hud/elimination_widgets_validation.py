"""Native list assignment/delegate/expiry plus original material/icon helpers."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,Vector2D
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import elimination_widgets_mixin as policy
from . import elimination_feed_relay_mixin as relay
from .elimination_feed_relay_contract import FIELDS
from .elimination_widgets_contract import PROFILES,require,validate


def tag(s):return GameplayTag(TagName=s)
def one(v):return v[0] if isinstance(v,tuple) and len(v)==1 else v
def container(names):return GameplayTagContainer(GameplayTags=[tag(n) for n in names])
def count(w,n):return sum(policy.evidence(w)[p+'_'+n] for p in ('python','fallback'))


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.widgets=[];self.sources={};self.index=0;self.assignments=[];self.expiries=[]
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_or_list_subscription_replaced','timer_callbacks_replayed','list_item_callbacks_replayed','localized_text_roundtripped','health_properties_written','split_screen_filter_added'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(policy.CLASSES[k]) for k in ('feed','entry')};self.cdo_profiles={k:c.get_cdo().get_property('PythonMixinProfile') for k,c in self.classes.items()}
        for k,c in self.classes.items():
            ue.register_declared_mixin(c);row,=[r for r in ue.get_registered_mixins() if r['target_class']==c];self.sources[k]={p:r['python_class'] for p,r in row['profiles'].items()}
        for p,base in self.sources['entry'].items():
            def around(fn,key):
                def invoke(w,*args):
                    item=one(policy.lib('UserObjectListEntryLibrary').call_function('GetListItemObject',w))
                    if item is not None and self.feed is not None and item.get_outer()==self.feed:
                        (self.assignments if key=='assign' else self.expiries).append(dict(widget=w,item=item,time=self.game_time()))
                    return fn(w,*args)
                invoke.override=getattr(fn,'override');return invoke
            ue.register_mixin_profile(self.classes['entry'],p,type('ObservedEliminationEntry'+p,(),dict(Colors=base.Colors,Text=base.Text,Assign=around(base.Assign,'assign'),Expire=around(base.Expire,'expire'))))
        self.feed=None;cls=ue.load_class(relay.CLASS);self.sender=next(c for c in ue.tobject_iterator(cls) if c.get_world()==self.world and c.call_function('GetOwner') is not None);self.start_profile()
    def create(self,k):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[k],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);w.call_function('SetDesiredSizeInViewport',Vector2D(X=750.,Y=400.));w.call_function('AddToPlayerScreen',0);return w
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for cls in self.classes.values():cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.feed=self.create('feed');self.view=self.feed.get_property('ToastListWidget');self.style=self.create('entry');self.row=dict(profile=self.profile,style_cases=[],icon_cases=[],initial_collapsed=int(self.feed.get_property('FeedVisibilityOvr').call_function('GetVisibility'))==1);self.report['pending_profile']=self.row;self.styles();self.names();self.assignments=[];self.expiries=[];self.enter('populate');self.send('First-A','First-B',1,2,['GameplayEffect.DamageType.Rifle']);self.send('Second-A','Second-B',2,1,['GameplayEffect.DamageType.Pistol'])
    def styles(self):
        for attacker,attackee in ((0,2),(1,1),(2,0)):
            w=self.style;w.set_property('AttackerTeamId',attacker);w.set_property('AttackeeTeamId',attackee);w.call_function('SetTeamColors');values=[];expected=[]
            for field,method,team in [('AttackerName','GetDynamicFontMaterial',attacker),('AttackerGlow','GetDynamicMaterial',attacker)]+[(n,'GetDynamicMaterial',attacker) for n in (*policy.ICONS,'WeaponGlow')]+[('AttackeeName','GetDynamicFontMaterial',attackee),('AttackeeGlow','GetDynamicMaterial',attackee)]:
                material=w.get_property(field).call_function(method);values.append(float(material.call_function('K2_GetScalarParameterValue','Animate_ActiveToInactive')));expected.append(float(team==1))
            self.row['style_cases'].append(dict(attacker=attacker,attackee=attackee,values=values,native_material_values_match=all(abs(a-b)<.0001 for a,b in zip(values,expected))))
    def names(self):
        cases=[([], 'SelfElimination')]+[(['GameplayEffect.DamageType.'+n],n) for n in policy.ICONS[:-1]]+[(['GameplayEffect.DamageType.Pistol','GameplayEffect.DamageType.Rifle'],'Pistol'),(['GameplayEffect.DamageType.Shotgun','GameplayEffect.DamageType.Grenade'],'Shotgun'),(['Gameplay.Damage.SelfDestruct'],'SelfElimination')]
        text=policy.lib('KismetTextLibrary');a=text.call_function('Conv_StringToText','Attacker-甲');b=text.call_function('Conv_StringToText','Attackee-乙')
        for names,icon in cases:
            self.style.call_function('SetWeaponIconAndNameText',a,b,container(names));self.row['icon_cases'].append(dict(tags=names,icon=icon,native_text_matches=bool(text.call_function('EqualEqual_TextText',a,self.style.get_property('AttackerName').call_function('GetText'))) and bool(text.call_function('EqualEqual_TextText',b,self.style.get_property('AttackeeName').call_function('GetText'))),native_icon_matches=self.style.get_property('WeaponIconSwitcher').call_function('GetActiveWidget')==self.style.get_property(icon)))
    def send(self,a,b,attacker,attackee,names):
        text=policy.lib('KismetTextLibrary');self.sender.call_function(relay.BROADCAST,text.call_function('Conv_StringToText',a),text.call_function('Conv_StringToText',b),attacker,attackee,container(names))
    def items(self):return list(one(self.view.call_function('GetListItems')))
    def entries(self):return list(one(self.view.call_function('GetDisplayedEntryWidgets')))
    def observe(self):
        require(time.monotonic()-self.phase_started<20.,'native elimination UI phase timeout: '+self.phase)
        if self.phase=='populate':
            if len(self.items())!=2 or len(self.assignments)<2:return
            self.row['two_items_visible']=int(self.feed.get_property('FeedVisibilityOvr').call_function('GetVisibility'))==0;self.row['items_outer_matches_feed']=all(item.get_outer()==self.feed for item in self.items());matches=True;active=True
            for item,w in [(one(policy.lib('UserObjectListEntryLibrary').call_function('GetListItemObject',w)),w) for w in self.entries()]:
                payload=item.get_property('Message');matches &= int(w.get_property('AttackerTeamId'))==int(getattr(payload,FIELDS['AttackerTeamID'])) and int(w.get_property('AttackeeTeamId'))==int(getattr(payload,FIELDS['AttackeeTeamID']));matches &= bool(policy.lib('KismetTextLibrary').call_function('EqualEqual_TextText',w.get_property('AttackerName').call_function('GetText'),getattr(payload,FIELDS['Attacker'])));active &= bool(w.call_function('IsAnimationPlaying',w.get_property('IntroWithTimedOutro')))
            self.row['all_native_entry_fields_match']=matches;self.row['animation_started']=active;self.enter('expiry')
        elif self.phase=='expiry':
            if self.items() or len(self.expiries)<2:return
            durations=[e['time']-max(a['time'] for a in self.assignments if a['widget']==e['widget'] and a['item']==e['item'] and a['time']<=e['time']) for e in self.expiries];self.row.update(expiry_entries=len(self.expiries),removed_entries=count(self.feed,'remove'),collapsed_after_expiry=int(self.feed.get_property('FeedVisibilityOvr').call_function('GetVisibility'))==1,native_expiry_durations_match=all(5.95<=d<=6.4 for d in durations),native_expiry_durations=durations,native_assignments_including_list_refresh=len(self.assignments))
            self.feed.call_function('RemoveFromParent');self.assignments=[];self.expiries=[];self.send('Offscreen','Queued',0,1,[]);self.enter('offscreen')
        elif self.phase=='offscreen':
            if time.monotonic()-self.phase_started<.2:return
            self.row['removed_widget_still_received_native_message']=len(self.items())==1;self.feed.call_function('AddToPlayerScreen',0);self.enter('remount')
        elif self.phase=='remount':
            if len(self.assignments)<1:return
            self.row['remount_has_one_entry']=len(self.items())==1;self.row['remount_single_listener_entry']=count(self.feed,'message')==3;self.enter('remount-expiry')
        elif self.phase=='remount-expiry':
            if self.items() or not self.expiries:return
            self.row['remount_expired']=len(self.expiries)==1;self.row['diagnostic_fallbacks']=policy.evidence(self.feed)['diagnostic_fallbacks']+policy.evidence(self.style)['diagnostic_fallbacks']+sum(policy.evidence(a['widget'])['diagnostic_fallbacks'] for a in self.assignments);self.report['profiles'].append(self.row);self.feed.call_function('RemoveFromParent');self.style.call_function('RemoveFromParent');ue.clear_mixin_profile(self.feed);ue.clear_mixin_profile(self.style);self.feed=None;self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for k,profiles in self.sources.items():
            for p,base in profiles.items():ue.register_mixin_profile(self.classes[k],p,base)
            self.classes[k].get_cdo().set_property('PythonMixinProfile',self.cdo_profiles[k])
        self.report.update(widget_roots_removed=bool(self.widgets) and all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),original_cdo_profiles_restored=all(c.get_cdo().get_property('PythonMixinProfile')==self.cdo_profiles[k] for k,c in self.classes.items()),production_profile_families_restored=all(any(r['target_class']==self.classes[k] and all(r['profiles'][p]['python_class'] is base for p,base in profiles.items()) for r in ue.get_registered_mixins()) for k,profiles in self.sources.items()),original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native elimination UI total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ELIMINATION_WIDGETS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ELIMINATION_WIDGETS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPEliminationWidgetsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
