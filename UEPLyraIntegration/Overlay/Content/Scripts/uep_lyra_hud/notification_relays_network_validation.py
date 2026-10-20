"""Only server sends test Verb messages; clients observe real production RPCs."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,LyraVerbMessage
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_abilities.jump_network_validation import Server as Playing,arg
from uep_lyra_abilities import network_identity as wire
from . import elimination_feed_relay_mixin as kill,accolade_relay_mixin as award
from .elimination_feed_relay_contract import FIELDS
from .notification_relays_network_contract import PEERS,PLAN,FALSE,require,validate_case


def tag(s):return GameplayTag(TagName=s)
def identity(o):
    if not valid(o):return None
    key=wire.key(wire.read(o));return list(key) if key else None
def tags(value):return sorted(str(t.TagName) for t in value.GameplayTags)
def payload_model(p,kind):return dict(kind=kind,verb=str(p.Verb.TagName),instigator=identity(p.Instigator),target=identity(p.Target),instigator_tags=tags(p.InstigatorTags),target_tags=tags(p.TargetTags),context_tags=tags(p.ContextTags),magnitude=float(p.Magnitude))


class Network:
    def __init__(self,result,peer,run):
        self.path=Path(result);self.root=self.path.parent;self.peer=peer;self.run=run;self.started=time.monotonic();self.finished=False;self.stage='ready';self.position=0;self.ready=False;self.armed=False;self.entries=dict(kill=0,award=0);self.receipts=[];self.kill_messages=[];self.award_messages=[];self.scopes=[];self.probes=[];self.sources={};self.components={};self.players={};self.statics=lib('GameplayStatics');self.playing_gate=False;self.playing_fingerprint=None;self.playing_stable_since=0.;self.waiting_reason='native Playing and two stable authority Pawns';self.target_score=None
        self.report=dict(status='running',error=None,run_id=run,peer=peer,cases=[],network_acceptance=False,server_waited_for_client_process_exit=False,**{k:False for k in FALSE})
    def token(self,name):
        value=read_json(self.root/name)
        if value is not None:require(value['run_id']==self.run,'foreign network relay token')
        return value
    def world_ready(self):
        if self.peer=='server' and not self.playing_gate:Playing.wait_playing(self)
        if self.peer=='server' and not self.playing_gate:return False
        if self.peer!='server' and self.token('playing-ready.json') is None:return False
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3,5) or 'L_Expanse' not in world.get_name():continue
            bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snapshot=bridge.call_function('CaptureSnapshot');mode=str(snapshot.NetMode)
            if mode!=('DedicatedServer' if self.peer=='server' else 'Client'):continue
            if self.peer!='server' and not (snapshot.bExperienceLoaded and snapshot.bAbilitySystemReady and snapshot.bHeroInputReady and snapshot.bHealthReady and not snapshot.bDamageImmune):continue
            self.world=world;self.report['native_mode']=mode;return True
        return False
    def setup(self):
        self.state=self.statics.call_function('GetGameState',self.world);self.router=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.team=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
        for kind,policy in (('kill',kill),('award',award)):
            cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(cls);actors=[c for c in ue.tobject_iterator(cls) if valid(c) and valid(c.call_function('GetOwner')) and c.get_world()==self.world];require(len(actors)==1,'one natural production relay required: '+kind);self.components[kind]=actors[0]
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[kind]=(cls,{p:r['python_class'] for p,r in row['profiles'].items()})
            for profile,base in self.sources[kind][1].items():
                def around(fn,key):
                    def invoke(component,Payload):
                        if self.armed and component==self.components[key]:self.entries[key]+=1;self.receipts.append(payload_model(Payload,key))
                        return fn(component,Payload)
                    invoke.override=policy.RECEIVE;return invoke
                ue.register_mixin_profile(cls,profile,type('ObservedRelay'+kind+profile+self.peer,(),dict(Received=around(base.Received,kind))))
        self.report.update(native_relay_counts={k:1 for k in self.components},callbacks_bound_once_native=True)
        scope=SubscriptionScope();self.scopes.append(scope)
        for kind,name,method,struct,channel in (('kill','BP_EliminationFeedProbe','ReadFeed',ue.load_object(ue.find_class('ScriptStruct'),kill.STRUCT),kill.CHANNEL),('award','BP_AccoladeRelayProbe','ReadNotification',ue.find_struct('LyraNotificationMessage'),award.CHANNEL)):
            probe=ue.load_class('/Game/UEPValidation/'+name+'.'+name+'_C').get_cdo();rooted=not probe.is_rooted()
            if rooted:probe.add_to_root()
            self.probes.append((probe,rooted))
            def reader(proxy,p=probe,m=method):
                value,ok=p.call_function(m,proxy);require(ok,'typed native notification extraction failed');return value
            scope.listen_gameplay_message(self.world,channel,struct,reader,self.on_kill if kind=='kill' else self.on_award)
        self.sender=self.probes[0][0]
        if self.peer=='server':
            self.scoring=self.state.get_component_by_type(ue.load_class('/ShooterCore/Elimination/B_TeamDeathMatchScoring.B_TeamDeathMatchScoring_C'));require(valid(self.scoring),'native TDM score component absent');self.target_score=int(self.scoring.get_property('TargetScore'));self.scoring.set_property('TargetScore',2000000000)
        else:
            self.controller=self.statics.call_function('GetPlayerController',self.world,0);self.player_id=int(self.controller.PlayerState.call_function('GetPlayerId'));self.report['player_id']=self.player_id
            atomic_write(self.root/(self.peer+'-ready.json'),dict(run_id=self.run,player_id=self.player_id,state_wire=identity(self.controller.PlayerState)))
        self.ready=True;self.stage='roster'
    def on_kill(self,channel,payload):
        if not self.armed:return
        v={name:getattr(payload,field) for name,field in FIELDS.items()};text=lib('KismetTextLibrary');self.kill_messages.append(dict(attacker=text.call_function('Conv_TextToString',v['Attacker']),attackee=text.call_function('Conv_TextToString',v['Attackee']),attacker_team=int(v['AttackerTeamID']),attackee_team=int(v['AttackeeTeamID']),tags=tags(v['InstigatorTags']),slot=str(v['TargetChannel'].TagName),channel=str(channel.TagName)))
    def on_award(self,channel,payload):
        if self.armed:self.award_messages.append(dict(player=identity(payload.TargetPlayer),target_channel=str(payload.TargetChannel.TagName),payload_tag=str(payload.PayloadTag.TagName),text=lib('KismetTextLibrary').call_function('Conv_TextToString',payload.PayloadMessage),object=identity(payload.PayloadObject),channel=str(channel.TagName)))
    def resolve(self,roster):
        states={int(a.call_function('GetPlayerId')):a for a in self.world.all_actors() if valid(a) and a.is_a(ue.find_class('LyraPlayerState'))};players={}
        for peer,row in roster.items():
            ps=states.get(row['player_id'])
            if not valid(ps) or identity(ps)!=row['state_wire']:return False
            pawn=ps.call_function('GetPawn')
            if not valid(pawn) or identity(pawn)!=row['pawn_wire'] or ps.call_function('GetPlayerName')!=row['name'] or self.team_id(pawn)!=row['team']:return False
            players[peer]=dict(state=ps,pawn=pawn)
        self.players=players;return True
    def team_id(self,pawn):return int(native_outputs('LyraTeamSubsystem','FindTeamFromActor',self.team.call_function('FindTeamFromActor',pawn))['TeamId'])
    def healths(self):return {p:float(v['pawn'].get_component_by_type(ue.find_class('LyraHealthComponent')).call_function('GetHealth')) for p,v in self.players.items()}
    def scores(self):
        if self.peer!='server':return []
        result=[]
        for p in PEERS:
            for name in ('Eliminations','Deaths','Assists'):result.append(int(self.players[p]['state'].call_function('GetStatTagStackCount',tag('ShooterGame.Score.'+name))))
        for p in PEERS:result.append(int(self.team.call_function('GetTeamTagStackCount',self.roster[p]['team'],tag('ShooterGame.Score.Eliminations'))))
        return result
    def restore_scores(self):
        if self.peer!='server':return
        after=self.scores()
        for i,p in enumerate(PEERS):
            for j,name in enumerate(('Eliminations','Deaths','Assists')):
                delta=after[3*i+j]-self.score_before[3*i+j]
                if delta:self.players[p]['state'].call_function('RemoveStatTagStack' if delta>0 else 'AddStatTagStack',tag('ShooterGame.Score.'+name),abs(delta))
        for i,p in enumerate(PEERS):
            delta=after[6+i]-self.score_before[6+i]
            if delta:self.team.call_function('RemoveTeamTagStack' if delta>0 else 'AddTeamTagStack',self.roster[p]['team'],tag('ShooterGame.Score.Eliminations'),abs(delta))
        require(self.scores()==self.score_before,'native score deltas not restored')
    def effects(self):
        a=kill.evidence(self.components['kill']);b=award.evidence(self.components['award'])
        return dict(multicast_requests=a['multicast_requests'],client_requests=b['client_requests'],cosmetic_broadcasts=a['cosmetic_broadcasts']+b['cosmetic_broadcasts'],diagnostic_fallbacks=a['diagnostic_fallbacks']+b['diagnostic_fallbacks'])
    def prepare(self,command):
        self.command=command
        for c in self.components.values():ue.set_mixin_profile(c,command['profile'])
        self.entries=dict(kill=0,award=0);self.receipts=[];self.kill_messages=[];self.award_messages=[];self.before=self.effects();self.health_before=self.healths();self.armed=True
        if self.peer=='server':self.score_before=self.scores()
    def record(self):
        after=self.effects();d={k:after[k]-self.before[k] for k in after};return dict(index=self.command['index'],profile=self.command['profile'],entries=copy.deepcopy(self.entries),receipts=copy.deepcopy(self.receipts),kill_notifications=copy.deepcopy(self.kill_messages),award_notifications=copy.deepcopy(self.award_messages),side_effects={k:d[k] for k in ('multicast_requests','client_requests','cosmetic_broadcasts')},diagnostic_fallbacks=d['diagnostic_fallbacks'],health_unchanged=self.healths()==self.health_before,observation_seconds=time.monotonic()-self.fired_seen if self.peer!='server' else 0.)
    def make_command(self):
        kind,source_peer,source_type,profile=PLAN[self.position];source=self.players[source_peer][{'ps':'state','pawn':'pawn','controller':'controller'}[source_type]] if source_peer else None;target=self.players['B0' if source_peer=='A' else 'A']['state'];verb='Lyra.Elimination.Message' if kind=='kill' else award.ROOT+'.EliminationChain.2x'
        require(source is None or identity(source) is not None,'existing source actor wire identity not yet available')
        message=LyraVerbMessage(Verb=tag(verb),Instigator=source,Target=target,InstigatorTags=GameplayTagContainer(GameplayTags=[tag('Gameplay.Damage.FellOutOfWorld')]),Magnitude=17.25)
        command=dict(run_id=self.run,index=self.position,kind=kind,source_peer=source_peer,source_type=source_type,profile=profile,roster=self.roster,expected_payload=payload_model(message,'kill' if kind=='kill' else 'award'))
        if kind=='kill':
            other='B0' if source_peer=='A' else 'A';command['expected_kill']=dict(attacker=self.roster[source_peer]['name'],attackee=self.roster[other]['name'],attacker_team=self.roster[source_peer]['team'],attackee_team=self.roster[other]['team'],tags=['Gameplay.Damage.FellOutOfWorld'],slot=kill.SLOT,channel=kill.CHANNEL)
        else:command['expected_award']=dict(player=self.roster[source_peer]['state_wire'] if source_peer else None,target_channel=award.ROOT,payload_tag=verb,text='',object=None,channel=award.CHANNEL)
        self.message=message;return command
    def send(self):
        require(self.peer=='server','clients must never synthesize relay input messages')
        channel='Lyra.Elimination.Message' if self.command['kind']=='kill' else 'Lyra.ShooterGame' if self.command['kind']=='parent' else award.ROOT
        self.sender.call_function('BroadcastVerb',self.router,tag(channel),self.message);self.fire_time=time.monotonic();atomic_write(self.root/'relay-fired.json',dict(run_id=self.run,index=self.position))
    def server_tick(self):
        if self.stage=='roster':
            ready={p:self.token(p+'-ready.json') for p in PEERS}
            if not all(ready.values()):return
            controllers,=self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('LyraPlayerController'));roster={};players={}
            for p,row in ready.items():
                found=[c for c in controllers if valid(c.PlayerState) and int(c.PlayerState.call_function('GetPlayerId'))==row['player_id']]
                if len(found)!=1:return
                c=found[0];ps=c.PlayerState;pawn=c.get_controlled_pawn()
                if not valid(pawn) or identity(ps) is None or identity(pawn) is None:return
                roster[p]=dict(player_id=row['player_id'],state_wire=identity(ps),pawn_wire=identity(pawn),name=ps.call_function('GetPlayerName'),team=self.team_id(pawn));players[p]=dict(controller=c,state=ps,pawn=pawn)
            require(roster['A']['state_wire']!=roster['B0']['state_wire'] and roster['A']['team']!=roster['B0']['team'],'native owners/teams are not distinct');self.roster=roster;self.players=players;self.report['roster']=roster;self.stage='publish'
        if self.stage=='publish':
            self.prepare(self.make_command());atomic_write(self.root/'relay-command.json',self.command);self.phase_started=time.monotonic();self.stage='armed'
        elif self.stage=='armed':
            rows=[self.token('relay-armed-'+p+'.json') for p in PEERS]
            if all(r is not None and r['index']==self.position for r in rows):self.send();self.stage='acks'
        elif self.stage=='acks':
            rows={p:self.token('relay-ack-'+p+'.json') for p in PEERS}
            if not all(r is not None and r['index']==self.position for r in rows.values()):return
            row=self.record();row['command']=copy.deepcopy(self.command);validate_case(self.command,row,'server')
            for p,r in rows.items():validate_case(self.command,r,p)
            self.restore_scores();self.armed=False;self.report['cases'].append(row);self.position+=1
            if self.position==len(PLAN):atomic_write(self.root/'relay-complete.json',dict(run_id=self.run));self.stage='release'
            else:self.stage='publish'
        elif self.stage=='release':
            done=[self.token(p+'-complete.json') for p in PEERS]
            if all(done):self.cleanup();atomic_write(self.root/'release.json',dict(run_id=self.run));self.stage='exits'
        elif self.stage=='exits':
            exits=[self.token(p+'-exited.json') for p in PEERS]
            if all(r is not None and r['exit_code']==0 for r in exits):self.report['server_waited_for_client_process_exit']=True;self.finish()
    def client_tick(self):
        if self.token('release.json') is not None:self.finish();return
        if self.token('relay-complete.json') is not None:
            require(len(self.report['cases'])==len(PLAN),'premature relay completion');atomic_write(self.root/(self.peer+'-complete.json'),dict(run_id=self.run));self.stage='release';return
        command=self.token('relay-command.json')
        if command is None or command['index']<len(self.report['cases']):return
        if not self.armed:
            if command['index']!=len(self.report['cases']) or not self.resolve(command['roster']):return
            self.prepare(command);atomic_write(self.root/('relay-armed-'+self.peer+'.json'),dict(run_id=self.run,index=command['index']));self.stage='fired'
        fired=self.token('relay-fired.json')
        if fired is None or fired['index']!=self.command['index']:return
        if self.stage=='fired':self.fired_seen=time.monotonic();self.stage='observe'
        if self.stage=='observe' and time.monotonic()-self.fired_seen>=1.:
            row=self.record();validate_case(self.command,row,self.peer);self.report['cases'].append(row);atomic_write(self.root/('relay-ack-'+self.peer+'.json'),dict(row,run_id=self.run));self.armed=False;self.stage='next'
    def cleanup(self):
        if getattr(self,'cleanup_done',False):return
        self.armed=False
        if self.peer=='server' and hasattr(self,'score_before'):self.restore_scores()
        for scope in self.scopes:scope.close()
        for c in self.components.values():ue.clear_mixin_profile(c)
        for cls,profiles in self.sources.values():
            for p,base in profiles.items():ue.register_mixin_profile(cls,p,base)
        for probe,rooted in self.probes:
            if rooted:probe.remove_from_root()
        if self.target_score is not None:self.scoring.set_property('TargetScore',self.target_score)
        self.report.update(observer_scopes_closed=bool(self.scopes) and all(s.closed for s in self.scopes),profile_overrides_cleared=bool(self.components) and all(str(ue.get_mixin_profile(c))=='Python' for c in self.components.values()),profile_classes_restored=all(any(r['target_class']==cls and all(r['profiles'][p]['python_class'] is base for p,base in profiles.items()) for r in ue.get_registered_mixins()) for cls,profiles in self.sources.values()),probe_roots_removed=all(not rooted or not probe.is_rooted() for probe,rooted in self.probes),original_scores_restored=self.peer!='server' or not hasattr(self,'score_before') or self.scores()==self.score_before,target_score_restored=self.target_score is None or self.scoring.get_property('TargetScore')==self.target_score)
        self.cleanup_done=True
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<480.,'network notification relays timeout')
            if not self.ready:
                if self.world_ready():self.setup()
            else:
                if self.peer=='server':isolate_bots(self.statics,self.world,ue.find_class('LyraPlayerBotController'));self.server_tick()
                else:self.client_tick()
            self.report['stage']=self.stage;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error,network_acceptance=not bool(error));atomic_write(self.path,self.report);(ue.log_error if error else ue.log)('UEP_NOTIFICATION_RELAYS_NETWORK_READY' if not error else 'UEP_NOTIFICATION_RELAYS_NETWORK_FAILED '+error);ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:
                require(len(self.report['cases'])==len(PLAN),'relay cases absent at shutdown');require(all(self.report[k] for k in ('observer_scopes_closed','profile_overrides_cleared','profile_classes_restored','probe_roots_removed','original_scores_restored','target_score_restored')),'relay shutdown cleanup missing');self.report['status']='passed'
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NOTIFICATION_RELAYS_'+('NETWORK' if self.peer=='server' else 'SHUTDOWN')+'_'+self.report['status'].upper())


if any(v.startswith('-UEPNotificationRelaysNetworkResult=') for v in sys.argv):
    validation=Network(arg('-UEPNotificationRelaysNetworkResult='),arg('-UEPJumpPeer='),arg('-UEPJumpRun='));atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
