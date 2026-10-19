"""Real device actors/target meshes, native Timeline and portal Niagara states."""
import atexit
import sys
import time
import traceback
import struct
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead,color,vector
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_world.effect_pad_mixin import valid
from . import traversal_cue_mixin as policy
from .traversal_cue_contract import require,validate,close


def path(obj):return obj.get_path_name() if valid(obj) else None
def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]
def v32(v):return [f32(x) for x in vector(v)]


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,launcher_pairs=[],teleport_pairs=[]);self.sources={};self.devices=[];self.index=0;self.materials={};self.kind='death'
        for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','health_properties_written'):self.report[key]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths()
        self.classes={k:ue.load_class(p) for k,p in policy.CLASSES.items()}
        for label,cls in self.classes.items():
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[label]={n:r['python_class'] for n,r in row['profiles'].items()}
        self.mesh_asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset');self.materials={'death':ue.load_object(ue.find_class('MaterialInterface'),'/Game/Characters/Heroes/Mannequin/Materials/Instances/Manny/MI_Manny_01.MI_Manny_01')}
        self.start_launcher()
    def params(self,causer):
        return policy.lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=.25,RawMagnitude=99.,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(),Normal=ue.FVector(0.,0.,1.),Instigator=self.controller.PlayerState,EffectCauser=causer,SourceObject=None,PhysicalMaterial=None,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def device(self,cls,location,rotation=0.):
        actor=self.world.actor_spawn(ue.load_class(cls));self.actors.append(actor);self.devices.append(actor);actor.call_function('K2_SetActorLocation',NewLocation=ue.FVector(*location),bSweep=False,bTeleport=True);actor.call_function('K2_SetActorRotation',ue.FRotator(0.,rotation,0.),True);return actor
    def cue(self,kind,profile):
        actor=self.world.actor_spawn(self.classes[kind]);self.cues.append(actor);ue.set_mixin_profile(actor,profile);actor.call_function('SetActorHiddenInGame',False);return actor
    def fx_value(self,effect,name,method):
        values=native_outputs('NiagaraComponent',method,effect.call_function(method,name));require(values.get('bIsValid'),'native variable absent: '+name);return values['ReturnValue']
    def start_launcher(self):
        self.duration=(.3,.8,.6,.8)[self.index];self.destroy_target=self.index==3;self.targets=[self.target(True) for _ in range(2)];self.current=[];self.spawned=[];self.pads=[];self.start=self.game_time()
        for profile,t in zip(('BlueprintFallback','Python'),self.targets):
            movement=t['actor'].add_actor_component(ue.find_class('ProjectileMovementComponent'),'UEPTraversalMovement');movement.call_function('SetComponentTickEnabled',False);movement.set_property('Velocity',ue.FVector(111.,-222.,333.))
            pad=self.device(policy.LAUNCHER,(2000.,-1500.,500.));pad.set_property('Light Color',ue.FLinearColor(.15,.65,.45,.9));pad.get_property('DefaultSceneRoot').call_function('SetWorldScale3D',ue.FVector(1.,2.,3.));self.pads.append(pad)
            actor=self.cue('launcher',profile);actor.set_property('MaterialEffectDuration',self.duration);actor.call_function('OnExecute',t['actor'],self.params(pad));self.current.append(actor);values=list(actor.get_property('SpawnedEffects'));self.spawned.append(values);self.effects.extend(values)
        self.row=dict(duration=self.duration,destroy_target=self.destroy_target,burst_entries=[policy.evidence(a)['python_burst']+policy.evidence(a)['fallback_burst'] for a in self.current],spawn_counts=[len(v) for v in self.spawned],natural_samples=0,all_material_and_raw_niagara_values_match=True,paired_clock_and_state_match=True,source_curve_distinction_observed=False,timeline_stopped_after_target_destroy=False)
        self.row['initial_configuration_match']=all(self.launch_config(a,t,p,v) for a,t,p,v in zip(self.current,self.targets,self.pads,self.spawned));self.enter('launcher')
    def launch_config(self,actor,t,pad,values):
        if len(values)!=2:return False
        result=True
        for effect,mesh in zip(values,[t['meshes'][0],t['meshes'][2]]):
            pos=native_outputs('NiagaraComponent','GetVariablePosition',effect.call_function('GetVariablePosition','LaunchPadWorldPosition'))
            if not pos.get('bIsValid'):pos=native_outputs('NiagaraComponent','GetVariableVec3',effect.call_function('GetVariableVec3','LaunchPadWorldPosition'))
            result &= bool(pos.get('bIsValid')) and close(vector(pos['ReturnValue']),vector(pad.get_actor_location())) and effect.call_function('GetAttachParent')==mesh and effect.get_property('bAutoDestroy') is False
            result &= abs(self.fx_value(effect,'LaunchPadScale','GetVariableFloat')-2.)<.0001 and abs(self.fx_value(effect,'Duration','GetVariableFloat')-self.duration)<.0001
            result &= close(vector(self.fx_value(effect,'PawnVelocity','GetVariableVec3')),[111.,-222.,333.]) and close(color(self.fx_value(effect,'LaunchPadColor','GetVariableColor')),color(pad.get_property('Light Color'))) and close(color(self.fx_value(effect,'TeamColor','GetVariableColor')),color(actor.get_property('TeamColor')))
        return bool(result)
    def launch_state(self,actor,t,values):
        raw=policy.evidence(actor)['last_time'];curve=actor.get_property('MaterialEffectCurve').call_function('GetFloatValue',raw) if raw is not None else None
        materials=[]
        if not dead(t['actor']):
            for mesh in t['meshes']:
                material=mesh.call_function('GetMaterial',0);require(material.is_a(ue.find_class('MaterialInstanceDynamic')),'native launch material MID absent');materials.append(float(material.call_function('K2_GetScalarParameterValue','EdgeGlowMagnitude')))
        fx=[float(self.fx_value(e,'LaunchPadGCNLValue','GetVariableFloat')) for e in values if valid(e)]
        done=policy.evidence(actor)['python_clear']+policy.evidence(actor)['fallback_clear']>0
        return dict(raw=raw,curve=float(curve) if curve is not None else None,materials=materials,fx=fx,done=done,position=float(actor.get_property(policy.TIMELINE).call_function('GetPlaybackPosition')))
    def launcher(self):
        elapsed=self.game_time()-self.start
        if self.destroy_target and elapsed>=self.duration*.3 and not self.row['timeline_stopped_after_target_destroy']:
            for t in self.targets:
                if not dead(t['actor']):t['actor'].call_function('K2_DestroyActor')
            self.row['timeline_stopped_after_target_destroy']=True
        states=[self.launch_state(a,t,v) for a,t,v in zip(self.current,self.targets,self.spawned)];self.row['natural_samples']+=1
        self.row['paired_clock_and_state_match'] &= close(states[0],states[1])
        for state in states:
            if state['raw'] is None:continue
            if abs(state['raw']-state['curve'])>.01:self.row['source_curve_distinction_observed']=True
            if not state['done']:
                self.row['all_material_and_raw_niagara_values_match'] &= all(abs(v-state['curve'])<.001 for v in state['materials']) and all(abs(v-state['raw'])<.001 for v in state['fx'])
        done=[policy.evidence(a)['python_clear']+policy.evidence(a)['fallback_clear'] for a in self.current]
        if not all(done):require(elapsed<self.duration+2.,'native launcher Timeline did not clear');return
        self.row.update(clear_entries=done,arrays_cleared=all(not a.get_property('SpawnedEffects') for a in self.current),finish_glow_zero=all(all(abs(v)<.001 for v in s['materials']) for s in states))
        self.enter('launch-drain')
    def launch_drain(self):
        alive=[e for values in self.spawned for e in values if valid(e)]
        if any(e.call_function('IsActive') for e in alive):require(time.monotonic()-self.phase_started<8.,'native launch particles did not drain');return
        self.row['all_effects_naturally_inactive']=True;self.report['launcher_pairs'].append(self.row)
        for actor in self.current:ue.clear_mixin_profile(actor);actor.set_property('MaterialEffectDuration',self.classes['launcher'].get_cdo().get_property('MaterialEffectDuration'));actor.call_function('K2_EndGameplayCue')
        for t in self.targets:
            if not dead(t['actor']):t['actor'].call_function('K2_DestroyActor')
        self.index+=1
        if self.index<4:self.start_launcher()
        else:self.teleports();self.manager_index=0;self.start_manager()
    def teleport_setup(self,with_dest,count):
        entry=self.device(policy.TELEPORTER,(1000.,2000.,300.),35.);destination=self.device(policy.TELEPORTER,(-800.,600.,900.),-70.) if with_dest else None
        entry.set_property('TeleporterDestination',destination);entry.set_property('TeleporterEntered',count);entry.set_property('TeleporterWidth',180.);entry.set_property('TeleporterHeight',320.);entry.set_property('TeleporterPhase',-37.)
        entry.get_property('Niagara').call_function('K2_SetRelativeLocation',NewLocation=ue.FVector(20.,-10.,31.),bSweep=False,bTeleport=True)
        if destination is not None:destination.set_property('TeleporterEntered',count);destination.set_property('TeleporterHeight',510.);destination.set_property('TeleporterPhase',13.)
        return entry,destination
    def teleport_state(self,entry,destination,actor):
        effects=[e for e in actor.get_property('ExitParticles') if valid(e)]
        return dict(entry_count=int(entry.get_property('TeleporterEntered')),destination_count=int(destination.get_property('TeleporterEntered')) if destination else None,
            entry_system_count=int(self.fx_value(entry.get_property('Niagara'),'SystemEntered','GetVariableInt')),destination_system_count=int(self.fx_value(destination.get_property('Niagara'),'SystemEntered','GetVariableInt')) if destination else None,
            entry_direction=float(self.fx_value(entry.get_property('Niagara'),'UseDirection','GetVariableFloat')),destination_direction=float(self.fx_value(destination.get_property('Niagara'),'UseDirection','GetVariableFloat')) if destination else None,
            positions=[vector(self.fx_value(e,'TeleporterPosition','GetVariableVec3')) for e in effects] if destination else [],count=len(actor.get_property('ExitParticles')))
    def teleports(self):
        math=policy.lib('KismetMathLibrary')
        for with_dest,count,bursts in ((True,0,1),(True,999999,1),(True,-2,1),(True,2147483647,1),(False,7,1),(True,3,2)):
            states=[];entries=[];checks=[];counts=[]
            for profile in ('BlueprintFallback','Python'):
                t=self.target(True);entry,destination=self.teleport_setup(with_dest,count);actor=self.cue('teleporter',profile);before=self.niagaras();expected=count
                for _ in range(bursts):actor.call_function('OnExecute',t['actor'],self.params(entry));expected=math.call_function('Percent_IntInt',math.call_function('Add_IntInt',expected,1),1000000)
                after=self.niagaras();new=[e for key,e in after.items() if key not in before];self.effects.extend(new);state=self.teleport_state(entry,destination,actor);states.append(state);entries.append(policy.evidence(actor)['python_burst']+policy.evidence(actor)['fallback_burst']);counts.append(len(actor.get_property('ExitParticles')))
                checks.append(self.teleport_parameters(t,entry,destination,new,actor) and state['entry_count']==state['entry_system_count']==expected and (state['destination_count']==state['destination_system_count']==expected if destination else True) and abs(state['entry_direction']-1.)<.001 and (abs(state['destination_direction']-f32(-.8))<.001 if destination else True))
                actor.call_function('K2_EndGameplayCue');t['actor'].call_function('K2_DestroyActor')
            self.report['teleport_pairs'].append(dict(with_destination=with_dest,initial_count=count,bursts=bursts,original=states[0],python=states[1],burst_entries=entries,all_native_parameters_match_source=all(checks),native_exit_particle_count=counts[0],entry_count_matches_native_int32=all(checks),destination_count_and_direction_match=all(checks)))
        self.report['wrong_causer_preserves_partial_assignment']=self.wrong_causers()
    def niagaras(self):return {e.get_path_name():e for e in ue.tobject_iterator(ue.find_class('NiagaraComponent')) if valid(e)}
    def teleport_parameters(self,t,entry,destination,effects,actor):
        flash=[e for e in effects if path(e.get_property('Asset'))==policy.ENTER];exits=list(actor.get_property('ExitParticles'));ok=len(flash)==len(exits)
        origin=entry.get_property('Niagara').call_function('K2_GetComponentLocation');local=policy.center(entry)
        for effect in flash:
            ok &= close(vector(effect.call_function('K2_GetComponentLocation')),vector(origin)) and close(vector(self.fx_value(effect,'TeleporterPosition','GetVariableVec3')),v32(local)) and close(vector(self.fx_value(effect,'TeleporterPlaneDirection','GetVariableVec3')),v32(entry.call_function('GetActorForwardVector')))
            mesh_position=t['meshes'][0].call_function('K2_GetComponentLocation');ok &= close(vector(self.fx_value(effect,'SkeletonPositionOffset','GetVariableVec3')),[0.,0.,f32(mesh_position.z-origin.z)])
            ok &= abs(self.fx_value(effect,'PortalWidth','GetVariableFloat')-180.)<.001 and abs(self.fx_value(effect,'PortalHeight','GetVariableFloat')-320.)<.001
        if destination:
            expected=policy.lib('KismetMathLibrary').call_function('Add_VectorVector',destination.get_actor_location(),policy.center(destination))
            ok &= all(close(vector(self.fx_value(e,'TeleporterPosition','GetVariableVec3')),v32(expected)) for e in exits if valid(e))
        return bool(ok)
    def wrong_causers(self):
        result=True;wrong=self.own();t=self.target(False)
        for kind in ('launcher','teleporter'):
            for profile in ('BlueprintFallback','Python'):
                actor=self.cue(kind,profile);actor.call_function('OnExecute',t['actor'],self.params(wrong));result &= actor.get_property('TargetActor')==t['actor'] and not actor.get_property('SpawnedEffects' if kind=='launcher' else 'ExitParticles');actor.call_function('K2_EndGameplayCue')
        return bool(result)
    def start_manager(self):
        self.manager_kind=('launcher','teleporter')[self.manager_index];self.manager_target=self.target(True)
        if self.manager_kind=='launcher':device=self.device(policy.LAUNCHER,(1700.,300.,800.));move=self.manager_target['actor'].add_actor_component(ue.find_class('ProjectileMovementComponent'),'UEPManagerMovement');move.call_function('SetComponentTickEnabled',False)
        else:device,_=self.teleport_setup(True,0)
        cls=self.classes[self.manager_kind];self.manager_before={a.get_path_name():policy.evidence(a)['python_burst'] for a in self.world.all_actors() if valid(a) and a.is_a(cls)}
        tag=cls.get_cdo().get_property('GameplayCueTag');policy.lib('GameplayCueFunctionLibrary').call_function('ExecuteGameplayCueOnActor',self.manager_target['actor'],tag,self.params(device));self.enter('manager')
    def manager(self):
        require(time.monotonic()-self.phase_started<15.,'real traversal manager did not execute')
        found=[a for a in self.world.all_actors() if valid(a) and a.is_a(self.classes[self.manager_kind]) and a.call_function('GetOwner')==self.manager_target['actor']]
        if not found:return
        actor,=found;self.cues.append(actor);field='SpawnedEffects' if self.manager_kind=='launcher' else 'ExitParticles';self.effects.extend(e for e in actor.get_property(field) if valid(e))
        self.report['real_default_python_manager_tags']=self.report.get('real_default_python_manager_tags',0)+(policy.evidence(actor)['python_burst']-self.manager_before.get(actor.get_path_name(),0)==1)
        actor.call_function('K2_EndGameplayCue');self.manager_index+=1
        if self.manager_index==2:self.finish()
        else:self.start_manager()
    def cleanup(self):
        for effect in self.effects:
            if valid(effect):effect.call_function('K2_DestroyComponent',effect.call_function('GetOwner'))
        for actor in self.cues:
            if not dead(actor):ue.clear_mixin_profile(actor);actor.call_function('K2_EndGameplayCue')
        for actor in self.actors:
            if not dead(actor):actor.call_function('K2_DestroyActor')
        self.report['owned_targets_and_devices_destroyed']=all(dead(a) for a in self.actors);self.report['owned_effects_removed']=all(not valid(e) for e in self.effects);self.report['original_health_unchanged']=hasattr(self,'health_before') and self.healths()==self.health_before
        self.report['production_profiles_restored']=all(any(r['target_class']==self.classes[k] and all(r['profiles'][p]['python_class'] is cls for p,cls in methods.items()) for r in ue.get_registered_mixins()) for k,methods in self.sources.items())
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'traversal native timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='launcher':self.launcher()
            elif self.phase=='launch-drain':self.launch_drain()
            elif self.phase=='manager':self.manager()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_TRAVERSAL_CUE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_TRAVERSAL_CUE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPTraversalCueResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
