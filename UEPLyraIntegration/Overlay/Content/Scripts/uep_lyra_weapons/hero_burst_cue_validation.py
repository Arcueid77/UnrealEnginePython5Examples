"""Actual native paired Timeline updates, owned meshes/materials and Cue manager."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_world.effect_pad_mixin import valid
from . import hero_burst_cue_mixin as policy
from .hero_burst_cue_contract import require,validate,close


def dead(actor):return not valid(actor) or actor.call_function('IsActorBeingDestroyed')
def color(c):return [float(c.r),float(c.g),float(c.b),float(c.a)]
def vector(v):return [float(v.x),float(v.y),float(v.z)]


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.cues=[];self.effects=[];self.sources={};self.index=0
        self.plan=[(kind,duration,teamed,False) for kind in ('dash','death') for duration in (.3,.8) for teamed in (False,True)]+[('dash',.6,True,True),('death',.6,True,True)]
        self.report=dict(status='running',error=None,pairs=[],manager_cases=[])
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','native_timer_properties_written','health_properties_written','identical_particle_lifetimes_claimed'):self.report[k]=False
    def own(self):
        actor=self.world.actor_spawn(ue.find_class('Actor'));actor.call_function('SetReplicates',False);self.actors.append(actor);return actor
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths()
        self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        for name,cls in self.classes.items():
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[name]={p:r['python_class'] for p,r in row['profiles'].items()}
        self.mesh_asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset')
        base='/Game/Characters/Heroes/Mannequin/Materials/Instances/Manny/'
        self.materials={kind:ue.load_object(ue.find_class('MaterialInterface'),base+name+'.'+name) for kind,name in (('dash','MI_Manny_01_SMEAR'),('death','MI_Manny_01'))};self.start_pair()
    def mesh(self,owner,name,ignored=False):
        mesh=owner.add_actor_component(ue.find_class('SkeletalMeshComponent'),name,owner.get_property('RootComponent'))
        mesh.call_function('SetSkeletalMeshAsset',self.mesh_asset);mesh.call_function('SetMaterial',0,self.materials[self.kind])
        if ignored:mesh.set_property('ComponentTags',['IGNORE'])
        return mesh
    def target(self,teamed):
        actor=self.own();root=actor.add_actor_root_component(ue.find_class('SceneComponent'),'UEPHeroBurstRoot')
        if teamed:actor.set_property('Instigator',self.pawn)
        center=self.pawn.get_actor_location();actor.call_function('K2_SetActorLocation',NewLocation=ue.FVector(center.x+300.,center.y,center.z),bSweep=False,bTeleport=True)
        main=self.mesh(actor,'UEPBody');ignored=self.mesh(actor,'UEPIgnored',True)
        child_component=actor.add_actor_component(ue.find_class('ChildActorComponent'),'UEPHeroBurstChild',root);child_component.call_function('SetChildActorClass',ue.find_class('StaticMeshActor'),None)
        child=child_component.get_property('ChildActor');require(valid(child),'native child actor fixture absent')
        if not valid(child.get_property('RootComponent')):child.add_actor_root_component(ue.find_class('SceneComponent'),'UEPChildRoot')
        child_mesh=self.mesh(child,'UEPChildBody');root_decal=actor.add_actor_component(ue.find_class('DecalComponent'),'UEPRootDecal',root);child_decal=child.add_actor_component(ue.find_class('DecalComponent'),'UEPChildDecal',child.get_property('RootComponent'))
        return dict(actor=actor,meshes=[main,ignored,child_mesh],root_decal=root_decal,child_decal=child_decal)
    def params(self,duration,kill):
        return policy.lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=duration,RawMagnitude=77.25,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),
            AggregatedSourceTags=GameplayTagContainer(GameplayTags=[GameplayTag(TagName='Gameplay.Damage.FellOutOfWorld')] if kill else []),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(),Normal=ue.FVector(.25,-.5,.75),Instigator=self.controller.PlayerState,EffectCauser=None,SourceObject=None,PhysicalMaterial=None,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def start_pair(self):
        self.kind,self.duration,self.teamed,self.switch=self.plan[self.index];self.targets=[self.target(self.teamed) for _ in range(2)];self.current=[];self.spawned=[];self.start=self.game_time()
        for profile,target in zip(('BlueprintFallback','Python'),self.targets):
            actor=self.world.actor_spawn(self.classes[self.kind]);self.cues.append(actor);ue.set_mixin_profile(actor,profile);actor.call_function('SetActorHiddenInGame',False)
            if self.kind=='death':actor.set_property('SpawningDuration',self.duration)
            actor.call_function('OnExecute',target['actor'],self.params(self.duration if self.kind=='dash' else 9.,self.teamed))
            values=list(actor.get_property('SpawnedEffects'));self.effects.extend(values);self.spawned.append(values);self.current.append(actor)
        self.row=dict(kind=self.kind,duration=self.duration,teamed=self.teamed,switch=self.switch,initial_burst_entries=[sum(policy.evidence(a)[k] for k in ('python_burst','fallback_burst')) for a in self.current],spawn_counts=[len(v) for v in self.spawned],natural_samples=0,all_sample_pairs_match=True,all_samples_match_native_curve_parameters=True,native_playback_positions_match=True,profile_switch_observed=False)
        self.report['fixture_diagnostics']=dict(kind=self.kind,source_mesh_asset=self.mesh_asset.get_path_name() if valid(self.mesh_asset) else None,source_material=self.materials[self.kind].get_path_name(),burst_entries=self.row['initial_burst_entries'],spawn_counts=self.row['spawn_counts'],
            targets=[dict(native_found_meshes=len(policy.components(t['actor'],'SkeletalMeshComponent',True)),meshes=[dict(owner=m.call_function('GetOwner').get_path_name(),registered=bool(m.component_is_registered()),material_slots=int(m.call_function('GetNumMaterials')),material=m.call_function('GetMaterial',0).get_path_name() if valid(m.call_function('GetMaterial',0)) else None,material_class=m.call_function('GetMaterial',0).get_class().get_path_name() if valid(m.call_function('GetMaterial',0)) else None) for m in t['meshes']]) for t in self.targets])
        start_states=[self.state(a,t,values) for a,t,values in zip(self.current,self.targets,self.spawned)]
        self.row['native_start_values_match']=close(start_states[0],start_states[1]);self.row['native_system_configuration_matches']=all(self.configuration(a,t,v) for a,t,v in zip(self.current,self.targets,self.spawned));self.enter('pair')
    def variable(self,effect,name,method):
        fields=native_outputs('NiagaraComponent',method,effect.call_function(method,name));require(fields.get('bIsValid'),'actual native Niagara variable missing: '+name);return fields['ReturnValue']
    def material_state(self,target):
        values=[]
        scalar=('DashDeform',) if self.kind=='dash' else ('KillAge','EdgeGlowMagnitude')
        vectors=('DashDirection',) if self.kind=='dash' else ('KillEdgeColor','EdgeGlowColor')
        for mesh in target['meshes']:
            mat=mesh.call_function('GetMaterial',0);require(valid(mat) and mat.is_a(ue.find_class('MaterialInstanceDynamic')),'native shared-mesh setter did not create actual MID')
            values.append(dict(scalars=[float(mat.call_function('K2_GetScalarParameterValue',n)) for n in scalar],vectors=[color(mat.call_function('K2_GetVectorParameterValue',n)) for n in vectors]))
        return values
    def state(self,actor,target,values):
        return dict(team_color=color(actor.get_property('TeamColor')),team_asset=actor.get_property('TeamDisplayAsset').get_path_name() if valid(actor.get_property('TeamDisplayAsset')) else None,
            materials=self.material_state(target),fx=[dict(scalar=float(self.variable(e,'LifetimeMultiplier' if self.kind=='dash' else 'KillTimeline','GetVariableFloat'))) for e in values],array_count=len(actor.get_property('SpawnedEffects')))
    def configuration(self,actor,target,values):
        if len(values)!=2:return False
        expected=[target['meshes'][0],target['meshes'][2]];ok=True
        for effect,mesh in zip(values,expected):
            ok &= effect.call_function('GetAttachParent')==mesh and effect.get_property('bAutoDestroy') is False
            value=self.variable(effect,'DashDuration' if self.kind=='dash' else 'KillTimeLength','GetVariableFloat');ok &= abs(float(value)-(self.duration*2. if self.kind=='dash' else self.duration))<.0001
            if self.kind=='dash':ok &= all(abs(a-b)<.0001 for a,b in zip(vector(self.variable(effect,'DashDirection','GetVariableVec3')),[.25,-.5,.75]))
        return bool(ok)
    def pair(self):
        elapsed=self.game_time()-self.start
        if self.switch and not self.row['profile_switch_observed'] and elapsed>=self.duration*.25:
            ue.set_mixin_profile(self.current[0],'Python');ue.set_mixin_profile(self.current[1],'BlueprintFallback');self.row['profile_switch_observed']=True
        states=[self.state(a,t,v) for a,t,v in zip(self.current,self.targets,self.spawned)]
        positions=[float(a.get_property(policy.TIMELINES[self.kind]).call_function('GetPlaybackPosition')) for a in self.current]
        self.row['native_playback_positions_match'] &= abs(positions[0]-positions[1])<.0001
        finished=[sum(policy.evidence(a)[k] for k in ('python_finished','fallback_finished')) for a in self.current]
        self.row['natural_samples']+=1;self.row['all_sample_pairs_match'] &= close(states[0],states[1])
        for actor,state in zip(self.current,states):
            curves=policy.evidence(actor)['last_curves']
            if curves is None:continue
            a,b=curves;done=sum(policy.evidence(actor)[k] for k in ('python_finished','fallback_finished'))>0
            for mat in state['materials']:
                self.row['all_samples_match_native_curve_parameters'] &= abs(mat['scalars'][0]-a)<.0001
                if self.kind=='death':self.row['all_samples_match_native_curve_parameters'] &= abs(mat['scalars'][1]-(0. if done else b*20.))<.0001
            if not done:
                for effect in state['fx']:self.row['all_samples_match_native_curve_parameters'] &= abs(effect['scalar']-(b if self.kind=='dash' else a))<.0001
        if not all(finished):require(elapsed<self.duration+2.,'native Timeline did not finish');return
        self.row.update(finished_entries=finished,finish_profiles=[str(ue.get_mixin_profile(a)) for a in self.current],effect_arrays_cleared=all(s['array_count']==0 for s in states),all_effects_deactivated=all(not e.call_function('IsActive') for values in self.spawned for e in values),completed_after_configured_duration=elapsed>=self.duration-.05)
        if self.kind=='death':self.row.update(root_decals_destroyed_child_decals_retained=all(not valid(t['root_decal']) and valid(t['child_decal']) for t in self.targets),final_edge_glow_zero=all(abs(m['scalars'][1])<.0001 for s in states for m in s['materials']))
        if not self.row['all_effects_deactivated']:self.enter('drain');return
        self.end_pair()
    def drain(self):
        flags=[[bool(e.call_function('IsActive')) for e in values] for values in self.spawned]
        self.row.setdefault('native_particle_drain_observations',[]).append(flags)
        if any(any(v) for v in flags):require(time.monotonic()-self.phase_started<8.,'native deactivated Niagara systems did not naturally drain');return
        self.row['all_effects_deactivated']=True;self.row['native_particle_drain_waited']=True;self.end_pair()
    def end_pair(self):
        self.report['pairs'].append(self.row)
        for actor in self.current:
            ue.clear_mixin_profile(actor)
            if self.kind=='death':actor.set_property('SpawningDuration',self.classes['death'].get_cdo().get_property('SpawningDuration'))
            actor.call_function('K2_EndGameplayCue')
        for target in self.targets:target['actor'].call_function('K2_DestroyActor')
        self.index+=1
        if self.index<len(self.plan):self.start_pair()
        else:self.manager_index=0;self.start_manager()
    def start_manager(self):
        self.kind=('dash','death')[self.manager_index];self.manager_target=self.target(True);self.manager_before={a.get_path_name():policy.evidence(a)['python_burst'] for a in self.world.all_actors() if valid(a) and a.is_a(self.classes[self.kind])}
        self.tag=self.classes[self.kind].get_cdo().get_property('GameplayCueTag');params=self.params(.4,False)
        policy.lib('GameplayCueFunctionLibrary').call_function('ExecuteGameplayCueOnActor',self.manager_target['actor'],self.tag,params);self.enter('manager')
    def manager(self):
        require(time.monotonic()-self.phase_started<15.,'real hero burst manager did not execute')
        actors=[a for a in self.world.all_actors() if valid(a) and a.is_a(self.classes[self.kind]) and a.call_function('GetOwner')==self.manager_target['actor']]
        if not actors:return
        actor,=actors;self.cues.append(actor);values=list(actor.get_property('SpawnedEffects'));self.effects.extend(values)
        self.report['manager_cases'].append(dict(kind=self.kind,selected_profile=str(ue.get_mixin_profile(actor)),default_python_burst_entry=policy.evidence(actor)['python_burst']-self.manager_before.get(actor.get_path_name(),0)==1,native_timeline_playing=bool(actor.get_property(policy.TIMELINES[self.kind]).call_function('IsPlaying')),effects_started=len(values)==2))
        actor.call_function('K2_EndGameplayCue');self.manager_target['actor'].call_function('K2_DestroyActor');self.manager_index+=1
        if self.manager_index==2:self.finish()
        else:self.start_manager()
    def cleanup(self):
        for effect in self.effects:
            if valid(effect):effect.call_function('K2_DestroyComponent',effect.call_function('GetOwner'))
        for actor in self.cues:
            if not dead(actor):ue.clear_mixin_profile(actor);actor.call_function('K2_EndGameplayCue')
        for actor in self.actors:
            if not dead(actor):actor.call_function('K2_DestroyActor')
        self.report['owned_actors_destroyed']=all(dead(a) for a in self.actors);self.report['owned_effects_removed']=all(not valid(e) for e in self.effects)
        self.report['production_profiles_restored']=all(any(r['target_class']==self.classes[k] and all(r['profiles'][n]['python_class'] is source and len(r['profiles'][n]['functions'])==3 for n,source in v.items()) for r in ue.get_registered_mixins()) for k,v in self.sources.items())
        self.report['original_health_unchanged']=hasattr(self,'health_before') and self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native hero burst total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='pair':self.pair()
            elif self.phase=='drain':self.drain()
            elif self.phase=='manager':self.manager()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_HERO_BURST_CUE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_HERO_BURST_CUE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroBurstCueResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
