"""Native two-local-player bomb elimination;poses are an explicit test fixture."""
import atexit,copy,math,sys,time,traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from unreal_engine.enums import EObjectTypeQuery,ELyraTeamComparison
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_world import arena_actor_mixin as actors,arena_mode_mixin as modes,arena_phases_mixin as phases
from .arena_local_input_validation import Validation as InputValidation,arg,path,dead,valid,base,drop
from .melee_trace_mixin import native_outputs
from .arena_opponent_bomb_contract import validate,FORBIDDEN

class Validation(InputValidation):
    def __init__(self):
        super().__init__(arg('UEPArenaOpponentResult'),arg('UEPArenaOpponentProfile'))
        self.death_scope=SubscriptionScope();self.message_scope=SubscriptionScope();self.death=None;self.last_health=[]
        self.report['native_elimination_messages']=[]
        self.report.update(dict.fromkeys(FORBIDDEN,False));self.report.update(test_bombs_destroyed_before_fuse=False,natural_explosion_tested=True,pawn_position_written=True,bounded_pose_fixture_used=True)
        for class_path,selector in [(actors.HERO,actors.SELECTOR),(actors.DEATH,'PythonMixinProfile'),*[(p,'PythonMixinProfile') for p in (modes.BASE,modes.LIVES,modes.LOCAL,*phases.CLASSES.values())]]:
            cls=ue.load_class(class_path)
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            self.selectors.append((cls,selector,cls.get_cdo().get_property(selector)));cls.get_cdo().set_property(selector,self.profile)

    def health(self):
        result=[]
        for i,p in enumerate(self.players):
            component=p['pawn'].get_component_by_type(ue.find_class('LyraHealthComponent')) if valid(p['pawn']) else None
            result.append(float(component.call_function('GetHealth')) if valid(component) else self.last_health[i] if i<len(self.last_health) else 0.)
        self.last_health=result;return list(result)

    def scores(self):
        return [[int(p['state'].call_function('GetStatTagStackCount',GameplayTag(TagName='ShooterGame.Score.'+name))) for name in ('Eliminations','Deaths','Assists')] for p in self.players]

    def team_scores(self):
        return [int(self.team.call_function('GetTeamTagStackCount',team,GameplayTag(TagName='ShooterGame.Score.Eliminations'))) for team in self.team_ids]

    def clear_cell(self,point):
        value=drop.lib('KismetSystemLibrary').call_function('BoxOverlapActors',WorldContextObject=self.world,BoxPos=point,BoxExtent=ue.FVector(48.,48.,48.),ObjectTypes=[EObjectTypeQuery.ObjectTypeQuery2,EObjectTypeQuery.ObjectTypeQuery1,EObjectTypeQuery.ObjectTypeQuery3],ActorClassFilter=None,ActorsToIgnore=[p['pawn'] for p in self.players])
        found=native_outputs('KismetSystemLibrary','BoxOverlapActors',value)['OutActors']
        return not any(a.is_a(ue.find_class('StaticMeshActor')) or a.is_a(ue.load_class(base.BLOCK)) for a in found)

    def start_case(self):
        if self.health()!=[100.,100.]:return
        for p in self.players:
            if p['asc'].call_function('GetGameplayTagCount',GameplayTag(TagName='Gameplay.DamageImmunity')):return
        self.team=drop.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
        teams=native_outputs('LyraTeamSubsystem','CompareTeams',self.team.call_function('CompareTeams',self.players[0]['state'],self.players[1]['state']))
        self.require(int(teams['ReturnValue'])==int(ELyraTeamComparison.DifferentTeams),'Two native Arena teams required')
        self.team_ids=[int(teams['TeamIdA']),int(teams['TeamIdB'])]
        self.mode=self.statics.call_function('GetGameState',self.world).get_component_by_type(ue.load_class(modes.BASE))
        self.require(valid(self.mode),'Original Arena scoring component required');self.mode_before=copy.deepcopy(modes.evidence(self.mode))
        probe=ue.load_class('/Game/UEPValidation/BP_GamePhaseProbe.BP_GamePhaseProbe_C')
        if not probe.is_rooted():probe.add_to_root();self.roots.append(probe)
        self.message_probe=probe.get_cdo()
        def reader(proxy):
            payload,ok=self.message_probe.call_function('ReadVerb',proxy);self.require(ok,'Typed native elimination extraction failed');return payload
        self.message_scope.listen_gameplay_message(self.world,'Lyra.Elimination.Message',ue.find_struct('LyraVerbMessage'),reader,self.on_elimination)
        self.score_before=self.scores();self.team_before=self.team_scores()
        source=self.players[0]['pawn'];target=self.players[1]['pawn']
        found=self.statics.call_function('GetAllActorsOfClass',self.world,ue.find_class('LyraPlayerStart'))
        starts=native_outputs('GameplayStatics','GetAllActorsOfClass',found)['OutActors']
        starts=sorted(starts,key=lambda a:tuple(float(getattr(a.get_actor_location(),k)) for k in ('x','y','z')))
        self.require(len(starts)>=2,'Two original map player starts required for the pose fixture')
        position=starts[0].get_actor_location();self.safe=starts[-1].get_actor_location()
        self.require(math.hypot(self.safe.x-position.x,self.safe.y-position.y)>400.,'Original map starts do not provide distinct safe poses')
        self.require(bool(source.call_function('K2_TeleportTo',position,source.get_actor_rotation())),'Native source pose placement rejected')
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
            cell=ue.FVector(position.x+100.*dx,position.y+100.*dy,50.)
            if self.clear_cell(cell):break
        else:raise AssertionError('Original Arena spawn has no free adjacent blast cell')
        health=target.get_component_by_type(ue.find_class('LyraHealthComponent'));self.death_scope.bind_event(health,'OnDeathStarted',self.on_death)
        self.require(bool(target.call_function('K2_TeleportTo',ue.FVector(cell.x,cell.y,position.z),target.get_actor_rotation())),'Native opponent pose placement rejected')
        self.report['pose_fixture']=dict(owner_original_player_start=[float(position.x),float(position.y)],opponent_cell=[float(cell.x),float(cell.y)],safe_original_player_start=[float(self.safe.x),float(self.safe.y)],purpose='Place owner at one original map start and opponent in its adjacent blast cell;move owner to another original map start after real bomb creation.No movement/pixel parity claim.')
        self.last_health=[100.,100.];super().start_case()

    def on_death(self,pawn):
        component=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
        self.death=dict(observed=True,pawn=path(pawn),player_state=path(self.players[1]['state']),health=float(component.call_function('GetHealth')),
            seconds_after_bomb_creation=float(self.statics.call_function('GetTimeSeconds',self.world))-self.bomb_observed_at+self.bomb_age)
        self.last_health[1]=0.
        # This is a one-shot observer. Detach before the original death ability
        # retires its component; cleanup must not access a destroyed delegate.
        self.death_scope.close()

    def on_elimination(self,channel,payload):
        comparison=native_outputs('LyraTeamSubsystem','CompareTeams',self.team.call_function('CompareTeams',payload.Instigator,payload.Target))['ReturnValue']
        relation=next(name for name in ('OnSameTeam','DifferentTeams','InvalidArgument') if int(getattr(ELyraTeamComparison,name))==int(comparison))
        self.report['native_elimination_messages'].append(dict(channel=str(channel.TagName),instigator=path(payload.Instigator),target=path(payload.Target),
            target_is_opponent=payload.Target==self.players[1]['state'],instigator_is_null=payload.Instigator is None,
            source_owner=next((i for i,p in enumerate(self.players) if payload.Instigator==p['state']),None),team_comparison=relation))

    def observe_spawn(self):
        super().observe_spawn()
        if self.phase!='repeat':return
        self.original_fuse=float(self.bomb.get_property('BombLifespan'));self.original_radius=int(self.bomb.get_property('ExplosionRadius'));self.bomb_counts=base.evidence(self.bomb)
        self.bomb_observed_at=float(self.statics.call_function('GetTimeSeconds',self.world));self.bomb_age=float(self.bomb.call_function('GetGameTimeSinceCreation'))
        self.require(bool(self.players[0]['pawn'].call_function('K2_TeleportTo',self.safe,self.players[0]['pawn'].get_actor_rotation())),'Native safe owner pose rejected')
        self.enter('natural')

    def observe_natural(self):
        self.report['pending_natural']=dict(health=self.health(),scores=self.scores(),remaining=self.remaining(),death=self.death)
        self.require(time.monotonic()-self.since<30.,'Native opponent bomb/death/score/refund did not complete')
        if self.death is None or not dead(self.bomb) or self.remaining()!=[1.,1.]:return
        scores=self.scores();team_scores=self.team_scores();before=self.score_before
        selected='python_' if self.profile=='Python' else 'fallback_';other='fallback_' if self.profile=='Python' else 'python_'
        counts=self.counts(0);mode=modes.evidence(self.mode)
        self.report['result']=dict(drop=copy.deepcopy(self.current),health_before=list(self.initial_health),health_after=self.health(),opponent_death=self.death,
            score_before=before,score_after=scores,score_delta=[[a-b for a,b in zip(after,prior)] for after,prior in zip(scores,before)],
            team_score_delta=[a-b for a,b in zip(team_scores,self.team_before)],different_native_teams=True,
            selected_elimination_callbacks=mode[selected+'elimination']-self.mode_before[selected+'elimination'],other_elimination_callbacks=mode[other+'elimination']-self.mode_before[other+'elimination'],
            selected_input_callbacks=sum(counts[k]-self.before_counts[k] for k in counts if k.startswith(selected)),other_input_callbacks=sum(counts[k]-self.before_counts[k] for k in counts if k.startswith(other)),
            native_bomb_callbacks={k:self.bomb_counts[selected+k] for k in ('trigger','increment','destroyed')},remaining_after_refund=self.remaining(),
            original_fuse_seconds=self.original_fuse,original_explosion_radius=self.original_radius,fixed_timestep_used=False,bombs_destroyed_by_cleanup=sum(not dead(b) for b in self.bombs_owned))
        self.finish()

    def cleanup(self):
        self.death_scope.close();self.report['death_observer_closed']=self.death_scope.closed
        self.message_scope.close();self.report['message_observer_closed']=self.message_scope.closed
        super().cleanup();self.report['input_released']=True

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_ARENA_OPPONENT_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ARENA_OPPONENT_SHUTDOWN_'+self.report['status'].upper())

    def tick(self,delta):
        try:
            self.require(time.monotonic()-self.started<180.,'Arena opponent observation timeout: '+self.phase)
            if self.phase=='world':self.discover_world()
            elif self.phase=='players':self.discover_players()
            elif self.phase=='settle':
                if time.monotonic()-self.since>=1.:self.start_case()
            elif self.phase=='press':
                self.press(self.frames<3);self.frames+=1
                if self.frames>=6:self.enter('spawn')
            elif self.phase=='spawn':self.observe_spawn()
            elif self.phase=='natural':self.observe_natural()
            atomic_write(self.path,self.report)
        except Exception:self.finish(traceback.format_exc())
        return not self.finished

if any(v.startswith('-UEPArenaOpponentResult=') for v in sys.argv):
    validation=Validation();atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
