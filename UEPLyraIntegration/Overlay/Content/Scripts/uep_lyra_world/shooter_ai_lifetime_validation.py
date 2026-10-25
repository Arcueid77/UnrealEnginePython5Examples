"""Opt-in native Wait/service cancellation on Pawn destruction and world travel."""
import atexit,sys,time,traceback
import unreal_engine as ue
from uep_runtime import SubscriptionScope
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from . import shooter_ai_mixin as policy
from .shooter_ai_validation import TREE
from .shooter_ai_lifetime_contract import FORBIDDEN,require,validate
MAP='/Game/System/FrontEnd/Maps/L_LyraFrontEnd.L_LyraFrontEnd'
def path(o):return o.get_path_name() if policy.valid(o) else None

def object_alive(name):
    try:return policy.valid(ue.find_object(name))
    except Exception as error:
        if str(error)=='unable to find object '+name:return False
        raise
def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.profile=arg('UEPShooterAILifetimeProfile');self.mode=arg('UEPShooterAILifetimeMode')
        self.report=dict(status='running',error=None,profile=self.profile,mode=self.mode,running_cases=[]);self.report.update(dict.fromkeys(FORBIDDEN,False))
        self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()};self.class_roots=[];self.cdos={};self.sources={};self.calls={};self.scopes={};self.ends={};self.old_paths=[]
        for k,cls in self.classes.items():
            if cls not in self.cdos:
                if not cls.is_rooted():cls.add_to_root();self.class_roots.append(cls)
                self.cdos[cls]=cls.get_cdo().get_property('PythonMixinProfile');cls.get_cdo().set_property('PythonMixinProfile',self.profile)
            if k in ('cp','passive'):continue
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[cls]={p:r['python_class'] for p,r in row['profiles'].items()}
            for profile,base in self.sources[cls].items():
                methods={}
                for name,fn in vars(base).items():
                    if not callable(fn) or not hasattr(fn,'override'):continue
                    gate=next(key for key,value in policy.GATES.items() if value==fn.override)
                    def around(fn,gate):
                        def invoke(obj,*args):
                            self.calls.setdefault((obj.get_path_name(),gate),[]).append(time.monotonic());return fn(obj,*args)
                        invoke.override=fn.override
                        if getattr(fn,'uep_named_outputs',False):invoke.uep_named_outputs=True
                        return invoke
                    methods[name]=around(fn,gate)
                ue.register_mixin_profile(cls,profile,type('LifetimeObserved'+k+profile,(),methods))
    def endplay(self,obj,reason):
        name=obj.get_path_name();self.ends[name]=dict(reason=int(reason),time=time.monotonic())
        scope=self.scopes.pop(name,None)
        if scope is not None:scope.close()
    def watch(self,obj):
        name=path(obj);self.old_paths.append(name);scope=SubscriptionScope();scope.bind_event(obj,'OnEndPlay',self.endplay);self.scopes[name]=scope
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode)
        self.player_name=path(self.pawn);self.health_before=self.healths()[self.player_name];self.old_world_path=path(self.world);self.old_paths.append(self.old_world_path)
        bots=list(policy.one(self.statics.call_function('GetAllActorsOfClass',self.world,self.classes['controller'])))
        live=[b for b in bots if policy.valid(b.get_controlled_pawn()) and policy.valid(b.get_property('BrainComponent'))]
        require(len(live)>=2,'Two actual initialized AI owners required');self.bot_names=[path(b) for b in live[:2]];self.index=0;self.start_tree()
    def start_tree(self):
        self.bot=ue.find_object(self.bot_names[self.index]);self.subject=self.bot.get_controlled_pawn();self.brain=self.bot.get_property('BrainComponent');self.owner_prefix=path(self.bot)
        self.watch(self.bot);self.watch(self.subject);self.old_paths.append(path(self.brain))
        self.subject.call_function('K2_SetActorLocation',NewLocation=ue.FVector(250000.+self.index*5000,250000.,3000.),bSweep=False,bTeleport=True)
        self.bot.call_function('StopMovement')
        tree=ue.load_object(ue.find_class('BehaviorTree'),TREE);task=tree.get_property('RootNode').get_property('Children')[0].ChildTask
        reader=policy.lib('ValueOrBBKeyBlueprintUtility')
        duration=float(reader.call_function('GetFloat',task.get_property('WaitTime'),self.brain));deviation=float(reader.call_function('GetFloat',task.get_property('RandomDeviation'),self.brain))
        self.wait=duration-deviation;self.task_class=task.get_class().get_name()
        require(policy.lib('LyraDevelopmentStatics').call_function('CanPlayerBotsAttack'),'Native Wait decorator must permit execution')
        self.started_tree=time.monotonic();require(self.bot.call_function('RunBehaviorTree',tree),'Native lifetime tree failed to start')
        self.brain=self.bot.get_property('BrainComponent');self.board=policy.lib('AIBlueprintHelperLibrary').call_function('GetBlackboard',self.bot);self.enter('running')
        self.service_names={path(node) for node in self.brain.get_property('NodeInstances')}
    def service_ticks(self):
        return sorted(t for node in self.brain.get_property('NodeInstances') if node.get_class()==self.classes['ammo'] for t in self.calls.get((node.get_path_name(),'ammo'),[]) if t>=self.started_tree)
    def snapshot(self,include_controller=False):return {str(k):len(v) for k,v in self.calls.items() if (k[0].startswith(self.owner_prefix) if include_controller else k[0] in self.service_names)}
    def observe(self):
        require(time.monotonic()-self.phase_started<90.,'AI lifetime phase timeout: '+self.phase)
        if self.phase=='running':
            ticks=self.service_ticks()
            if len(ticks)<3:return
            elapsed=time.monotonic()-self.started_tree;running=bool(self.brain.call_function('IsRunning'))
            self.report['running_cases'].append(dict(purpose='pawn-destroy' if self.index==0 else 'world-travel',controller=path(self.bot),pawn=path(self.subject),native_brain_running=running,task_class=self.task_class,wait_seconds=self.wait,elapsed=elapsed,native_ammo_ticks=len(ticks),intervals=[b-a for a,b in zip(ticks,ticks[1:])]))
            require(running and elapsed<self.wait,'Native Wait already finished before lifetime stimulus')
            self.subject_name=path(self.subject);self.bot_name=path(self.bot)
            if self.index==0:
                self.subject.actor_destroy();self.report.update(pawn_endplay_observed=self.subject_name in self.ends,native_unpossess_stopped_brain=not self.brain.call_function('IsRunning'),native_unpossess_cleared_enemy=self.board.call_function('GetValueAsObject','TargetEnemy') is None)
                self.quiet_before=self.snapshot();self.report['pawn_destroy_callbacks_before']=self.quiet_before;self.report['owner_callbacks_before']=self.snapshot(True);self.enter('destroy_quiet')
            else:
                self.report['player_health_before']=self.health_before;self.report['player_health_before_travel']=self.healths()[self.player_name]
                self.report['player_health_unchanged_before_travel']=self.report['player_health_before_travel']==self.health_before
                self.statics.call_function('OpenLevel',self.world,MAP.split('.')[0],True,'Experience=B_LyraFrontEnd_Experience')
                for name in ('world','controller','pawn','asc','health','ability','death','bot','subject','brain','board'):setattr(self,name,None)
                self.report['python_object_references_released']=True;self.enter('arrival')
        elif self.phase=='destroy_quiet':
            if time.monotonic()-self.phase_started<.9:return
            self.report.update(quiet_seconds_after_destroy=time.monotonic()-self.phase_started,pawn_destroy_callbacks_quiet=self.snapshot()==self.quiet_before)
            self.report['pawn_destroy_callbacks_after']=self.snapshot();self.report['owner_callbacks_after']=self.snapshot(True)
            self.bot.actor_destroy();self.index=1;self.start_tree()
        elif self.phase=='arrival':
            found=[w for w in ue.all_worlds() if w.get_world_type() in (1,3) and path(w)==MAP]
            if not found or self.bot_name not in self.ends or self.subject_name not in self.ends:return
            self.report.update(native_world_replaced=True,world_owner_endplay_observed=True);self.quiet_before=self.snapshot();self.enter('world_quiet')
        elif self.phase=='world_quiet':
            if time.monotonic()-self.phase_started<.9:return
            self.report.update(world_callbacks_quiet=self.snapshot()==self.quiet_before,quiet_seconds_after_world_endplay=time.monotonic()-self.phase_started,
                owned_endplay_scopes_closed=not self.scopes)
            policy.lib('KismetSystemLibrary').call_function('CollectGarbage');self.report['gc_requested']=True;self.frames=0;self.enter('gc')
        elif self.phase=='gc':
            self.frames+=1
            if self.frames<12:return
            alive=[name for name in self.old_paths if object_alive(name)];self.report['retained_old_objects']=alive
            require(not alive,'Old AI objects/World retained after native travel and GC: '+str(alive));self.report['old_world_and_ai_objects_collected']=True;self.finish()
    def cleanup(self):
        for scope in list(self.scopes.values()):scope.close()
        self.scopes={}
        for cls,value in self.cdos.items():cls.get_cdo().set_property('PythonMixinProfile',value)
        for cls,profiles in self.sources.items():
            for profile,base in profiles.items():ue.register_mixin_profile(cls,profile,base)
        for cls in self.class_roots:cls.remove_from_root()
        self.report['profiles_and_class_roots_restored']=all(c.get_cdo().get_property('PythonMixinProfile')==v for c,v in self.cdos.items()) and all(not c.is_rooted() for c in self.class_roots)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<300.,'AI lifetime total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SHOOTER_AI_LIFETIME_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SHOOTER_AI_LIFETIME_SHUTDOWN_'+self.report['status'].upper())
result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterAILifetimeResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
