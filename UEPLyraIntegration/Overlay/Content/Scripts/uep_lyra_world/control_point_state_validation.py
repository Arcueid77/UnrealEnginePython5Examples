"""Real capsule overlap events and original Timeline capture/contest/recapture."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead,color
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_weapons.cp_scoring_mixin import CLASS as SCORING
from . import control_point_state_mixin as policy
from .control_point_state_contract import PROFILES,require,validate


def path(o):return o.get_path_name() if valid(o) else None
def count(a,n):return sum(policy.evidence(a)[p+'_'+n] for p in ('python','fallback'))


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,cases=[]);self.index=0;self.volumes=[];self.units=[]
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','overlap_callbacks_replayed','timeline_callbacks_replayed','pawn_arrays_written_by_fixture','health_properties_written','timeline_update_finish_rpc_vfx_audio_business_migrated'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);self.state=self.statics.call_function('GetGameState',self.world);self.scoring=self.state.get_component_by_type(ue.load_class(SCORING));require(valid(self.scoring),'actual CP experience absent')
        self.original_points=list(self.scoring.get_property('ControlPoints'));self.original_owners=list(self.scoring.get_property('ControlPointOwnerTeams'));self.real_target=self.scoring.get_property('TargetScore');self.scoring.set_property('TargetScore',2000000000)
        initial=[a for a in self.world.all_actors() if valid(a) and a.is_a(self.cls)];self.report['natural_map_python_ready']=sum(policy.evidence(a)['python_Ready'] for a in initial);self.report['natural_map_volumes']=len(initial)
        self.start_case()
    def unit(self,index):
        pc=self.world.actor_spawn(ue.find_class('LyraPlayerController'));ps=pc.get_property('PlayerState');pawn=self.world.actor_spawn(ue.find_class('LyraCharacter'),ue.FVector(self.x+1200.,250000.+index*400.,3050.));self.actors.extend((pc,ps,pawn));pc.call_function('Possess',pawn);pawn.get_property('CharacterMovement').call_function('SetComponentTickEnabled',False);pawn.get_property('CapsuleComponent').call_function('SetGenerateOverlapEvents',True)
        manager=ue.new_object(ue.find_class('CheatManager'),pc);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager);cheats.call_function('SetTeam',index+1);return dict(pc=pc,state=ps,pawn=pawn,manager=manager,cheats=cheats)
    def move(self,index,inside):
        self.units[index]['pawn'].call_function('K2_SetActorLocation',NewLocation=ue.FVector(self.x if inside else self.x+1200.,250000.,3050.),bSweep=False,bTeleport=True)
    def start_case(self):
        self.profile=PROFILES[self.index];self.x=250000.+self.index*10000.;transform=ue.FTransform();transform.translation=ue.FVector(self.x,250000.,3000.)
        self.actor=self.statics.call_function('BeginDeferredActorSpawnFromClass',self.world,self.cls,transform,1,None);self.actors.append(self.actor);self.volumes.append(self.actor);ue.set_mixin_profile(self.actor,self.profile);self.actor.set_property('AreaScale',policy.lib('KismetMathLibrary').call_function('MakeVector',20.,20.,4.));self.actor.set_property('TimeRequiredForCapture',1.);self.statics.call_function('FinishSpawningActor',self.actor,transform)
        self.units=[self.unit(i) for i in (0,1)];self.row=dict(profile=self.profile,ready_entries=0,native_rate=None,stages=[]);self.report['pending_case']=self.row;self.enter('volume-ready')
    def snapshot(self):
        points=list(self.scoring.get_property('ControlPoints'));index=points.index(self.actor);timeline=self.actor.get_property('TL_ConvertPoint')
        return dict(owner=int(self.actor.get_property('OwnerTeamID')),teams=list(self.actor.get_property('OverlappingTeams')),pawns=[path(p) for p in self.actor.get_property('OverlappingPawns')],point_owner=int(self.scoring.get_property('ControlPointOwnerTeams')[index]),playing=bool(timeline.call_function('IsPlaying')),reversing=bool(timeline.call_function('IsReversing')),position=float(timeline.call_function('GetPlaybackPosition')),enter_entries=count(self.actor,'EnterAuthority'),exit_entries=count(self.actor,'ExitAuthority'),recompute_entries=count(self.actor,'Recompute'),owning_color=color(self.actor.get_property('OwningTeamColor')),target_color=color(self.actor.get_property('TargetColor')))
    def observe(self):
        require(time.monotonic()-self.phase_started<8.,'native physical overlap/capture stage timeout: '+self.phase)
        if self.phase=='volume-ready':
            if count(self.actor,'Ready')!=1 or not valid(self.actor.get_property('ControlPointGameMode')):return
            self.row['ready_entries']=count(self.actor,'Ready');self.row['native_rate']=float(self.actor.get_property('TL_ConvertPoint').call_function('GetPlayRate'));self.move(0,True);self.enter('one-enter');return
        s=self.snapshot();elapsed=time.monotonic()-self.phase_started
        self.report['pending_native_state']=s
        if self.phase=='one-enter':
            if s['teams']!=[1] or elapsed<.1:return
            self.row['stages'].append(dict(name=self.phase,**s));self.move(1,True);self.enter('mixed')
        elif self.phase=='mixed':
            if len(s['teams'])!=2 or elapsed<.08:return
            self.row['stages'].append(dict(name=self.phase,**s));self.move(1,False);self.enter('capture-one')
        elif self.phase=='capture-one':
            if s['owner']!=1:return
            self.row['stages'].append(dict(name=self.phase,**s));self.move(0,False);self.enter('empty')
        elif self.phase=='empty':
            if s['pawns'] or elapsed<.1:return
            self.row['stages'].append(dict(name=self.phase,**s));self.move(1,True);self.enter('capture-two')
        elif self.phase=='capture-two':
            if s['owner']!=2:return
            self.row['stages'].append(dict(name=self.phase,**s));self.move(1,False);self.enter('final-empty')
        elif self.phase=='final-empty':
            if s['pawns'] or elapsed<.1:return
            self.row['stages'].append(dict(name=self.phase,**s));self.row['final_enter_entries']=count(self.actor,'EnterAuthority');self.row['final_exit_entries']=count(self.actor,'ExitAuthority');self.report['cases'].append(self.row)
            for unit in self.units:
                for key in ('pawn','pc','state'):
                    if not dead(unit[key]):unit[key].actor_destroy()
            ue.clear_mixin_profile(self.actor);self.actor.actor_destroy();self.scoring.set_property('ControlPoints',self.original_points);self.scoring.set_property('ControlPointOwnerTeams',self.original_owners);self.index+=1
            if self.index<len(PROFILES):self.start_case()
            else:self.finish()
    def cleanup(self):
        for a in self.actors:
            if not dead(a):
                if a.is_a(self.cls):ue.clear_mixin_profile(a)
                a.actor_destroy()
        if hasattr(self,'scoring') and valid(self.scoring):self.scoring.set_property('ControlPoints',self.original_points);self.scoring.set_property('ControlPointOwnerTeams',self.original_owners);self.scoring.set_property('TargetScore',self.real_target)
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),source_scoring_arrays_restored=hasattr(self,'scoring') and list(self.scoring.get_property('ControlPoints'))==self.original_points and list(self.scoring.get_property('ControlPointOwnerTeams'))==self.original_owners,original_health_unchanged=self.healths()==self.health_before,
            production_profiles_restored=any(r['target_class']==self.cls and all(len(r['profiles'][p]['functions'])==8 for p in PROFILES) for r in ue.get_registered_mixins()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native point state total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_CONTROL_POINT_STATE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CONTROL_POINT_STATE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPControlPointStateResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
