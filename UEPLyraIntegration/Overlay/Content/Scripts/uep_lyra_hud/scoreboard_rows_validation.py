"""Genuine Blueprint-parent/interface calls and original one-second timer flow."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.scoring_base_validation import Validation as Fixtures
from uep_lyra_weapons.hero_burst_cue_validation import dead
from . import scoreboard_rows_mixin as policy
from .scoreboard_rows_contract import PROFILES,require,validate

TAG='ShooterGame.Score.Eliminations'


def color(c):return [float(getattr(c,n)) for n in ('r','g','b','a')]
def close(a,b):return all(abs(x-y)<.00001 for x,y in zip(a,b))
def text(w):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',w.call_function('GetText'))
def tint(w):return color(w.get_property('ColorAndOpacity').SpecifiedColor)


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.widgets=[];self.index=0
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','health_properties_written','new_native_timer_cleanup_added'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.cdo_profiles={k:c.get_cdo().get_property('PythonMixinProfile') for k,c in self.classes.items()}
        for c in self.classes.values():ue.register_declared_mixin(c)
        self.team_ids=[1,2];self.units=[self.unit(i) for i in (0,1)]
        for u,n in zip(self.units,('Score-甲','Score-乙')):u['state'].set_property('PlayerNamePrivate',n)
        self.start_profile()
    def create(self,key):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[key],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile);w.call_function('AddToPlayerScreen',0);return w
    def set_value(self,ps,value):
        current=int(ps.call_function('GetStatTagStackCount',GameplayTag(TagName=TAG)))
        if current:ps.call_function('RemoveStatTagStack',GameplayTag(TagName=TAG),current)
        if value:ps.call_function('AddStatTagStack',GameplayTag(TagName=TAG),value)
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.classes.values():c.get_cdo().set_property('PythonMixinProfile',self.profile)
        a,b=[u['state'] for u in self.units];self.set_value(a,0);self.set_value(b,0);row=dict(profile=self.profile,mode_rows=[]);self.report['pending_profile']=row;self.row=row
        base=self.create('base');base.call_function('SetPlayerState',a);row['base_association']=base.get_property('AssociatedPlayerState')==a
        icon=self.create('icon');icon.call_function('SetPlayerState',a);row['icon_association']=icon.get_property('Player State')==a
        name=self.create('name');checks=[]
        for ps in (a,b):name.call_function('SetPlayerState',ps);checks.append(text(name.get_property('PlayerNameWidget'))==ps.call_function('GetPlayerName') and close(tint(name.get_property('PlayerNameWidget')),color(policy.color(int(ps.call_function('GetTeamId'))))))
        row['name_team_colors_match']=all(checks);name.call_function('SetAsLocalPlayer');row['local_name_white']=close(tint(name.get_property('PlayerNameWidget')),[1,1,1,1])
        self.set_value(a,1234)
        for key in ('cp','tdm'):
            w=self.create(key);w.call_function('SetPlayerState',a);children=list(policy.one(w.call_function('GetPlayerStateAwareChildren')));expected=list(policy.one(w.get_property('MyHorizontalBox').call_function('GetAllChildren')));associated=[]
            for child in children:
                if policy.lib('KismetSystemLibrary').call_function('DoesImplementInterface',child,ue.load_class(policy.INTERFACE)):
                    props=child.properties();associated.append(child.get_property('AssociatedPlayerState' if 'AssociatedPlayerState' in props else 'Player State')==a)
            colors=[]
            for team in (1,2):
                w.set_property('TeamId',team)
                for odd in (False,True):
                    w.call_function('SetRowColor',odd);actual=color(w.get_property('EntryBorder').get_property('BrushColor'));expected_color={1:(.107023,.014444,.011612,.3) if odd else (.036889,.005182,.005605,.3),2:(.006995,.068478,.107023,.3) if odd else (.003035,.021219,.040915,.3)}[team];colors.append(close(actual,expected_color))
            target=name.get_property('PlayerNameWidget');w.call_function('UpdateIndividualScoreWidget',target,GameplayTag(TagName=TAG));grouped=text(target)=='1,234';w.call_function('SetPlayerState',self.controller.PlayerState);white=close(tint(w.get_property('PlayerName').get_property('PlayerNameWidget')),[1,1,1,1])
            row['mode_rows'].append(dict(kind=key,children_from_native_panel=children==expected,child_association_fanout=bool(associated) and all(associated),team_and_local_marker_match=white and int(w.get_property('TeamId'))==int(self.controller.PlayerState.call_function('GetTeamId')),all_row_colors_match=all(colors),native_grouped_individual_score_match=grouped))
        self.stat=self.create('stat');self.stat.set_property('Stat Tag',GameplayTag(TagName=TAG));box=self.stat.get_property('ForcedWidthSB');row['native_construct_width']=abs(float(box.get_property('WidthOverride'))-float(self.stat.get_property('StatWidth')))<.0001
        self.stat.set_property('StatWidth',145.);self.stat.call_function('PreConstruct',False);row['positive_preconstruct_width']=abs(float(box.get_property('WidthOverride'))-145.)<.0001;self.stat.set_property('StatWidth',-12.);self.stat.call_function('PreConstruct',True);row['nonpositive_preconstruct_retains_width']=abs(float(box.get_property('WidthOverride'))-145.)<.0001
        self.set_value(a,0);self.stat.call_function('SetPlayerState',a);self.control=self.stat.get_property('StatTextWidget');row['zero_stat_tinted']=text(self.control)=='0' and close(tint(self.control),color(policy.color(1,.4)));self.change_time=self.game_time();self.set_value(a,1234);self.enter('native-timer')
    def observe(self):
        require(time.monotonic()-self.phase_started<8.,'native scoreboard timer timeout: '+self.phase)
        a,b=[u['state'] for u in self.units]
        if self.phase=='native-timer':
            if text(self.control)!='1,234':return
            self.row.update(native_timer_updated_grouped_stat=True,positive_stat_white=close(tint(self.control),[1,1,1,1]),native_update_elapsed_seconds=self.game_time()-self.change_time)
            self.stat.call_function('SetPlayerState',b);self.row['rebinding_updates_immediately']=text(self.control)=='0' and close(tint(self.control),color(policy.color(2,.4)));previous=text(self.control);self.stat.call_function('SetPlayerState',None);self.row['null_association_preserves_text']=text(self.control)==previous
            self.stat.call_function('SetPlayerState',b);self.stat.call_function('RemoveFromParent');self.set_value(b,9);self.enter('removed-rooted')
        elif self.phase=='removed-rooted':
            if text(self.control)!='9':return
            self.row['removed_rooted_stat_timer_still_updates']=True;self.row['diagnostic_fallbacks']=sum(policy.evidence(w)['diagnostic_fallbacks'] for w in self.widgets);self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for key,c in self.classes.items():c.get_cdo().set_property('PythonMixinProfile',self.cdo_profiles[key])
        policy.lib('KismetSystemLibrary').call_function('CollectGarbage')
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        self.report.update(widget_roots_removed=bool(self.widgets) and all(not w.is_rooted() if w.is_valid() else True for w in self.widgets),cdo_profiles_restored=all(c.get_cdo().get_property('PythonMixinProfile')==self.cdo_profiles[k] for k,c in self.classes.items()),profile_families_restored=all(any(r['target_class']==c for r in ue.get_registered_mixins()) for c in self.classes.values()),owned_actors_destroyed=all(dead(a) for a in self.actors),original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native scoreboard row timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SCOREBOARD_ROWS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SCOREBOARD_ROWS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPScoreboardRowsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
