"""Actual native PlayerStarts/geometry and native GameMode RestartPlayer entry."""
import atexit
import copy
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import HitResult
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .message_validation import arg
from . import spawning as policy
from .spawn_validation_contract import require,validate


def position(actor):return actor.call_function('K2_GetActorLocation')
def move(actor,value):actor.call_function('K2_SetActorLocation',value,False,HitResult(),True)


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeSpawnResult'));self.profile=arg('UEPNativeSpawnProfile');self.started=time.monotonic();self.finished=False;self.phase='ready';self.actors=[];self.component=None;self.saved_flags=[];self.saved_pawns=[];self.labels={}
        self.report=dict(status='running',error=None,profile=self.profile,cases=[],private_cache_not_written=True,
            physics_query_replaced=False,native_rng_replaced=False,native_claim_timer_replaced=False,cached_player_starts_overwritten=False,
            network_acceptance=False,packaged_acceptance=False)
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.previous=self.cls.get_cdo().get_property('PythonMixinProfile');self.cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        atexit.register(self.finalize)

    def own(self,actor):self.actors.append(actor);return actor
    def start(self,label,xyz):
        actor=self.own(self.world.actor_spawn(ue.find_class('LyraPlayerStart'),ue.FVector(*xyz)));self.labels[actor]=label;return actor
    def cube(self,xyz,scale):
        actor=self.own(self.world.actor_spawn(ue.find_class('StaticMeshActor'),ue.FVector(*xyz)))
        mesh=actor.get_component_by_type(ue.find_class('StaticMeshComponent'));mesh.call_function('SetMobility',2)
        require(mesh.call_function('SetStaticMesh',ue.load_object(ue.find_class('StaticMesh'),'/Engine/BasicShapes/Cube.Cube')),'native collision cube setup failed')
        mesh.call_function('SetCollisionProfileName','BlockAll',True);actor.call_function('SetActorScale3D',ue.FVector(*scale));return actor
    def clear_claims(self,starts):
        for start in starts:start.set_property('ClaimingController',None)
    def spectator_enemies(self,value):
        for state,pawn in self.enemies:state.set_property('bOnlySpectator',value)

    def setup(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            state=policy.lib('GameplayStatics').call_function('GetGameState',world)
            if not valid(state):continue
            found=[c for c in ue.tobject_iterator(self.cls) if valid(c) and c.get_world()==world and c.call_function('GetOwner')==state]
            if len(found)!=1:continue
            controller=policy.lib('GameplayStatics').call_function('GetPlayerController',world,0)
            if not valid(controller) or not valid(controller.PlayerState) or not valid(controller.get_controlled_pawn()):continue
            team=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',world,ue.find_class('LyraTeamSubsystem'))
            own_team=policy.team_id(team,controller)
            enemies=[(p,p.call_function('GetPawn')) for p in state.get_property('PlayerArray') if valid(p) and policy.team_id(team,p)!=own_team and valid(p.call_function('GetPawn'))]
            if len(enemies)<2:return False
            self.world=world;self.component=found[0];self.controller=controller;self.state=state;self.enemies=enemies[:2]
            isolate_bots(policy.lib('GameplayStatics'),world,ue.find_class('AIController'))
            self.saved_flags=[(p,bool(p.get_property('bOnlySpectator'))) for p in state.get_property('PlayerArray')]
            for p,_ in self.saved_flags:
                if p!=controller.PlayerState:p.set_property('bOnlySpectator',True)
            for p,pawn in self.enemies:
                self.saved_pawns.append((pawn,position(pawn),int(pawn.CharacterMovement.MovementMode)))
                pawn.CharacterMovement.call_function('DisableMovement')
            self.report.update(natural_component_count=1,natural_metrics=copy.deepcopy(policy.metrics(self.component)))
            self.a=self.start('A',(400000.,400000.,4000.));self.b=self.start('B',(400100.,400000.,4000.))
            # A single wall edge yields a native partial fit. A narrow corridor
            # between opposite walls yields a native full fit.
            self.cube((410000.,400000.,4000.),(1.,20.,100.))
            self.cube((420000.-30.,400000.,4000.),(.2,20.,100.));self.cube((420000.+30.,400000.,4000.),(.2,20.,100.))
            self.full=self.start('full',(420000.,400000.,4000.));self.phase='physics';self.prepared=time.monotonic();return True
        return False

    def calibrate(self):
        require(int(self.component.call_function('UEPGetStartOccupancy',self.a,self.controller))==0,'far native fixture start not empty')
        self.partial=None
        for offset in (-30.,-10.,0.,10.,20.,30.,40.):
            candidate=self.start('partial',(410050.+offset,400000.,4000.))
            if int(self.component.call_function('UEPGetStartOccupancy',candidate,self.controller))==1:self.partial=candidate;break
        require(self.partial is not None,'native partial occupancy calibration failed')
        self.report['physics_states']={name:int(self.component.call_function('UEPGetStartOccupancy',actor,self.controller)) for name,actor in (('empty',self.a),('partial',self.partial),('full',self.full))}
        require(self.report['physics_states']==dict(empty=0,partial=1,full=2),'native full corridor occupancy calibration failed')

    def case(self,name,starts,root=False):
        self.report['pending_case']=name;atomic_write(self.path,self.report)
        method=policy.CHOOSE if root else policy.TDM
        owner='LyraPlayerSpawningManagerComponent' if root else 'TDM_PlayerSpawningManagmentComponent'
        chosen=policy.native_outputs(owner,method,self.component.call_function(method,self.controller,starts))['ReturnValue']
        self.report['cases'].append(dict(name=name,chosen=self.labels.get(chosen) if chosen is not None else None,
            claimed_after=[bool(self.component.call_function('UEPIsStartClaimed',s)) for s in starts]))

    def execute(self):
        self.calibrate();self.enemies[0][0].set_property('bOnlySpectator',False)
        move(self.enemies[0][1],ue.FVector(400010.,400500.,4000.));self.case('tdm_far',[self.a,self.b])
        move(self.enemies[0][1],ue.FVector(400050.,400500.,4000.));self.case('tdm_tie',[self.a,self.b])
        move(self.enemies[0][1],ue.FVector(400000.,400500.,4000.));self.enemies[1][0].set_property('bOnlySpectator',False)
        move(self.enemies[1][1],ue.FVector(401000.,400500.,4000.));self.case('tdm_max_pair',[self.a,self.b])
        self.enemies[1][0].set_property('bOnlySpectator',True);move(self.enemies[0][1],ue.FVector(400010.,400500.,4000.))
        for start in (self.a,self.b):require(self.component.call_function('UEPTryClaimStart',start,self.controller),'native claim failed')
        self.case('claimed_fallback',[self.a,self.b]);self.b.set_property('ClaimingController',None);self.case('unclaimed_priority',[self.a,self.b])
        self.case('no_candidates',[]);self.spectator_enemies(True);self.clear_claims([self.a,self.b])
        self.controller.PlayerState.set_property('bOnlySpectator',True);self.case('spectator',[self.a],True);self.case('spectator_empty',[],True)
        self.controller.PlayerState.set_property('bOnlySpectator',False)
        self.case('fallback_empty',[self.a,self.partial,self.full],True)
        self.clear_claims([self.a,self.partial,self.full]);self.case('fallback_partial',[self.partial,self.full],True)
        self.clear_claims([self.partial,self.full]);self.case('fallback_full',[self.full],True)
        self.restore_fixtures();before=copy.deepcopy(policy.metrics(self.component));self.old_pawn=self.controller.get_controlled_pawn();self.old_pawn.call_function('K2_DestroyActor')
        mode=policy.lib('GameplayStatics').call_function('GetGameMode',self.world);mode.call_function('RestartPlayer',self.controller)
        self.report['native_restart_executed']=True;prefix='python_' if self.profile=='Python' else 'native_'
        self.report['native_restart_choose_delta']=policy.metrics(self.component)[prefix+'choose']-before[prefix+'choose'];self.phase='restart';self.restarted=time.monotonic()

    def restore_fixtures(self):
        for p,value in self.saved_flags:p.set_property('bOnlySpectator',value)
        self.report['player_state_flags_restored']=all(bool(p.get_property('bOnlySpectator'))==v for p,v in self.saved_flags)
        for pawn,location,mode in self.saved_pawns:
            if valid(pawn):move(pawn,location);pawn.CharacterMovement.call_function('SetMovementMode',mode,0)
        self.report['pawn_positions_restored']=all(valid(p) and (position(p)-v).size()<.01 for p,v,_ in self.saved_pawns)
        for actor in reversed(self.actors):
            if valid(actor):actor.call_function('K2_DestroyActor')
        self.report['fixture_actors_destroyed']=all(not valid(a) for a in self.actors)

    def cleanup(self):
        if self.component:
            self.restore_fixtures();self.report['metrics']=copy.deepcopy(policy.metrics(self.component))
        self.cls.get_cdo().set_property('PythonMixinProfile',self.previous);self.report['selectors_restored']=self.cls.get_cdo().get_property('PythonMixinProfile')==self.previous

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<200.,'native spawning fixture timed out')
            if self.phase=='ready':self.setup()
            elif self.phase=='physics' and time.monotonic()-self.prepared>=.15:self.execute()
            elif self.phase=='restart':
                pawn=self.controller.get_controlled_pawn()
                if valid(pawn) and pawn!=self.old_pawn:
                    self.report['native_restart_new_pawn_valid']=True;self.finish();return False
                require(time.monotonic()-self.restarted<10.,'native RestartPlayer did not produce a new Pawn')
            return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_SPAWN_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_SPAWN_SHUTDOWN_'+self.report['status'].upper())


if any(v.startswith('-UEPNativeSpawnResult=') for v in __import__('sys').argv):
    validation=Validation();ticker=ue.add_ticker(validation.tick)
