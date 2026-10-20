"""Native GameState roster + dynamic entry pool + original one-second clocks."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.scoring_base_validation import Validation as Fixtures
from uep_lyra_weapons.hero_burst_cue_validation import dead
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import scoreboard_list_mixin as policy
from .scoreboard_list_contract import PROFILES,require,validate

TAG='ShooterGame.Score.Eliminations'


def path(o):return o.get_path_name() if policy.valid(o) else None
def paths(values):return [path(v) for v in values]
def count(w,n):return sum(policy.evidence(w)[p+'_'+n] for p in ('python','fallback'))


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.widgets=[];self.index=0
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','native_timer_replaced','timer_callbacks_replayed','localized_format_roundtripped','health_properties_written','native_roster_array_written'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.state=self.statics.call_function('GetGameState',self.world);self.team=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'));self.team_ids=[1,2,1];self.units=[self.unit(i) for i in (0,1)];self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        self.row_classes=[ue.load_class('/ShooterCore/'+folder+'/UI/'+n+'.'+n+'_C') for folder,n in (('ControlPoint','W_SB_PlayerRow_CP'),('Elimination','W_SB_PlayerRow_TDM'))];self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in [*self.classes.values(),*self.row_classes]}
        for c in self.classes.values():ue.register_declared_mixin(c)
        for u in self.units:u['state'].call_function('AddStatTagStack',GameplayTag(TagName=TAG),5)
        self.start_profile()
    def create(self,key,filter_value=1):
        w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes[key],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,self.profile)
        if key=='list':w.set_property('PlayerRowClass',self.row_classes[1]);w.set_property('TeamIdFilter',filter_value)
        w.call_function('AddToPlayerScreen',0);return w
    def members(self,w):return list(w.get_property('PlayerStates'))
    def native_expected(self,team):
        result=[]
        for ps in self.state.get_property('PlayerArray'):
            if not policy.valid(ps) or not ps.is_a(ue.find_class('LyraPlayerState')):continue
            found=native_outputs('LyraTeamSubsystem','FindTeamFromActor',self.team.call_function('FindTeamFromActor',ps))
            if team==-1 or found['bIsPartOfTeam'] and int(found['TeamId'])==team:result.append(ps)
        return result
    def rank(self,w):return sorted(self.members(w),key=lambda ps:-int(ps.call_function('GetStatTagStackCount',GameplayTag(TagName=TAG))))
    def entries(self,w):return list(policy.one(w.get_property('PlayerList').call_function('GetAllEntries')))
    def entry_states(self,w):return [e.get_property('AssociatedPlayerState') for e in self.entries(w)]
    def start_profile(self):
        self.profile=PROFILES[self.index]
        for c in self.cdos:c.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.row=dict(profile=self.profile);self.report['pending_profile']=self.row;self.unfiltered=self.create('list',-1);self.row['unfiltered_accepts_null']=bool(policy.one(self.unfiltered.call_function('PassesFilter',None)));self.no_timer_before=count(self.unfiltered,'poll');self.list=self.create('list',1)
        a,b=[u['state'] for u in self.units];self.row['team_filter_matches_native']=bool(policy.one(self.list.call_function('PassesFilter',a))) and not policy.one(self.list.call_function('PassesFilter',b)) and not policy.one(self.list.call_function('PassesFilter',None));self.row['initial_membership_matches']=paths(self.members(self.list))==paths(self.native_expected(1));self.row['initial_rank_matches']=paths(self.entry_states(self.list))==paths(self.rank(self.list));self.row['ties_keep_membership_order']=True;self.row['pooled_rows_match_sorted_states']=self.row['initial_rank_matches']
        self.connection=self.create('connection');self.connection.call_function('SetPlayerState',a);self.control=self.connection.get_property('ConnectionStatus');self.cached_color=self.control.get_property('DefaultTextStyleOverride').ColorAndOpacity.SpecifiedColor;self.row['native_ping_text_format_matches']=self.expected_ping(a);self.ping_before=count(self.connection,'update');self.poll_before=count(self.list,'poll');self.change_time=self.game_time();self.extra=self.unit(2);self.extra['state'].call_function('AddStatTagStack',GameplayTag(TagName=TAG),5);self.enter('native-add')
    def expected_ping(self,ps):
        number=policy.lib('KismetMathLibrary').call_function('Round',ps.call_function('GetPingInMilliseconds'));text=policy.lib('KismetTextLibrary').call_function('Conv_TextToString',self.control.call_function('GetText'));return text=='<text color="FFFFFFFF">'+str(number)+'</> ms'
    def observe(self):
        require(time.monotonic()-self.phase_started<9.,'native scoreboard-list phase timeout: '+self.phase)
        if self.phase=='native-add':
            if self.extra['state'] not in self.members(self.list) or count(self.list,'poll')==self.poll_before:return
            self.row['native_timer_added_new_player']=True;self.row['native_poll_elapsed_seconds']=self.game_time()-self.change_time;self.row['ties_keep_membership_order']=paths(self.entry_states(self.list))==paths(self.rank(self.list));self.row['pooled_rows_match_sorted_states'] &= self.row['ties_keep_membership_order'];self.row['native_ping_timer_updates']=count(self.connection,'update')>self.ping_before;self.row['unfiltered_has_no_native_periodic_update']=count(self.unfiltered,'poll')==self.no_timer_before
            self.list.set_property('TeamIdFilter',2);self.enter('native-filter')
        elif self.phase=='native-filter':
            expected=self.native_expected(2)
            if paths(self.members(self.list))!=paths(expected):return
            self.row['native_timer_changed_filter']=True;self.list.set_property('TeamIdFilter',1);self.enter('return-filter')
        elif self.phase=='return-filter':
            if self.extra['state'] not in self.members(self.list):return
            for k in ('pawn','controller','state'):
                if not dead(self.extra[k]):self.extra[k].actor_destroy()
            self.enter('native-remove')
        elif self.phase=='native-remove':
            if any(not policy.valid(ps) for ps in self.members(self.list)) or paths(self.members(self.list))!=paths(self.native_expected(1)):return
            self.row['native_timer_removed_destroyed_player']=True;self.connection.call_function('RemoveFromParent');self.ping_before=count(self.connection,'update');self.enter('removed-rooted')
        elif self.phase=='removed-rooted':
            if count(self.connection,'update')<=self.ping_before:return
            self.row['removed_rooted_timer_updates']=True;now=self.control.get_property('DefaultTextStyleOverride').ColorAndOpacity.SpecifiedColor;self.row['ping_color_cached_at_association']=all(abs(float(getattr(now,k))-float(getattr(self.cached_color,k)))<.00001 for k in ('r','g','b','a'));self.row['diagnostic_fallbacks']=sum(policy.evidence(w)['diagnostic_fallbacks'] for w in (self.list,self.unfiltered,self.connection));self.report['profiles'].append(self.row);self.index+=1
            if self.index<len(PROFILES):self.start_profile()
            else:self.finish()
    def cleanup(self):
        for w in self.widgets:ue.clear_mixin_profile(w);w.call_function('RemoveFromParent');w.remove_from_root()
        for c,profile in self.cdos.items():c.get_cdo().set_property('PythonMixinProfile',profile)
        policy.lib('KismetSystemLibrary').call_function('CollectGarbage')
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        self.report.update(widget_roots_removed=bool(self.widgets) and all(not w.is_rooted() if w.is_valid() else True for w in self.widgets),profile_selectors_restored=all(c.get_cdo().get_property('PythonMixinProfile')==profile for c,profile in self.cdos.items()),owned_actors_destroyed=all(dead(a) for a in self.actors),original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native scoreboard list total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SCOREBOARD_LIST_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SCOREBOARD_LIST_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPScoreboardListResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
