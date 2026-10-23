"""Original placed Explorer AI, compiled tree, real navigation, cancel and travel."""
import atexit,copy,sys,time,traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_characters.explorer_experience_validation import Validation as Experience,path,vector
from .effect_pad_mixin import valid,ability_system
from . import explorer_state_mixin as policy
from .explorer_follow_contract import MAP,RESET_MAP,TREE,PAWN,require,validate

def squared(a,b):return sum((x-y)**2 for x,y in zip(vector(a),vector(b)))
def frame():return int(lib('KismetSystemLibrary').call_function('GetFrameCount'))

class Validation(Experience):
    def __init__(self,result):
        super().__init__(result);self.node_classes={};self.templates={};self.observers=[];self.observed={};self.ai=[];self.components=[];self.pose=None
        self.report.update(waypoints=[],cancel={},restart={},node_observations=[],original_tree=TREE,fixture_player_position_and_movement_mode=True,
            fixture_ai_or_task_spawned=False,tree_asset_or_bindings_edited=False,task_events_or_callbacks_replayed=False,
            unused_evaluator_or_delay_claimed_as_map_execution=False,templates_and_observers_restored=False,player_pose_restored=False,
            original_placed_ai_destroyed_after_travel=False,original_runtime_nodes_destroyed_after_travel=False,late_callbacks_after_travel=0)
    def context(self):
        if self.phase in ('warmup','reset-travel','cleanup-quiet'):return super().context()
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or world.get_path_name()!=MAP+'.L_StateTree_FollowTest':continue
            pc=lib('GameplayStatics').call_function('GetPlayerController',world,0);pawn=pc.get_controlled_pawn() if valid(pc) else None
            if not valid(pawn) or pawn.get_property('bHidden'):continue
            asc=ability_system(pawn);inventory=pc.get_component_by_type(ue.find_class('LyraInventoryManagerComponent'))
            if valid(asc) and asc.get_property('AvatarActor')==pawn and valid(inventory) and inventory.call_function('GetAllItems'):return world,pc,pawn,asc
    def prepare(self):
        self.node_classes={k:ue.load_class(policy.CLASSES[k]) for k in ('location','goto','follow')}
        for cls in list(self.node_classes.values())+[ue.load_class(PAWN)]:ue.register_declared_mixin(cls)
        super().prepare()
    def around(self,kind,name,profile,original):
        def invoke(node,*args):
            key=path(node)
            if node not in self.templates and 'Default__' not in key:
                row=self.observed.setdefault(key,dict(node=node,kind=kind,profile=profile,calls={},location_mismatches=0))
                row['calls'][name]=row['calls'].get(name,0)+1
            else:row=None
            return original(node,*args)
        invoke.override=original.override;return invoke
    def sample_locations(self):
        # Fallback's True result first lets the original graph update the value.
        # Read on the next control frame, before changing the controlled player.
        if self.pose is None or not valid(self.pawn):return
        for row in self.observed.values():
            if row['kind']!='location' or not valid(row['node']):continue
            ticks=row['calls'].get('tick',0)
            if ticks==row.get('sampled_tick',0):continue
            row['sampled_tick']=ticks;row['location_samples']=row.get('location_samples',0)+1
            row['last_location']=vector(row['node'].get_property('PlayerLocation'));row['last_player_location']=vector(self.pawn.get_actor_location())
            if sum((a-b)**2 for a,b in zip(row['last_location'],row['last_player_location']))>.01:row['location_mismatches']+=1
    def select_tree_templates(self):
        self.tree=ue.load_object(ue.find_class('StateTree'),TREE)
        if not self.tree.is_rooted():self.tree.add_to_root();self.roots.append(self.tree)
        for kind,cls in self.node_classes.items():
            for node in ue.tobject_iterator(cls):
                if node.get_path_name().startswith(TREE+':'):
                    self.templates[node]=str(node.get_property('PythonMixinProfile'));node.set_property('PythonMixinProfile',self.profile)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls]
            for profile,value in row['profiles'].items():
                original=value['python_class'];methods={}
                for name,fn in vars(original).items():
                    if callable(fn) and hasattr(fn,'override'):methods[name]=self.around(kind,name,profile,fn)
                if methods:
                    ue.register_mixin_profile(cls,profile,type('ObservedPlacedExplorer'+kind+profile,(),methods));self.observers.append((cls,profile,original))
        require(self.templates,'original serialized tree templates missing')
        self.report['template_count']=len(self.templates)
    def travel(self):
        self.release_input()
        if self.pc is not None:self.old.append((self.pc,self.pawn))
        self.previous_world=self.world
        for cls in self.classes:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        first=self.report['native_level_open_requests']==0
        if first:self.select_tree_templates()
        self.report['native_level_open_requests']+=1
        lib('GameplayStatics').call_function('OpenLevel',self.world,MAP if first else RESET_MAP,True,'')
        self.pc=None;self.pawn=None;self.world=None;self.enter('travel' if first else 'reset-travel')
    def rows(self):
        return [dict(path=key,kind=r['kind'],profile=r['profile'],calls=dict(r['calls']),location_mismatches=r['location_mismatches'],
            location_samples=r.get('location_samples',0),last_location=r.get('last_location'),last_player_location=r.get('last_player_location')) for key,r in sorted(self.observed.items())]
    def totals(self):
        result={kind+'_'+name:0 for kind in self.node_classes for name in policy.METHODS[kind]}
        for row in self.observed.values():
            for name,value in row['calls'].items():result[row['kind']+'_'+name]+=value
        return result
    def start_case(self,context):
        self.world,self.pc,self.pawn,self.asc=context
        self.inventory_before=self.inventory();self.report['initial_inventory']=self.inventory_before
        actors,=lib('GameplayStatics').call_function('GetAllActorsOfClass',self.world,ue.load_class(PAWN))
        self.placed=sorted((a for a in actors if valid(a)),key=path);require(len(self.placed)==3,'all three original placed Explorer Pawns required')
        self.report['placed_pawns']=[dict(path=path(a),cls=path(a.get_class()),use_behavior_tree=bool(a.get_property('UseBhvTree'))) for a in self.placed]
        for actor in self.placed:
            component=actor.get_property('StateTree');controller=actor.call_function('GetController')
            if valid(component) and valid(controller):self.ai.append(dict(pawn=actor,controller=controller,component=component));self.components.append(component)
        require(self.ai,'original placed StateTree/controller bindings missing')
        self.movement=self.pawn.get_component_by_type(ue.find_class('CharacterMovementComponent'))
        self.pose=dict(location=self.pawn.get_actor_location(),mode=int(self.movement.get_property('MovementMode')),custom=int(self.movement.get_property('CustomMovementMode')))
        self.movement.call_function('SetMovementMode',0,0);self.enter('native-ready')
    def project(self,point):
        result=lib('NavigationSystemV1').call_function('K2_ProjectPointToNavigation',WorldContextObject=self.world,Point=point,NavData=None,FilterClass=None,QueryExtent=ue.FVector(300.,300.,700.))
        projected,=[v for v in result if type(v) is not bool];success,=[v for v in result if type(v) is bool]
        return projected if success else None
    def candidates(self):
        center=self.pose['location'];candidates=[]
        for x,y in ((1600.,0.),(-1600.,0.),(0.,1600.),(0.,-1600.),(1600.,1600.),(-1600.,-1600.),(2400.,0.),(0.,2400.)):
            point=self.project(ue.FVector(center.x+x,center.y+y,center.z))
            if point is None:continue
            plans=[]
            for row in self.ai:
                actor=row['pawn'];route=lib('NavigationSystemV1').call_function('FindPathToLocationSynchronously',self.world,actor.get_actor_location(),point,actor,None)
                if not valid(route) or not route.call_function('IsValid') or route.call_function('IsPartial') or squared(actor.get_actor_location(),point)<1100.**2:break
                plans.append(dict(pawn=path(actor),length=float(route.call_function('GetPathLength')),points=len(route.get_property('PathPoints')),partial=False))
            if len(plans)==len(self.ai):candidates.append((point,plans))
        return candidates
    def begin_waypoint(self,index):
        point,plans=self.routes[index];half=float(self.pawn.get_property('CapsuleComponent').call_function('GetScaledCapsuleHalfHeight'))
        self.pawn.set_actor_location(ue.FVector(point.x,point.y,point.z+half));self.counts_before=self.totals()
        self.row=dict(index=index,nav_point=vector(point),plans=plans,before_counts=self.counts_before,
            ai_start=[vector(r['pawn'].get_actor_location()) for r in self.ai]);self.report['waypoints'].append(self.row);self.enter('waypoint')
    def native_ready(self):
        self.report['native_ready_diagnostics']=[dict(pawn=path(r['pawn']),controller=path(r['controller']),tree=path(r['component']),running=bool(r['component'].call_function('IsRunning')),move_status=int(r['controller'].call_function('GetMoveStatus'))) for r in self.ai]
        if not all(r['component'].call_function('IsRunning') for r in self.ai):return
        if self.totals()['location_tick']<3:return
        routes=self.candidates();require(routes,'no complete original navigation route beyond follow distance')
        first=routes[0];second=next((r for r in routes[1:] if squared(first[0],r[0])>1400.**2),None)
        require(second is not None,'two separated original navigation waypoints required')
        self.routes=[first,second];self.begin_waypoint(0)
    def waypoint(self):
        distances=[(r['pawn'].get_actor_location().x-self.pawn.get_actor_location().x)**2+(r['pawn'].get_actor_location().y-self.pawn.get_actor_location().y)**2 for r in self.ai]
        counts=self.totals();self.row.update(current_counts=counts,current_distances_squared=distances)
        if not all(d<400.**2 for d in distances):return
        self.row.update(arrived=True,ai_end=[vector(r['pawn'].get_actor_location()) for r in self.ai],
            native_success_delta=sum(counts[k]-self.counts_before[k] for k in ('goto_success','follow_success')))
        if self.row['native_success_delta']<1:return
        if self.row['index']==0:self.begin_waypoint(1)
        else:
            point=self.routes[0][0];half=float(self.pawn.get_property('CapsuleComponent').call_function('GetScaledCapsuleHalfHeight'))
            self.pawn.set_actor_location(ue.FVector(point.x,point.y,point.z+half));self.enter('cancel-moving')
    def cancel_moving(self):
        moving=[r for r in self.ai if int(r['controller'].call_function('GetMoveStatus'))==3]
        if not moving:return
        self.report['cancel']=dict(moving_before=len(moving),before_counts=self.totals())
        for row in self.ai:
            row['component'].call_function('StopLogic','UEP original placed-tree cancel');row['controller'].call_function('StopMovement')
        self.enter('cancel-drain')
    def cancel_drain(self):
        if time.monotonic()-self.phase_started<.5:return
        require(all(not r['component'].call_function('IsRunning') and int(r['controller'].call_function('GetMoveStatus'))==0 for r in self.ai),'native cancel did not stop original tree and movement')
        self.report['cancel'].update(stopped=True,after_counts=self.totals());self.quiet_counts=self.totals();self.enter('cancel-quiet')
    def restart(self):
        require(self.totals()==self.quiet_counts,'original stopped tree kept invoking task callbacks')
        self.report['cancel']['quiet_after_drain']=True
        self.restart_counts=self.totals()
        for row in self.ai:row['component'].call_function('RestartLogic')
        self.enter('restart-moving')
    def restart_moving(self):
        if not all(r['component'].call_function('IsRunning') for r in self.ai):return
        moving=[r for r in self.ai if int(r['controller'].call_function('GetMoveStatus'))==3]
        if not moving or self.totals()['location_tick']<=self.restart_counts['location_tick']:return
        self.report['restart']=dict(running=True,moving=len(moving),native_callbacks_resumed=True,travel_while_move_active=True)
        self.restore_pose();self.travel()
    def restore_pose(self):
        if self.pose is not None and valid(self.pawn):
            self.pawn.set_actor_location(self.pose['location']);self.movement.call_function('SetMovementMode',self.pose['mode'],self.pose['custom'])
            self.report['player_pose_restored']=squared(self.pawn.get_actor_location(),self.pose['location'])<.001 and int(self.movement.get_property('MovementMode'))==self.pose['mode'];self.pose=None
    def reset_complete(self,context):
        self.world,self.pc,self.pawn,self.asc=context
        self.report['garbage_collection_requested_frame']=frame()
        lib('KismetSystemLibrary').call_function('CollectGarbage')
        self.cleanup_counts=self.totals();self.enter('cleanup-quiet')
    def check_after_deferred_gc(self):
        # CollectGarbage requests an end-of-frame collection; it is not synchronous.
        require(frame()>self.report['garbage_collection_requested_frame'],'native deferred GC requires a later engine frame')
        self.report['garbage_collection_checked_frame']=frame()
        survivors=[r for r in self.observed.values() if valid(r['node'])]
        self.report['surviving_node_diagnostics']=[dict(path=path(r['node']),kind=r['kind'],rooted=bool(r['node'].is_rooted()),python_owned=bool(r['node'].is_owned()),outer=path(r['node'].get_outer())) for r in survivors]
        for row in survivors[:3]:
            ue.log('UEP_FOLLOW_NODE_REFERENCE '+path(row['node']))
            lib('KismetSystemLibrary').call_function('ExecuteConsoleCommand',self.world,'obj refs name="'+path(row['node'])+'" shortest',self.pc)
        self.report['original_placed_ai_destroyed_after_travel']=all(not valid(a) for a in self.placed)
        self.report['original_runtime_nodes_destroyed_after_travel']=all(not valid(r['node']) for r in self.observed.values())
        self.report['old_profile_pawns_and_controllers_destroyed']=all(not valid(v) for pair in self.old for v in pair)
        self.report['inventory_preserved_after_travel']=self.inventory()==self.inventory_before
        self.report['late_callbacks_after_travel']=sum(self.totals().values())-sum(self.cleanup_counts.values());self.finish()
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<420.,'original Explorer follow-map timeout');require(time.monotonic()-self.phase_started<90.,'original follow-map phase timeout: '+self.phase)
            self.sample_locations()
            if self.phase=='warmup':
                context=self.context()
                if context is not None:self.world,self.pc,self.pawn,self.asc=context;self.prepare()
            elif self.phase in ('travel','reset-travel'):
                context=self.context()
                if context is not None and context[0]!=self.previous_world:
                    if self.phase=='travel':self.start_case(context)
                    else:self.reset_complete(context)
            elif self.phase=='native-ready':self.native_ready()
            elif self.phase=='waypoint':self.waypoint()
            elif self.phase=='cancel-moving':self.cancel_moving()
            elif self.phase=='cancel-drain':self.cancel_drain()
            elif self.phase=='cancel-quiet' and time.monotonic()-self.phase_started>.5:self.restart()
            elif self.phase=='restart-moving':self.restart_moving()
            elif self.phase=='cleanup-quiet' and time.monotonic()-self.phase_started>1.:
                self.check_after_deferred_gc()
            self.report.update(phase=self.phase,node_observations=self.rows(),totals=self.totals());self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:
            self.restore_pose();self.release_input()
            for cls,profile,original in self.observers:ue.register_mixin_profile(cls,profile,original)
            for node,profile in self.templates.items():node.set_property('PythonMixinProfile',profile)
            self.report['templates_and_observers_restored']=all(str(n.get_property('PythonMixinProfile'))==p for n,p in self.templates.items()) and all(next(r for r in ue.get_registered_mixins() if r['target_class']==cls)['profiles'][p]['python_class'] is original for cls,p,original in self.observers)
            for cls,profile in self.classes.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
            for obj in self.roots:obj.remove_from_root()
            self.report['selectors_restored']=all(str(c.get_cdo().get_property('PythonMixinProfile'))==p for c,p in self.classes.items()) and all(not o.is_rooted() for o in self.roots)
            self.report.update(node_observations=self.rows(),totals=self.totals())
            if error is None:validate(dict(self.report,status='passed',actual_exit_finalizer=True))
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_FOLLOW_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        self.report['actual_exit_finalizer']=True
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_FOLLOW_SHUTDOWN_'+self.report['status'].upper())

result=next((a.split('=',1)[1] for a in sys.argv if a.startswith('-UEPExplorerFollowResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
