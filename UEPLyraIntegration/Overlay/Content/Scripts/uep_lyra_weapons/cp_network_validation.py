"""Opt-in real CP server/two-client capture with native scoring and local feedback."""
import atexit,copy,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_network_io import atomic_write,read_json
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_world import control_point_feedback_mixin as volume
from uep_lyra_hud import control_point_widgets_mixin as hud,cue_widget_mixin as cue,match_message_mixin as match,waiting_message_mixin as waiting
from uep_lyra_hud.notification_relays_network_validation import identity
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_weapons import cp_scoring_mixin as scoring,scoring_base_mixin as base,game_phases_mixin as phases
from uep_lyra_weapons.cp_network_contract import FALSE,require,validate,validate_result

SCORE='ShooterGame.ControlPoint.TeamScore'
CAPTURE='ShooterGame.Score.ControlPointCapture'
MATCH_CUE='/ShooterCore/GameplayCues/GCNL_MatchDecided.GCNL_MatchDecided_C'
WAIT_CUE='/ShooterCore/GameplayCues/GCNL_WaitingForPlayers.GCNL_WaitingForPlayers_C'
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def tag(name):return GameplayTag(TagName=name)
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def world_of(obj):
    if not valid(obj):return None
    # The SDK get_world helper accepts Actors/Components, not UserWidgets.
    if obj.is_a(ue.find_class('UserWidget')):
        player=obj.call_function('GetOwningPlayer')
        return player.get_world() if valid(player) else None
    try:return obj.get_world()
    except Exception:return None

