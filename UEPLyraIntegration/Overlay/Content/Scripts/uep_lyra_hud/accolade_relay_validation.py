"""Real partial accolade messages, native nullable notification fields and GC."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,LyraVerbMessage
from uep_runtime import SubscriptionScope
from uep_lyra_weapons.scoring_base_validation import Validation as ScoringFixtures
from uep_lyra_weapons.hero_burst_cue_validation import dead
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import accolade_relay_mixin as policy
from .accolade_relay_contract import PROFILES,require,validate


def path(o):return o.get_path_name() if valid(o) else None
def count(c):return sum(policy.evidence(c)[p+'_received'] for p in ('python','fallback'))
def tag(s):return GameplayTag(TagName=s)


class Validation(ScoringFixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,profiles=[]);self.scope=None;self.notifications=[]
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','callbacks_replayed','begin_play_replayed','production_subscription_replaced','native_relay_proxies_cancelled_by_fixture','health_properties_written'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.game=self.statics.call_function('GetGameInstance',self.world);self.state=self.statics.call_function('GetGameState',self.world);self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
        self.natural=[c for c in ue.tobject_iterator(self.cls) if valid(c) and valid(c.call_function('GetOwner')) and c.get_world()==self.world];self.report['natural_relays']=len(self.natural)
        self.real=self.state.get_component_by_type(ue.load_class('/ShooterCore/Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C'));require(valid(self.real),'actual TDM scoring absent');self.target_score=self.real.get_property('TargetScore');self.real.set_property('TargetScore',2000000000)
        self.team=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'));self.team_ids=sorted(native_outputs('LyraTeamSubsystem','GetTeamIDs',self.team.call_function('GetTeamIDs'))['ReturnValue']);self.units=[self.unit(i) for i in (0,1)]
        for u,name in zip(self.units,('Attacker-甲','Target-乙')):u['state'].set_property('PlayerNamePrivate',name)
        self.orphan=self.world.actor_spawn(ue.find_class('PlayerState'));self.actors.append(self.orphan);self.orphan.set_property('PlayerNamePrivate','Pawnless-丙');self.score_before=self.values()
        self.router=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.sender=ue.load_class('/Game/UEPValidation/BP_AccoladeRelayProbe.BP_AccoladeRelayProbe_C').get_cdo();self.sender_root=not self.sender.is_rooted()
        if self.sender_root:self.sender.add_to_root()
        self.scope=SubscriptionScope();struct=ue.find_struct('LyraNotificationMessage')
        self.scope.listen_gameplay_message(self.world,policy.CHANNEL,struct,self.read,self.on_feed);self.start_profile()
    def read(self,proxy):
        payload,success=self.sender.call_function('ReadNotification',proxy);require(success,'typed native feed extraction failed');return payload
    def on_feed(self,channel,payload):
        self.notifications.append(dict(player=path(payload.TargetPlayer),target_channel=str(payload.TargetChannel.TagName),payload_tag=str(payload.PayloadTag.TagName),text=policy.lib('KismetTextLibrary').call_function('Conv_TextToString',payload.PayloadMessage),object=path(payload.PayloadObject),channel=str(channel.TagName)))
    def start_profile(self):
        profile=PROFILES[self.index];before=set(self.all_proxies());self.current=ue.new_object(self.cls,self.state);self.components.append(self.current);ue.set_mixin_profile(self.current,profile);self.current.register_component();self.current.call_function('SetComponentTickEnabled',False)
        added=[p for name,p in self.all_proxies().items() if name not in before];self.proxies.extend(added);require(len(added)==1,'source accolade BeginPlay must create one native listener')
        self.row=dict(profile=profile,native_listener_proxies=1,cases=[]);self.report['pending_profile']=self.row
        foreign=self.world.actor_spawn(ue.find_class('Actor'));self.actors.append(foreign);a,b=[u['state'] for u in self.units];child=policy.ROOT+'.EliminationChain.2x';nested=policy.ROOT+'.EliminationStreak.10'
        cases=[('root-ps',policy.ROOT,child,a,a),('child-pawn',child,nested,self.units[0]['pawn'],a),('nested-controller',nested,policy.ROOT,self.units[1]['controller'],b),('plain-ps',policy.ROOT,child,self.orphan,self.orphan),('foreign',policy.ROOT,child,foreign,None),('null',policy.ROOT,child,None,None),('wrong-channel','Lyra.Assist.Message',child,a,a),('parent-channel','Lyra.ShooterGame',child,a,a)]
        for name,channel,verb,source,expected_player in cases:
            self.notifications=[];before=self.values();fixture_count=count(self.current);natural_count=sum(count(c) for c in self.natural)
            payload=LyraVerbMessage(Verb=tag(verb),Instigator=source,Target=b,InstigatorTags=GameplayTagContainer(GameplayTags=[tag('Gameplay.Damage.FellOutOfWorld')]),Magnitude=-17.25)
            expected=dict(player=path(expected_player),target_channel=policy.ROOT,payload_tag=verb,text='',object=None,channel=policy.CHANNEL)
            self.sender.call_function('BroadcastVerb',self.router,tag(channel),payload)
            self.row['cases'].append(dict(name=name,fixture_entries=count(self.current)-fixture_count,natural_entries=sum(count(c) for c in self.natural)-natural_count,notifications=list(self.notifications),expected=expected));self.restore_scores(before)
        e=policy.evidence(self.current);self.row.update(diagnostic_fallbacks=e['diagnostic_fallbacks'],python_client_requests=e['client_requests'],python_cosmetic_broadcasts=e['cosmetic_broadcasts'],python_player_helper_calls=e['player_helper_calls']);self.keys={path(p) for p in added};self.current.call_function('K2_DestroyComponent',self.state);policy.lib('KismetSystemLibrary').call_function('CollectGarbage');self.gc_frames=0;self.enter('relay-gc')
    def after_gc(self):
        self.gc_frames+=1
        if self.gc_frames<3:return
        before=self.values();self.sender.call_function('BroadcastVerb',self.router,tag(policy.ROOT),LyraVerbMessage(Verb=tag(policy.ROOT),Instigator=self.units[0]['state'],Target=self.units[1]['state']));self.restore_scores(before)
        self.row.update(relay_proxy_gi_released_after_gc_and_message=not self.keys.intersection(self.gi()),engine_gc_frames=self.gc_frames);self.report['profiles'].append(self.row);self.index+=1
        if self.index<len(PROFILES):self.start_profile()
        else:self.finish()
    def cleanup(self):
        for c in self.components:
            if valid(c):c.call_function('K2_DestroyComponent',self.state)
        if self.scope:self.scope.close()
        self.report['observer_scope_closed']=self.scope is not None and self.scope.closed
        self.report['original_scores_restored']=self.values()==self.score_before
        if valid(self.real):self.real.set_property('TargetScore',self.target_score)
        self.report['actual_tdm_target_score_restored']=self.real.get_property('TargetScore')==self.target_score
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        if self.sender_root:self.sender.remove_from_root()
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),owned_components_destroyed=all(not valid(c) or c.call_function('IsBeingDestroyed') or not c.component_is_registered() for c in self.components),original_health_unchanged=self.healths()==self.health_before,diagnostic_probe_root_removed=not self.sender_root or not self.sender.is_rooted(),production_profiles_restored=any(r['target_class']==self.cls and all(len(r['profiles'][p]['functions'])==1 for p in PROFILES) for r in ue.get_registered_mixins()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native relay timeout')
            if self.phase=='ready':self.ready()
            else:self.after_gc()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ACCOLADE_RELAY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ACCOLADE_RELAY_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPAccoladeRelayResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
