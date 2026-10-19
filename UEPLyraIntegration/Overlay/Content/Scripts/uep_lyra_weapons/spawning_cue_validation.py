"""Owned native characters, real team/parts events and natural Spawn Timeline."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import LyraCharacterPart,GameplayCueNotify_SpawnResult
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead,color,vector
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from . import spawning_cue_mixin as policy
from .spawning_cue_contract import PLAN,require,validate,close


def count(actor,name):return sum(policy.evidence(actor)[p+'_'+name] for p in ('python','fallback'))
def path(value):return value.get_path_name() if valid(value) else None


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,pairs=[],manager_cases=[]);self.plan=PLAN;self.index=0;self.sources={};self.watchers=[];self.current=[];self.removed=False
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','python_timeline_clock_added','timeline_callbacks_replayed','parts_delegate_broadcast_by_fixture','team_properties_written','health_properties_written'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths()
        self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={p:r['python_class'] for p,r in row['profiles'].items()}
        self.report['source_default_template_count']=len(self.cls.get_cdo().get_property('NiagaraSystemTemplates'))
        team_system=policy.lib('SubsystemBlueprintLibrary').call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
        self.team_numbers=sorted(native_outputs('LyraTeamSubsystem','GetTeamIDs',team_system.call_function('GetTeamIDs'))['ReturnValue']);require(len(self.team_numbers)>=2,'two actual native teams required');self.report['native_team_ids']=self.team_numbers
        self.report['native_team_change_entry']='Owned LyraPlayerController/CheatManager -> LyraTeamCheats.SetTeam -> native team subsystem and possession propagation'
        self.mesh_asset=self.pawn.get_property('Mesh').call_function('GetSkeletalMeshAsset');self.kind='death';self.materials={'death':ue.load_object(ue.find_class('MaterialInterface'),'/Game/Characters/Heroes/Mannequin/Materials/Instances/Manny/MI_Manny_01.MI_Manny_01')}
        self.system=ue.load_object(ue.find_class('NiagaraSystem'),'/Game/Effects/Particles/Environmental/NS_CharacterSpawnIn.NS_CharacterSpawnIn');self.start_pair()
    def make_target(self,parts,team):
        actor=self.world.actor_spawn(ue.find_class('LyraCharacter'),ue.FVector(10000.,10000.,3000.));self.actors.append(actor);actor.call_function('SetReplicates',False);actor.call_function('SetActorEnableCollision',False)
        actor.call_function('SetActorTickEnabled',False);actor.get_property('CharacterMovement').call_function('SetComponentTickEnabled',False)
        mesh=actor.get_property('Mesh');mesh.call_function('SetSkeletalMeshAsset',self.mesh_asset);mesh.call_function('SetMaterial',0,self.materials['death'])
        ignored=self.mesh(actor,'UEPSpawnIgnored',True)
        child_component=actor.add_actor_component(ue.find_class('ChildActorComponent'),'UEPSpawnChild',actor.get_property('RootComponent'));child_component.call_function('SetChildActorClass',ue.find_class('StaticMeshActor'),None);child=child_component.get_property('ChildActor');require(valid(child),'spawn child absent');child_mesh=self.mesh(child,'UEPSpawnChildMesh')
        controller=self.world.actor_spawn(ue.find_class('LyraPlayerController'));self.actors.append(controller);self.actors.append(controller.get_property('PlayerState'))
        controller.call_function('Possess',actor);manager=ue.new_object(ue.find_class('CheatManager'),controller);cheats=ue.new_object(ue.find_class('LyraTeamCheats'),manager)
        target=dict(actor=actor,controller=controller,manager=manager,cheats=cheats,meshes=[mesh,ignored,child_mesh],parts=actor.add_actor_component(ue.find_class('LyraPawnComponent_CharacterParts'),'UEPSpawnParts') if parts else None,handles=[],child_meshes=[])
        if team!=-1:self.owned_team(target,team)
        return target
    def owned_team(self,target,number):
        number=self.team_numbers[number];target['cheats'].call_function('SetTeam',number)
        fields=native_outputs('LyraTeamStatics','FindTeamFromObject',policy.lib('LyraTeamStatics').call_function('FindTeamFromObject',target['actor'],False))
        require(int(fields['TeamId'])==number,'owned native development team transition rejected')
    def start_pair(self):
        self.name,self.duration,with_parts,self.initial_team,self.switch,self.late=self.plan[self.index];self.targets=[self.make_target(with_parts,self.initial_team) for _ in range(2)];self.current=[];self.removed=False;self.actions=0;self.start=self.game_time()
        self.row=dict(name=self.name,duration=self.duration,late_parts_after_removal=self.late,switched=False,natural_samples=0,all_samples_match=True,clocks_match=True,native_callbacks_match=True)
        self.report['pending_pair']=self.row
        for profile,target in zip(('BlueprintFallback','Python'),self.targets):
            cue=self.world.actor_spawn(self.cls);self.cues.append(cue);self.current.append(cue);ue.set_mixin_profile(cue,profile);cue.set_property('NiagaraSystemTemplates',[self.system]);cue.set_property('SpawningDuration',self.duration)
            cue.call_function('OnApplication',target['actor'],self.params(self.duration,False),GameplayCueNotify_SpawnResult())
            watcher=cue.get_property('TeamColorWatcherHandle');self.watchers.append(watcher)
        self.row.update(initial_application_entries=[count(c,'application') for c in self.current],initial_team_entries=[count(c,'team') for c in self.current],initial_fx_counts=[len(c.get_property('SpawnedEffects')) for c in self.current],watchers_native_active=all(valid(w) and w.call_function('IsActive') for w in self.watchers[-2:]))
        self.row['initial_system_configuration']=all(len(c.get_property('SpawnedEffectMap'))==2 and all(e.call_function('GetAttachParent')==m and e.get_property('Asset')==self.system and not e.get_property('bAutoDestroy') and abs(float(self.variable(e,'SpawnTImeLength','GetVariableFloat'))-self.duration)<.0001 for e,m in zip(c.get_property('SpawnedEffects'),(t['meshes'][0],t['meshes'][2]))) for c,t in zip(self.current,self.targets))
        self.effects.extend(e for c in self.current for e in c.get_property('SpawnedEffects') if valid(e));self.enter('pair')
    def variable(self,effect,name,method):
        fields=native_outputs('NiagaraComponent',method,effect.call_function(method,name));require(fields.get('bIsValid'),'native spawning variable absent: '+name);return fields['ReturnValue']
    def state(self,cue,target):
        fx=list(cue.get_property('SpawnedEffects'));materials=[]
        for mesh in target['meshes']+target['child_meshes']:
            if not valid(mesh):continue
            material=mesh.call_function('GetMaterial',0);require(valid(material) and material.is_a(ue.find_class('MaterialInstanceDynamic')),'Spawn source did not produce actual MID')
            materials.append(dict(slots=int(mesh.call_function('GetNumMaterials')),age=float(material.call_function('K2_GetScalarParameterValue','SpawnAge')),edge=color(material.call_function('K2_GetVectorParameterValue','KillEdgeColor'))))
        return dict(team=color(cue.get_property('TeamColor')),time=float(cue.get_property('Spawn Linear Time')),fx_count=len(fx),map_count=len(cue.get_property('SpawnedEffectMap')),materials=materials,
            fx=[dict(body=vector(self.variable(e,'BodyColor','GetVariableVec3')),duration=float(self.variable(e,'SpawnTImeLength','GetVariableFloat')),timeline=float(self.variable(e,'SpawnTimeline','GetVariableFloat'))) for e in fx if valid(e)])
    def change_team(self,restore=False,record=True):
        before=[count(c,'team') for c in self.current]
        destination=(0 if self.initial_team!=1 else 1) if restore else (1 if self.initial_team!=1 else 0)
        for target in self.targets:self.owned_team(target,destination)
        delta=[count(c,'team')-b for c,b in zip(self.current,before)]
        if record:self.row['team_change_callback_deltas']=delta
    def add_parts(self):
        before=[count(c,'parts') for c in self.current]
        for target in self.targets:
            component=target['parts'];handle=component.call_function('AddCharacterPart',LyraCharacterPart(PartClass=ue.find_class('StaticMeshActor'))).clone();target['handles'].append(handle)
            actors=component.call_function('GetCharacterPartActors');child=actors[-1];target['child_meshes'].append(self.mesh(child,'UEPSpawnAddedMesh'))
            target['handles'].append(component.call_function('AddCharacterPart',LyraCharacterPart(PartClass=ue.find_class('Actor'))).clone())
        self.row['part_add_callback_deltas']=[count(c,'parts')-b for c,b in zip(self.current,before)]
        self.effects.extend(e for c in self.current for e in c.get_property('SpawnedEffects') if valid(e) and e not in self.effects)
        counts=[len(c.get_property('SpawnedEffects')) for c in self.current]
        for cue in self.current:cue.call_function('SpawnEffectForEachMeshComponent')
        self.row['repeat_discovery_does_not_duplicate_effects']=[len(c.get_property('SpawnedEffects')) for c in self.current]==counts
    def remove(self):
        self.removal_counts=[{n:count(c,n) for n in ('team','parts')} for c in self.current]
        retained=[(c.get_property('TeamColorWatcherHandle'),c.get_property('PawnCosmeticSystem')) for c in self.current]
        clocks=[bool(c.get_property('SpawnTimeline').call_function('IsPlaying')) for c in self.current]
        for cue,target in zip(self.current,self.targets):cue.call_function('OnRemoval',target['actor'],self.params(self.duration,False),GameplayCueNotify_SpawnResult())
        self.row['removal_cleared_caches']=all(not c.get_property('SpawnedEffects') and not c.get_property('SpawnedEffectMap') for c in self.current)
        self.row['removal_cancelled_watchers']=all(not valid(w) or not w.call_function('IsActive') for w in self.watchers[-2:])
        self.row['removal_retained_source_handles']=all(c.get_property('TeamColorWatcherHandle')==w and c.get_property('PawnCosmeticSystem')==p for c,(w,p) in zip(self.current,retained))
        self.row['removal_did_not_stop_native_clock']=[bool(c.get_property('SpawnTimeline').call_function('IsPlaying')) for c in self.current]==clocks
        self.row.setdefault('removal_observations',[]).append({k:self.row[k] for k in ('removal_cleared_caches','removal_cancelled_watchers','removal_retained_source_handles','removal_did_not_stop_native_clock')})
        self.removed=True
    def pair(self):
        elapsed=self.game_time()-self.start
        if self.switch and not self.row['switched'] and elapsed>.03:
            ue.set_mixin_profile(self.current[0],'Python');ue.set_mixin_profile(self.current[1],'BlueprintFallback');self.row['switched']=True
        if self.actions==0 and elapsed>.05:
            if self.late:self.remove()
            for target in self.targets:
                if target['parts'] is None:target['parts']=target['actor'].add_actor_component(ue.find_class('LyraPawnComponent_CharacterParts'),'UEPSpawnLateParts')
            self.actions=1;return
        if self.actions==1 and elapsed>.12:
            self.change_team();self.add_parts();self.actions=2;return
        states=[self.state(c,t) for c,t in zip(self.current,self.targets)]
        self.row['natural_samples']+=1;self.row['all_samples_match'] &= close(states[0],states[1])
        positions=[float(c.get_property('SpawnTimeline').call_function('GetPlaybackPosition')) for c in self.current];self.row['clocks_match'] &= abs(positions[0]-positions[1])<.0001
        for c,s in zip(self.current,states):
            value=policy.evidence(c)['last_time']
            if value is not None:self.row['all_samples_match'] &= abs(s['time']-value)<.0001 and all(abs(m['age']-value)<.0001 for m in s['materials'] if m['slots']>0) and all(abs(e['timeline']-value)<.0001 for e in s['fx'])
        if elapsed<self.duration+.08:return
        require(self.actions==2,'native action sequence absent');self.row['before_final_removal']=states
        self.row['late_retry_rebound_after_removal']=all(c.get_property('PawnCosmeticSystem')==t['parts'] and count(c,'parts')-b['parts']==2 for c,t,b in zip(self.current,self.targets,self.removal_counts)) if self.late else False
        self.row['native_part_callback_entries_match']=[count(c,'parts') for c in self.current];self.row['native_team_callback_entries_match']=[count(c,'team') for c in self.current]
        self.removed=False;self.remove()
        before=[count(c,'parts') for c in self.current]
        for target in self.targets:
            for handle in target['handles']:target['parts'].call_function('RemoveCharacterPart',handle)
        self.row['native_parts_unbound_after_removal']=all(count(c,'parts')==b for c,b in zip(self.current,before));self.change_team(True,False)
        self.row['native_team_unbound_after_removal']=all(count(c,'team')==b['team'] for c,b in zip(self.current,self.removal_counts))
        self.row['source_arrays_and_map_empty']=all(not c.get_property('SpawnedEffects') and not c.get_property('SpawnedEffectMap') for c in self.current);self.report['pairs'].append(self.row)
        for cue in self.current:ue.clear_mixin_profile(cue);cue.set_property('NiagaraSystemTemplates',list(self.cls.get_cdo().get_property('NiagaraSystemTemplates')));cue.set_property('SpawningDuration',self.cls.get_cdo().get_property('SpawningDuration'));cue.call_function('K2_EndGameplayCue')
        for target in self.targets:target['actor'].call_function('K2_DestroyActor')
        self.index+=1
        if self.index<len(self.plan):self.start_pair()
        else:self.start_manager()
    def start_manager(self):
        self.manager_target=self.make_target(True,0);self.manager_before={c.get_path_name():count(c,'application') for c in ue.tobject_iterator(self.cls) if valid(c)};self.tag=self.cls.get_cdo().get_property('GameplayCueTag')
        policy.lib('GameplayCueFunctionLibrary').call_function('AddGameplayCueOnActor',self.manager_target['actor'],self.tag,self.params(.3,False));self.enter('manager')
    def manager(self):
        require(time.monotonic()-self.phase_started<15.,'real spawning manager did not apply')
        found=[c for c in self.world.all_actors() if valid(c) and c.is_a(self.cls) and c.call_function('GetOwner')==self.manager_target['actor']]
        if not found:return
        cue,=found;self.cues.append(cue);watcher=cue.get_property('TeamColorWatcherHandle');self.watchers.append(watcher);self.effects.extend(e for e in cue.get_property('SpawnedEffects') if valid(e));self.manager_cue=cue
        self.manager_row=dict(default_profile=str(ue.get_mixin_profile(cue)),application_entries=count(cue,'application')-self.manager_before.get(cue.get_path_name(),0),native_watcher_active=bool(valid(watcher) and watcher.call_function('IsActive')),python_application=policy.evidence(cue)['python_application']>0)
        policy.lib('GameplayCueFunctionLibrary').call_function('RemoveGameplayCueOnActor',self.manager_target['actor'],self.tag,self.params(.3,False));self.enter('manager-removed')
    def manager_removed(self):
        watcher=self.manager_cue.get_property('TeamColorWatcherHandle');self.manager_row.update(watcher_cancelled=not valid(watcher) or not watcher.call_function('IsActive'),cache_empty=not self.manager_cue.get_property('SpawnedEffects') and not self.manager_cue.get_property('SpawnedEffectMap'))
        self.report['manager_cases'].append(self.manager_row);self.finish()
    def cleanup(self):
        for cue in self.cues:
            if not dead(cue):
                watcher=cue.get_property('TeamColorWatcherHandle')
                if valid(watcher) and watcher.call_function('IsActive'):watcher.call_function('Cancel')
                cue.call_function('StopWatchingForParts');ue.clear_mixin_profile(cue);cue.call_function('K2_EndGameplayCue')
        for effect in self.effects:
            if valid(effect):effect.call_function('K2_DestroyComponent',effect.call_function('GetOwner'))
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        self.report['owned_actor_cleanup_observations']=[dict(path=path(a),destroyed=dead(a)) for a in self.actors]
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),owned_effects_removed=all(not valid(e) for e in self.effects),owned_watchers_cancelled=all(not valid(w) or not w.call_function('IsActive') for w in self.watchers),original_health_unchanged=self.healths()==self.health_before,
            production_profiles_restored=any(r['target_class']==self.cls and all(r['profiles'][p]['python_class'] is source and len(r['profiles'][p]['functions'])==8 for p,source in self.sources.items()) for r in ue.get_registered_mixins()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native spawning total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='pair':self.pair()
            elif self.phase=='manager':self.manager()
            elif self.phase=='manager-removed':self.manager_removed()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SPAWNING_CUE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SPAWNING_CUE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSpawningCueResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