class Network:
    def __init__(self,path,peer,run,profile):
        self.path=Path(path);self.root=self.path.parent;self.peer=peer;self.run=run;self.profile=profile;self.started=time.monotonic();self.finished=False;self.stage='ready';self.players={};self.pending=[];self.audio=[];self.boot=[];self.class_roots=[];self.sources={};self.ready=False
        self.report=dict(status='running',error=None,peer=peer,run_id=run,requested_profile=profile,server_waited_for_client_process_exit=False);self.report.update(dict.fromkeys(FALSE,False))
        paths=[base.CLASS,scoring.CLASS,volume.CLASS,*phases.CLASSES.values(),*hud.CLASSES.values(),cue.CLASS,MATCH_CUE,WAIT_CUE,match.CLASS,waiting.CLASS,
            '/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C','/ShooterCore/ControlPoint/B_MusicManagerComponent_ControlPoint.B_MusicManagerComponent_ControlPoint_C']
        preexisting=[]
        for path in dict.fromkeys(paths):
            cls=ue.load_class(path)
            if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
            for obj in ue.tobject_iterator(cls):
                world=world_of(obj)
                if valid(world) and world.get_world_type() in (1,3,5):preexisting.append(obj.get_path_name())
            cdo=cls.get_cdo()
            if 'PythonMixinProfile' in cdo.properties():self.boot.append((cls,cdo.get_property('PythonMixinProfile')));cdo.set_property('PythonMixinProfile',profile)
        self.report['profiles_selected_before_component_creation']=not preexisting;require(not preexisting,'Profile selection happened after runtime instances: '+str(preexisting))
        cls=ue.load_class(volume.CLASS);ue.register_declared_mixin(cls);registered,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources={p:r['python_class'] for p,r in registered['profiles'].items()};self.volume_class=cls
        for name,source in self.sources.items():
            methods={key:fn for key,fn in vars(source).items() if callable(fn) and hasattr(fn,'override')};fn=methods['CaptureAudio']
            def observe(fn):
                def invoke(actor,OwnerTeamID):
                    self.pending.append((actor,int(OwnerTeamID),time.monotonic()));return fn(actor,OwnerTeamID)
                invoke.override=volume.GATES['CaptureAudio'];return invoke
            methods['CaptureAudio']=observe(fn);ue.register_mixin_profile(cls,name,type('ObservedCPAudio'+name+peer,(),methods))
    def read(self,name):
        value=read_json(self.root/name)
        if value is not None:require(value['run_id']==self.run,'Foreign CP network token')
        return value
    def write(self,name,value):atomic_write(self.root/name,dict(value,run_id=self.run))
    def phase(self,name):return bool(self.phase_system.call_function('IsPhaseActive',tag('ShooterGame.GamePhase.'+name)))
    def find_world(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3,5) or 'L_Convolution_Blockout' not in world.get_name():continue
            bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot');mode=str(snap.NetMode)
            if mode!=('DedicatedServer' if self.peer=='server' else 'Client'):continue
            self.world=world;self.phase_system=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',world,ue.find_class('LyraGamePhaseSubsystem'))
            if self.peer=='server':
                if not self.phase('Playing'):continue
            elif not(self.read('playing-ready.json') and snap.bExperienceLoaded and snap.bAbilitySystemReady and snap.bHeroInputReady and snap.bHealthReady and snap.Health==100. and not snap.bDamageImmune):continue
            self.report['native_mode']=mode;return True
        return False
    def setup(self):
        statics=lib('GameplayStatics');self.state=statics.call_function('GetGameState',self.world);self.team=lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'));self.scoring=self.state.get_component_by_type(ue.load_class(scoring.CLASS))
        if not valid(self.scoring):return
        self.points=list(self.scoring.get_property('ControlPoints'))
        if len(self.points)!=3 or any(not valid(p) for p in self.points):return
        if self.peer=='server':
            controllers=[a for a in self.world.all_actors() if valid(a) and a.is_a(ue.find_class('LyraPlayerController')) and not a.is_a(ue.find_class('LyraPlayerBotController')) and valid(a.get_property('PlayerState'))]
            if len(controllers)!=2:return
            if not all(self.healthy(c.get_property('PlayerState')) for c in controllers):return
            self.original_target=int(self.scoring.get_property('TargetScore'));self.write('playing-ready.json',{});self.stage='roster'
        else:
            self.controller=statics.call_function('GetPlayerController',self.world,0);ps=self.controller.PlayerState
            if not self.healthy(ps):return
            self.write(self.peer+'-ready.json',dict(player_id=int(ps.call_function('GetPlayerId')),state_wire=identity(ps)));self.stage='roster'
        self.ready=True
    def healthy(self,ps):
        pawn=ps.call_function('GetPawn');asc=ps.get_property('AbilitySystemComponent')
        if not valid(pawn) or not valid(asc) or asc.get_property('AvatarActor')!=pawn or asc.get_property('OwnerActor')!=ps:return False
        health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
        return valid(health) and float(health.call_function('GetHealth'))==100.
    def resolve(self,roster):
        values={int(a.call_function('GetPlayerId')):a for a in self.world.all_actors() if valid(a) and a.is_a(ue.find_class('LyraPlayerState'))};players={}
        for peer,row in roster.items():
            ps=values.get(row['player_id'])
            if not valid(ps) or identity(ps)!=row['state_wire'] or not self.healthy(ps):return False
            pawn=ps.call_function('GetPawn')
            if identity(pawn)!=row['pawn_wire']:return False
            players[peer]=dict(state=ps,pawn=pawn)
        self.players=players;return True
    def scores(self):return [int(self.team.call_function('GetTeamTagStackCount',self.roster[p]['team'],tag(SCORE))) for p in ('A','B0')]
    def captures(self):return [int(self.players[p]['state'].call_function('GetStatTagStackCount',tag(CAPTURE))) for p in ('A','B0')]
    def sample_audio(self):
        for actor,team,stamp in self.pending:
            audio=actor.get_property('Audio_CPComplete');sound=audio.get_property('Sound');self.audio.append(dict(owner_team=team,sound=sound.get_path_name() if valid(sound) else None,playing=bool(audio.call_function('IsPlaying'))))
        self.pending=[]
    def make_result(self):
        cues=[a for a in ue.tobject_iterator(ue.load_class(MATCH_CUE)) if world_of(a)==self.world]
        widgets=[w for w in ue.tobject_iterator(ue.load_class(hud.CLASSES['score'])) if world_of(w)==self.world and w.get_property('ControlPointMode')==self.scoring]
        display={}
        if len(widgets)==1:
            text=lib('KismetTextLibrary');w=widgets[0];display={key:text.call_function('Conv_TextToString',w.get_property(field).call_function('GetText')) for key,field in (('ally','AllyScore'),('enemy','EnemyScore'),('target','Goal'))}
        asc=[self.players[p]['state'].get_property('AbilitySystemComponent') for p in ('A','B0')]
        row=dict(roster=self.roster,point_wire=self.point_wire,team_scores=self.scores(),capture_stats=self.captures(),point_owner=int(self.point.get_property('OwnerTeamID')),target_score=int(self.scoring.get_property('TargetScore')),
            healths=[float(self.players[p]['pawn'].get_component_by_type(ue.find_class('LyraHealthComponent')).call_function('GetHealth')) for p in ('A','B0')],damage_immunity=[bool(a.call_function('GetGameplayTagCount',tag('Gameplay.DamageImmunity'))) for a in asc],
            capture_audio_owner_teams=[a['owner_team'] for a in self.audio],capture_audio_sounds=[a['sound'] for a in self.audio],capture_audio_playing=[a['playing'] for a in self.audio],native_score_widgets=len(widgets),hud=display,match_decided_cue_actors=len(cues),native_postgame=self.phase('PostGame'),native_playing=self.phase('Playing'),effective_profiles=dict(scoring=str(ue.get_mixin_profile(self.scoring)),point=str(ue.get_mixin_profile(self.point)),**({'score_widget':str(ue.get_mixin_profile(widgets[0]))} if len(widgets)==1 else {})))
        if self.peer=='server':
            prefix='python_' if self.profile=='Python' else 'fallback_';counts=scoring.evidence(self.scoring);row.update(selected_capture_calls=counts[prefix+'Capture']-self.before_counts[prefix+'Capture'],selected_victory_calls=counts[prefix+'Victory']-self.before_counts[prefix+'Victory'],real_overlap_observed=self.overlap_seen)
        return row
    def restore(self):
        for p,before,after in zip(('A','B0'),self.baseline_scores,self.scores()):
            if after!=before:self.team.call_function('RemoveTeamTagStack' if after>before else 'AddTeamTagStack',self.roster[p]['team'],tag(SCORE),abs(after-before))
        for p,before,after in zip(('A','B0'),self.baseline_captures,self.captures()):
            if after!=before:self.players[p]['state'].call_function('RemoveStatTagStack' if after>before else 'AddStatTagStack',tag(CAPTURE),abs(after-before))
        self.scoring.call_function(scoring.SET_TARGET,self.original_target)
        self.players['A']['pawn'].call_function('K2_SetActorLocation',NewLocation=ue.FVector(*self.origin),bSweep=False,bTeleport=True)
        self.report['native_scores_and_capture_stats_restored']=self.scores()==self.baseline_scores and self.captures()==self.baseline_captures;self.report['target_score_restored']=int(self.scoring.get_property('TargetScore'))==self.original_target
        self.write('restored.json',dict(scores=self.baseline_scores,captures=self.baseline_captures,target=self.original_target))
    def server_tick(self):
        if self.stage=='roster':
            ready={p:self.read(p+'-ready.json') for p in ('A','B0')}
            if not all(ready.values()):return
            states={int(a.call_function('GetPlayerId')):a for a in self.world.all_actors() if valid(a) and a.is_a(ue.find_class('LyraPlayerState'))};self.roster={}
            for p,row in ready.items():
                ps=states[row['player_id']];pawn=ps.call_function('GetPawn');team=native_outputs('LyraTeamSubsystem','FindTeamFromActor',self.team.call_function('FindTeamFromActor',pawn))['TeamId'];self.roster[p]=dict(player_id=row['player_id'],state_wire=identity(ps),pawn_wire=identity(pawn),team=int(team),name=ps.call_function('GetPlayerName'))
            require(self.roster['A']['team']!=self.roster['B0']['team'],'Distinct natural CP teams required');require(self.resolve(self.roster),'Native authority owners not canonical')
            self.report['initial_canonical_healthy_owners']=True;self.point=self.points[0];self.point_wire=identity(self.point);require(self.point_wire is not None,'Existing control-point wire identity required');self.baseline_scores=self.scores();self.baseline_captures=self.captures();require(self.baseline_scores==self.baseline_captures==[0,0],'Pristine CP score fixture required')
            self.origin=vec(self.players['A']['pawn'].get_actor_location());self.scoring.call_function(scoring.SET_TARGET,1);self.before_counts=copy.deepcopy(scoring.evidence(self.scoring));self.overlap_seen=False
            self.write('roster.json',dict(roster=self.roster,point_wire=self.point_wire));self.stage='armed'
        elif self.stage=='armed':
            if not all(self.read('armed-'+p+'.json') for p in ('A','B0')):return
            pawn=self.players['A']['pawn'];pawn.get_property('CharacterMovement').call_function('StopMovementImmediately');location=self.point.get_actor_location();half=float(pawn.get_property('CapsuleComponent').call_function('GetScaledCapsuleHalfHeight'))
            pawn.call_function('K2_SetActorLocation',NewLocation=ue.FVector(location.x,location.y,location.z+half+20.),bSweep=False,bTeleport=True);self.stage='capture'
        elif self.stage=='capture':
            self.overlap_seen |= self.players['A']['pawn'] in self.point.get_property('OverlappingPawns')
            if not(self.phase('PostGame') and self.audio):return
            row=self.make_result()
            if row['damage_immunity']!=[True,True]:return
            validate_result(row,self.peer);self.report['result']=row;self.stage='client-capture'
        elif self.stage=='client-capture':
            if not all(self.read('captured-'+p+'.json') for p in ('A','B0')):return
            self.restore();self.stage='restore-acks'
        elif self.stage=='restore-acks':
            if not all(self.read('restored-'+p+'.json') for p in ('A','B0')):return
            self.write('ready-server.json',{});self.stage='exit'
        elif self.stage=='exit':
            if self.read('release.json') is None:return
            source=self.read('server-release.json')
            if source is None:return
            require(source['client_exit_codes']==dict(A=0,B0=0),'Real client exits required');self.report['server_waited_for_client_process_exit']=True;self.finish()
    def client_tick(self):
        if self.stage=='roster':
            source=self.read('roster.json')
            if source is None or not self.resolve(source['roster']):return
            self.roster=source['roster'];self.point_wire=source['point_wire'];matches=[p for p in self.points if identity(p)==self.point_wire]
            if len(matches)!=1:return
            self.point=matches[0];self.report['initial_canonical_healthy_owners']=True;self.write('armed-'+self.peer+'.json',{});self.stage='capture'
        elif self.stage=='capture':
            if not self.audio:return
            row=self.make_result()
            self.report['last_observed_result']=row
            if row['team_scores']!=[1,0] or row['capture_stats']!=[1,0] or row['damage_immunity']!=[True,True] or row['match_decided_cue_actors']<1 or row['native_score_widgets']!=1:return
            if row['hud']!=dict(ally='1' if self.peer=='A' else '0',enemy='0' if self.peer=='A' else '1',target='1') or row['point_owner']!=self.roster['A']['team'] or row['target_score']!=1:return
            validate_result(row,self.peer);self.report['result']=row;self.write('captured-'+self.peer+'.json',{});self.stage='restore'
        elif self.stage=='restore':
            source=self.read('restored.json')
            if source is None or self.scores()!=source['scores'] or self.captures()!=source['captures'] or int(self.scoring.get_property('TargetScore'))!=source['target']:return
            self.report.update(native_scores_and_capture_stats_restored=True,target_score_restored=True);self.write('restored-'+self.peer+'.json',{});self.write('ready-'+self.peer+'.json',{});self.stage='exit'
        elif self.stage=='exit':
            if self.read('release.json') is not None:self.finish()
    def cleanup(self):
        for name,source in self.sources.items():ue.register_mixin_profile(self.volume_class,name,source)
        self.report['observer_profiles_restored']=all(any(r['target_class']==self.volume_class and r['profiles'][name]['python_class'] is source for r in ue.get_registered_mixins()) for name,source in self.sources.items())
        for cls,value in reversed(self.boot):cls.get_cdo().set_property('PythonMixinProfile',value)
        self.report['boot_selectors_restored']=all(c.get_cdo().get_property('PythonMixinProfile')==v for c,v in self.boot)
        for cls in self.class_roots:cls.remove_from_root()
        self.report['observer_class_roots_restored']=all(not c.is_rooted() for c in self.class_roots)
        self.pending=[];self.players={};self.points=[]
        for name in ('world','state','scoring','team','point','controller','phase_system'):setattr(self,name,None)
        self.boot=[];self.class_roots=[];self.sources={};self.volume_class=None
        self.report['observer_references_released']=True
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'CP network timeout at '+self.stage)
            self.sample_audio()
            if not self.ready:
                if self.find_world():self.setup()
            elif self.peer=='server':self.server_tick()
            else:self.client_tick()
            self.report['stage']=self.stage;self.report['capture_audio_observations']=self.audio;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report);(ue.log_error if error else ue.log)('UEP_CP_NETWORK_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CP_NETWORK_SHUTDOWN_'+self.report['status'].upper())

if any(v.startswith('-UEPCPNetworkResult=') for v in sys.argv):
    validation=Network(arg('UEPCPNetworkResult'),arg('UEPCPNetworkPeer'),arg('UEPCPNetworkRun'),arg('UEPCPNetworkProfile'));atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
