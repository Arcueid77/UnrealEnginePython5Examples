"""Placed original Rock/Chair, native input/GAS, pickup, montage, marker and travel."""
import atexit,copy,hashlib,sys,time,traceback
from pathlib import Path
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_weapons import collect_cue_lifecycle_mixin as cue
from uep_lyra_characters.explorer_experience_validation import Validation as Experience,path,vector
from .auto_respawn_helpers_validation import instances
from . import explorer_interact_mixin as interact,explorer_actions_mixin as actions,explorer_marker_mixin as marker
from .explorer_gameplay_contract import MAP,TARGETS,require,validate

def counters(obj,policy):return {k:v for k,v in policy.evidence(obj).items() if isinstance(v,(int,float))}
def difference(obj,policy,before):return {k:v-before.get(k,0) for k,v in counters(obj,policy).items()}

class Validation(Experience):
    def __init__(self,result):
        super().__init__(result);self.targets={};self.cues=[];self.pose=None;self.recorded_abilities=[];self.images=[];self.observed_profiles=[];self.activation_events=[]
        self.report.update(actions=[],marker=[],images=self.images,fixture_position_movement_and_aim=True,native_input_asset_injections=[],
            pawn_pose_restored=False,level_targets_destroyed_after_travel=False,native_inventory_restored_after_travel=False,original_target_counts_restored=False,action_observers_restored=False)
    def observe_entry(self,kind,original):
        def called(actor,EventData):
            self.activation_events.append(dict(kind=kind,instance=path(actor),instigator=path(EventData.Instigator),target=path(EventData.Target)))
            return original(actor,EventData)
        return called
    def install_observers(self):
        for kind,target in actions.CLASSES.items():
            cls=ue.load_class(target);binding,=[r for r in ue.get_registered_mixins() if r['target_class']==cls]
            base=binding['profiles'][self.profile]['python_class'];values={k:v for k,v in vars(base).items() if not k.startswith('__') and callable(v)}
            values['K2_ActivateAbilityFromEvent']=self.observe_entry(kind,values['K2_ActivateAbilityFromEvent'])
            ue.register_mixin_profile(cls,self.profile,type('ObservedActualExplorer'+kind.title()+self.profile,(),values));self.observed_profiles.append((cls,self.profile,base))
    def context(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or world.get_path_name()!=MAP+'.L_InteractionTestMap':continue
            pc=lib('GameplayStatics').call_function('GetPlayerController',world,0);pawn=pc.get_controlled_pawn() if valid(pc) else None
            if not valid(pawn):continue
            asc=ability_system(pawn);health=pawn.get_component_by_type(ue.find_class('LyraHealthComponent'))
            if not valid(asc) or asc.get_property('AvatarActor')!=pawn or not valid(health) or health.call_function('GetHealth')<=0 or pawn.get_property('bHidden'):continue
            if any(s.ActiveCount and valid(s.Ability) and s.Ability.get_class().get_name()=='GA_SpawnEffect_C' for s in asc.get_property('ActivatableAbilities').Items):continue
            return world,pc,pawn,asc
    def prepare(self):
        for value in list(actions.CLASSES.values())+[interact.CLASS,marker.CLASS,cue.CLASS]:ue.register_declared_mixin(ue.load_class(value))
        super().prepare()
    def travel(self):
        self.release_input()
        if self.pc is not None:self.old.append((self.pc,self.pawn))
        self.previous_world=self.world
        for cls in self.classes:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        self.report['native_level_open_requests']+=1
        lib('GameplayStatics').call_function('OpenLevel',self.world,MAP,True,'')
        self.pc=None;self.pawn=None;self.world=None;self.enter('travel' if self.report['native_level_open_requests']==1 else 'reset-travel')
    def actors(self,kind):
        actors,=lib('GameplayStatics').call_function('GetAllActorsOfClass',self.world,ue.load_class(TARGETS[kind]))
        return sorted((a for a in actors if valid(a) and not a.call_function('IsActorBeingDestroyed')),key=path)
    def counts(self):return {kind:len(self.actors(kind)) for kind in TARGETS}
    def inventory_totals(self):
        values={}
        for row in self.inventory():values[row['definition']]=values.get(row['definition'],0)+row['count']
        return values
    def start_case(self,context):
        self.world,self.pc,self.pawn,self.asc=context;require(self.world!=self.previous_world,'fresh native interaction World required')
        require(str(self.pawn.get_property('PythonMixinProfile'))==self.profile,'actual Explorer hero did not select requested profile before spawn')
        gs=lib('GameplayStatics').call_function('GetGameState',self.world);experience=gs.get_component_by_type(ue.find_class('LyraExperienceManagerComponent')).get_property('CurrentExperience')
        self.report.update(world=path(self.world),experience=path(experience),pawn_class=path(self.pawn.get_class()),native_role=int(self.pawn.call_function('GetLocalRole')),
            initial_inventory=self.inventory(),initial_target_counts=self.counts(),actual_interactor_count=0)
        self.targets={kind:self.actors(kind)[0] for kind in TARGETS};self.target_paths={kind:path(a) for kind,a in self.targets.items()}
        self.report['placed_target_paths']=self.target_paths
        self.interactors=[a for a in instances(self.asc,ue.load_class(interact.CLASS)) if a.get_property('bIsActive')]
        require(self.interactors,'naturally granted active original Interact instances missing')
        self.report['actual_interactor_count']=len(self.interactors);self.recorded_abilities.extend(self.interactors)
        self.install_observers()
        self.movement=self.pawn.get_component_by_type(ue.find_class('CharacterMovementComponent'))
        self.pose=dict(location=self.pawn.get_actor_location(),rotation=self.pc.call_function('GetControlRotation'),mode=int(self.movement.get_property('MovementMode')),custom=int(self.movement.get_property('CustomMovementMode')))
        self.start_action('collect')
    def place(self,target):
        origin=target.get_actor_location();self.movement.call_function('SetMovementMode',0,0)
        self.pawn.set_actor_location(ue.FVector(origin.x-150.,origin.y-90.,origin.z+95.));self.aim_target=target;self.aim()
    def aim(self):
        origin,_=self.aim_target.call_function('GetActorBounds',True);camera=self.pc.get_property('PlayerCameraManager').call_function('GetCameraLocation')
        self.pc.call_function('SetControlRotation',lib('KismetMathLibrary').call_function('FindLookAtRotation',camera,origin))
    def start_action(self,kind):
        self.kind=kind;self.target=self.targets[kind];self.place(self.target);self.inventory_before=self.inventory_totals()
        self.row=dict(kind=kind,target_class=path(self.target.get_class()),target=path(self.target),inventory_before=self.inventory_before)
        if kind=='collect':
            pickup=self.target.get_property('StaticInventory');self.row['pickup_templates']=[dict(definition=path(t.ItemDef),count=int(t.StackCount)) for t in pickup.Templates]
        self.report['actions'].append(self.row);self.enter('scan')
    def press(self,asset):
        self.inject('/ShooterExplorer/Input/Actions/'+asset+'.'+asset,(1.,0.,0.));self.released=False
        self.report['native_input_asset_injections'].append(asset)
    def scan(self):
        self.aim();self.action_instances=instances(self.asc,ue.load_class(actions.CLASSES[self.kind]))
        matching=[a for a in self.interactors if any(valid(o.InteractionAbilityToGrant) and path(o.InteractionAbilityToGrant)==actions.CLASSES[self.kind] for o in a.get_property('CurrentOptions'))]
        self.report['scan_diagnostics']=dict(kind=self.kind,matching=len(matching),interactors=len(self.interactors),action_instances=len(self.action_instances),
            options=[[path(o.InteractionAbilityToGrant) for o in a.get_property('CurrentOptions')] for a in self.interactors])
        if len(matching)!=len(self.interactors) or not self.action_instances or time.monotonic()-self.phase_started<.75:return
        self.action_before={path(a):counters(a,actions) for a in self.action_instances};self.interact_before={path(a):counters(a,interact) for a in self.interactors}
        self.recorded_abilities.extend(self.action_instances);self.montage_seen=False;self.payload_seen=False;self.action_time=self.game_time();self.press('IA_Interact');self.enter('action')
    def game_time(self):return float(lib('GameplayStatics').call_function('GetTimeSeconds',self.world))
    def capture(self,kind):
        destination=self.path.parent/(kind+'.png');require(not destination.exists(),'refusing to overwrite native gameplay frame')
        lib('KismetSystemLibrary').call_function('ExecuteConsoleCommand',self.world,'Shot -nosuffix filename="'+str(destination)+'"',self.pc)
        self.images.append(dict(kind=kind,path=str(destination),game_time=self.game_time(),sha256=None))
    def observe_action(self):
        if not self.released:self.release_input();self.released=True
        activated=[a for a in self.action_instances if sum(difference(a,actions,self.action_before[path(a)])[p+'_activate'] for p in ('python','fallback'))>0]
        if not activated:return
        anim=self.pawn.get_property('Mesh').call_function('GetAnimInstance')
        if any(a.get_property('bIsActive') and anim.call_function('Montage_IsPlaying',a.get_property('Montage to Play')) for a in activated):
            if not self.montage_seen:self.capture(self.kind)
            self.montage_seen=True
        event_rows=[e for e in self.activation_events if e['kind']==self.kind and e['instance'] in {path(a) for a in activated}]
        self.row['native_activation_events']=copy.deepcopy(event_rows)
        require(len(event_rows)==len(activated) and all(e['instigator']==path(self.pawn) and e['target']==path(self.target) for e in event_rows),'actual native entry delivered a different interaction target/instigator: '+repr(event_rows))
        self.payload_seen=True
        if self.kind=='collect':
            for a in ue.tobject_iterator(ue.load_class(cue.CLASS)):
                if valid(a) and a.call_function('GetOwner')==self.pawn and a not in self.cues:self.cues.append(a)
        if any(a.get_property('bIsActive') or a.get_property('ActiveTasks') for a in activated) or self.game_time()-self.action_time<.8:return
        self.row.update(native_montage_seen=self.montage_seen,actual_event_target_and_instigator=self.payload_seen,inventory_after=self.inventory_totals(),
            interactor_press_deltas=[difference(a,interact,self.interact_before[path(a)]) for a in self.interactors],
            action_deltas=[difference(a,actions,self.action_before[path(a)]) for a in activated],native_tasks_closed=True,
            target_collision_after=bool(self.target.call_function('GetActorEnableCollision')) if valid(self.target) else False,
            target_lifespan_after=float(self.target.call_function('GetLifeSpan')) if valid(self.target) else None)
        if self.kind=='collect':self.enter('collect-retire')
        else:self.place(self.targets['sit']);self.marker_instances=instances(self.asc,ue.load_class(marker.CLASS));self.enter('marker-aim')
    def collect_retire(self):
        if valid(self.targets['collect']) or not self.cues:return
        if any(not valid(a) or a.call_function('GetOwner') is not None or not a.get_property('bHidden') for a in self.cues):return
        self.row['native_target_expired_after_three_seconds']=self.game_time()-self.action_time>=2.9
        self.report['recycled_collect_cues']=[dict(actor=path(a),alive=True,hidden=True,owner_cleared=True,
            splines=len(lib('LyraSystemStatics').call_function('FindComponentsByClass',a,ue.find_class('SplineComponent'),False)),
            lifespan=float(a.call_function('GetLifeSpan')),counters=counters(a,cue)) for a in self.cues]
        self.start_action('sit')
    def marker_aim(self):
        self.aim()
        if time.monotonic()-self.phase_started<.75:return
        require(self.marker_instances,'original granted marker instance missing');self.marker_before={path(a):counters(a,marker) for a in self.marker_instances}
        self.recorded_abilities.extend(self.marker_instances);self.press('IA_ToggleMarkerInWorld');self.enter('marker')
    def marker_result(self):
        if not self.released:self.release_input();self.released=True
        active=[a for a in self.marker_instances if sum(difference(a,marker,self.marker_before[path(a)])[p+'_activate'] for p in ('python','fallback'))]
        if not active:return
        if any(a.get_property('bIsActive') or a.get_property('ActiveTasks') for a in active):return
        api=lib('AbilitySystemBlueprintLibrary')
        for a in active:
            data=marker.evidence(a)['last_data'];require(data is not None,'native marker target data callback missing')
            self.report['marker'].append(dict(deltas=difference(a,marker,self.marker_before[path(a)]),has_actor=bool(api.call_function('TargetDataHasActor',data,0)),
                endpoint=vector(api.call_function('GetTargetDataEndPoint',data,0)),draw_center=marker.evidence(a)['last_center'],
                hit_actor_classes=[path(v.get_class()) for v in api.call_function('GetActorsFromTargetData',data,0)],native_tasks_closed=True))
        self.capture('marker');self.enter('marker-capture')
    def restore_pose(self):
        if self.pose is not None and valid(self.pawn):
            self.release_input();self.pawn.set_actor_location(self.pose['location']);self.pc.call_function('SetControlRotation',self.pose['rotation']);self.movement.call_function('SetMovementMode',self.pose['mode'],self.pose['custom'])
            self.report['pawn_pose_restored']=sum((a-b)**2 for a,b in zip(vector(self.pawn.get_actor_location()),vector(self.pose['location'])))<.001 and int(self.movement.get_property('MovementMode'))==self.pose['mode']
            self.pose=None
    def reset_complete(self,context):
        self.world,self.pc,self.pawn,self.asc=context
        self.report['native_inventory_restored_after_travel']=self.inventory()==self.report['initial_inventory']
        self.report['original_target_counts_restored']=self.counts()==self.report['initial_target_counts']
        self.report['level_targets_destroyed_after_travel']=all(not valid(a) for a in self.targets.values())
        self.report['old_profile_pawns_and_controllers_destroyed']=all(not valid(v) for pair in self.old for v in pair)
        self.report['old_ability_instances_destroyed_after_travel']=all(not valid(a) for a in self.recorded_abilities)
        self.finish()
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'actual Explorer gameplay timeout');require(time.monotonic()-self.phase_started<45.,'actual Explorer gameplay phase timeout: '+self.phase)
            if self.phase=='warmup':
                context=self.context()
                if context is not None:self.world,self.pc,self.pawn,self.asc=context;self.prepare()
            elif self.phase in ('travel','reset-travel'):
                context=self.context()
                if context is not None and context[0]!=self.previous_world:
                    if self.phase=='travel':self.start_case(context)
                    else:self.reset_complete(context)
            elif self.phase=='scan':self.scan()
            elif self.phase=='action':self.observe_action()
            elif self.phase=='collect-retire':self.collect_retire()
            elif self.phase=='marker-aim':self.marker_aim()
            elif self.phase=='marker':self.marker_result()
            elif self.phase=='marker-capture' and all(Path(r['path']).exists() for r in self.images):self.restore_pose();self.travel()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:
            self.restore_pose();self.release_input()
            for cls,profile,original in self.observed_profiles:ue.register_mixin_profile(cls,profile,original)
            self.report['action_observers_restored']=all(next(r for r in ue.get_registered_mixins() if r['target_class']==cls)['profiles'][profile]['python_class'] is original for cls,profile,original in self.observed_profiles)
            for cls,profile in self.classes.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
            for cls in self.roots:cls.remove_from_root()
            self.report['selectors_restored']=all(str(cls.get_cdo().get_property('PythonMixinProfile'))==p for cls,p in self.classes.items()) and all(not cls.is_rooted() for cls in self.roots)
            for row in self.images:
                data=Path(row['path']).read_bytes();require(data.startswith(b'\x89PNG\r\n\x1a\n'),'native PNG missing');row['sha256']=hashlib.sha256(data).hexdigest()
            if error is None:validate(dict(self.report,status='passed',actual_exit_finalizer=True))
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_GAMEPLAY_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        self.report['actual_exit_finalizer']=True
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_GAMEPLAY_SHUTDOWN_'+self.report['status'].upper())

result=next((a.split('=',1)[1] for a in sys.argv if a.startswith('-UEPExplorerGameplayResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
