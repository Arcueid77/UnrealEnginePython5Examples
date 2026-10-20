"""Run original compiled tree; unused evaluator/delay use real native events."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from .effect_pad_mixin import valid
from . import explorer_state_mixin as policy
from .explorer_state_contract import FALSE_FIELDS,require,validate

TREE='/ShooterExplorer/AI/StateTrees/Trees/L_STT_FollowPlayer.L_STT_FollowPlayer'

def xyz(v):return [float(v.x),float(v.y),float(v.z)]
def near(a,b):return all(abs(x-y)<.1 for x,y in zip(xyz(a),xyz(b)))
def count(obj,kind,key):return sum(policy.evidence(obj,kind)[p+'_'+key] for p in ('python','fallback'))

class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.require_local_playing_phase=False;self.require_auto_active=False
        self.profile=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerStateProfile=')),'Python')
        self.report=dict(status='running',error=None,profile=self.profile,compiled_tree_nodes=['location','goto','follow'],direct_event_nodes=['eval','delay','goto','follow'])
        self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.cdos={};self.templates={};self.roots=[];self.owned=[];self.nodes=[];self.observed={};self.sources={}
    def ready(self):
        # This node fixture does no damage or combat. Warmup immunity is irrelevant.
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3):continue
            bridge=policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0):continue
            controller=self.statics.call_function('GetPlayerController',world,0)
            if not valid(controller) or not valid(controller.get_controlled_pawn()):continue
            self.world,self.controller,self.pawn=world,controller,controller.get_controlled_pawn();self.begin();return
    def begin(self):
        self.health_before=self.healths();self.classes={key:ue.load_class(path) for key,path in policy.CLASSES.items()}
        for key,cls in self.classes.items():
            if not cls.is_rooted():cls.add_to_root();self.roots.append(cls)
            self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[cls]={p:r['python_class'] for p,r in row['profiles'].items()}
            for profile,base in self.sources[cls].items():
                methods={}
                for name,fn in vars(base).items():
                    if not callable(fn) or not hasattr(fn,'override'):continue
                    def around(fn,key,name):
                        def invoke(node,*args):
                            if node.get_path_name() not in self.observed:self.observed[node.get_path_name()]=dict(node=node,kind=key,calls={})
                            calls=self.observed[node.get_path_name()]['calls'];calls[name]=calls.get(name,0)+1
                            return fn(node,*args)
                        invoke.override=fn.override;return invoke
                    methods[name]=around(fn,key,name)
                ue.register_mixin_profile(cls,profile,type('ObservedExplorer'+key+profile,(),methods))
        self.tree=ue.load_object(ue.find_class('StateTree'),TREE)
        if not self.tree.is_rooted():self.tree.add_to_root();self.roots.append(self.tree)
        for key in ('location','goto','follow'):
            for node in ue.tobject_iterator(self.classes[key]):
                if node.get_path_name().startswith(TREE+':'):
                    self.templates[node]=node.get_property('PythonMixinProfile');node.set_property('PythonMixinProfile',self.profile)
        require(self.templates,'original serialized StateTree templates absent')
        # Owned character satisfies the original schema, including its CapsuleComponent binding.
        self.subject=self.world.actor_spawn(ue.load_class('/Game/Characters/Heroes/B_Hero_Default.B_Hero_Default_C'),self.pawn.get_actor_location()+ue.FVector(1600.,0.,0.));self.owned.append(self.subject)
        self.subject.call_function('SetActorEnableCollision',False)
        self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',0,0)
        self.ai=self.world.actor_spawn(ue.find_class('AIController'));self.owned.append(self.ai);self.ai.call_function('Possess',self.subject)
        self.component=ue.new_object(ue.find_class('StateTreeComponent'),self.subject)
        self.component.call_function('SetStartLogicAutomatically',False);self.component.call_function('SetStateTree',self.tree);self.subject.add_instance_component(self.component);self.component.register_component();self.component.call_function('StartLogic')
        require(self.component.call_function('IsRunning'),'original compiled StateTree did not start')
        self.report['original_compiled_tree_executed']=True;self.enter('tree');self.repositioned=False
    def totals(self):
        result={kind+'_'+key:0 for kind in ('location','goto','follow') for key in policy.METHODS[kind]}
        for row in self.observed.values():
            if row['kind'] not in ('location','goto','follow'):continue
            # Only callbacks belonging to the component's native runtime node instances count.
            node=row['node']
            if not valid(node) or node in self.templates or node.get_path_name().startswith('/Engine/Transient.Default__'):continue
            for key,value in row['calls'].items():result[row['kind']+'_'+key]+=value
        return result
    def observe(self):
        require(time.monotonic()-self.phase_started<65.,'Explorer phase timeout: '+self.phase)
        if self.phase=='tree':
            counts=self.totals();self.report['compiled_tree_counts']=counts
            for row in self.observed.values():
                if row['kind']=='location' and valid(row['node']) and row['node'] not in self.templates:
                    require(near(row['node'].get_property('PlayerLocation'),self.pawn.get_actor_location()),'native global location does not match player zero');self.report['native_global_location_matches_player_zero']=True
            # Original tree skips Follow when already near; move only our fixture character.
            if not self.repositioned and counts['goto_success']+counts['goto_failed']:
                self.subject.call_function('K2_SetActorLocation',NewLocation=self.pawn.get_actor_location()+ue.FVector(1600.,0.,0.),bSweep=False,bTeleport=True);self.repositioned=True
            if not (counts['location_tick']>=3 and counts['goto_enter'] and counts['follow_enter'] and counts['goto_success']+counts['goto_failed'] and counts['follow_success']+counts['follow_failed']):return
            self.report['native_goto_and_follow_callbacks_observed']=True;self.component.call_function('StopLogic','UEP Explorer original-tree acceptance');self.report['native_tree_stopped']=not self.component.call_function('IsRunning');self.start_direct_moves()
        elif self.phase=='direct_moves':
            key,node=self.direct_move;values={m:count(node,key,m) for m in policy.METHODS[key]};self.report['direct_move_counts'][key]=values
            if not values['success'] and not values['failed']:return
            require(values==dict(enter=1,success=1,failed=0),'native already-at-goal completion differs: '+key)
            if key=='goto':self.start_direct_move('follow')
            else:self.direct_events()
        elif self.phase=='delay':
            d=self.delay
            if count(d,'delay','enter_done')==0:
                require(d.get_property('DelayInProgress') is True,'enter delay flag cleared before native completion');return
            require(d.get_property('DelayInProgress') is False,'enter completion must clear flag')
            require(count(d,'delay','tick_done')==0,'enter completion must not finish tick')
            d.call_function('ReceiveLatentTick',.016);d.call_function('ReceiveLatentTick',.016)
            require(d.get_property('DelayInProgress') is True,'tick delay must set flag');self.enter('delay_tick')
        elif self.phase=='delay_tick':
            if count(self.delay,'delay','tick_done')<1:return
            require(self.delay.get_property('DelayInProgress') is True,'original tick completion leaves delay flag set')
            self.report['delay_counts']={key:count(self.delay,'delay',key) for key in policy.METHODS['delay']};self.report['delay_elapsed']=self.game_time()-self.delay_started;self.report['native_delay_enter_tick_flags_and_two_completions_observed']=True;self.finish()
    def start_direct_moves(self):
        # Already-at-goal succeeds without navigation; callbacks are native AI-task delegates.
        # These task event fixtures do not claim a StateTree weak execution context.
        self.subject.call_function('SetActorEnableCollision',True)
        self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent')).call_function('SetMovementMode',5,0)
        self.subject.call_function('K2_SetActorLocation',NewLocation=self.pawn.get_actor_location()+ue.FVector(100.,0.,0.),bSweep=False,bTeleport=True)
        self.report['direct_move_counts']={}
        self.start_direct_move('goto')
    def start_direct_move(self,key):
        node=ue.new_object(self.classes[key],self.subject);node.add_to_root();self.nodes.append(node);ue.set_mixin_profile(node,self.profile);node.set_property('Actor',self.subject);node.set_property('StopDistance',1000.)
        if key=='goto':node.set_property('GoToLocation',self.pawn.get_actor_location())
        self.report.setdefault('direct_move_diagnostics',{})[key]=dict(subject=xyz(self.subject.get_actor_location()),player=xyz(self.pawn.get_actor_location()),controlled=self.ai.get_controlled_pawn()==self.subject,actor_property_matches=node.get_property('Actor')==self.subject,native_ai_controller_matches=policy.lib('AIBlueprintHelperLibrary').call_function('GetAIController',self.subject)==self.ai,stop_distance=float(node.get_property('StopDistance')))
        self.direct_move=(key,node);node.call_function('ReceiveLatentEnterState',ue.find_struct('StateTreeTransitionResult')());self.enter('direct_moves')
    def direct_events(self):
        for key in ('eval','delay'):
            node=ue.new_object(self.classes[key],self.subject);node.add_to_root();self.nodes.append(node);ue.set_mixin_profile(node,self.profile)
            if key=='eval':
                node.call_function('ReceiveTick',.123);require(near(node.get_property('PlayerPosition'),self.pawn.get_actor_location()) and count(node,key,'tick')==1,'native evaluator event/getter differs');self.report['native_evaluator_event_location_matches']=True
            else:self.delay=node
        self.delay.set_property('Delay',.18);self.delay.set_property('DelayInProgress',False);self.report['delay_duration']=.18;self.delay_started=self.game_time()
        self.delay.call_function('ReceiveLatentEnterState',ue.find_struct('StateTreeTransitionResult')());self.delay.call_function('ReceiveLatentTick',.016);require(self.delay.get_property('DelayInProgress') is True,'native enter delay missing');self.enter('delay')
    def cleanup(self):
        if hasattr(self,'component') and valid(self.component):self.component.call_function('StopLogic','UEP Explorer fixture cleanup');self.component.call_function('K2_DestroyComponent',self.subject)
        for node in self.nodes:
            if valid(node):ue.clear_mixin_profile(node);node.remove_from_root()
        for actor in reversed(self.owned):
            if valid(actor):actor.actor_destroy()
        for node,profile in self.templates.items():node.set_property('PythonMixinProfile',profile)
        for cls,profile in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',profile)
        for cls,profiles in self.sources.items():
            for name,source in profiles.items():ue.register_mixin_profile(cls,name,source)
        self.report['owned_objects_roots_profiles_and_templates_restored']=all(node.get_property('PythonMixinProfile')==profile for node,profile in self.templates.items()) and all(cls.get_cdo().get_property('PythonMixinProfile')==profile for cls,profile in self.cdos.items()) and all(not valid(a) for a in self.owned)
        for obj in self.roots:obj.remove_from_root()
        if hasattr(self,'health_before'):self.report['initial_gameplay_health_unchanged']=self.healths()==self.health_before
    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<210.,'Explorer validation timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_EXPLORER_STATE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_EXPLORER_STATE_SHUTDOWN_'+self.report['status'].upper())

result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerStateResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
