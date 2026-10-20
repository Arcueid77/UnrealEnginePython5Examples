"""Actual bot/controller, native BT instances and real GAS event observations."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from .effect_pad_mixin import valid
from . import shooter_ai_mixin as policy
from .shooter_ai_contract import FALSE_FIELDS,require,validate

TREE='/Game/UEPValidation/BT_ShooterAIProbe.BT_ShooterAIProbe'


def count(a,key):return sum(policy.evidence(a)[p+'_'+key] for p in ('python','fallback'))


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.profile=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterAIProfile='));self.mode=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterAIMode='));self.report=dict(status='running',error=None,profile=self.profile,mode=self.mode,ammo_cases=[],weapon_cases=[],gas_events=[],direct_bt_callback_fixtures_also_used=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={};self.sources={};self.cdos={};self.manual=[];self.actions=[];self.actors=[];self.observed={};self.armed=False;self.created=None;self.install()
    def install(self):
        self.classes={key:ue.load_class(path) for key,path in policy.CLASSES.items()};self.class_roots=[cls for cls in self.classes.values() if not cls.is_rooted()]
        for cls in self.class_roots:cls.add_to_root()
        self.cdos={cls:cls.get_cdo().get_property('PythonMixinProfile') for cls in self.classes.values()}
        for cls in self.cdos:cls.get_cdo().set_property('PythonMixinProfile',self.profile)
        for key,cls in self.classes.items():
            if key in ('passive','cp'):continue
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[cls]={p:r['python_class'] for p,r in row['profiles'].items()}
            for profile,base in self.sources[cls].items():
                methods={}
                for name,fn in vars(base).items():
                    if callable(fn) and hasattr(fn,'override'):
                        keyname=next(k for k,v in policy.GATES.items() if v==fn.override)
                        def around(fn,keyname):
                            def invoke(a,*args):
                                self.observed.setdefault((a.get_path_name(),keyname),[]).append(time.monotonic());return fn(a,*args)
                            invoke.override=fn.override
                            if getattr(fn,'uep_named_outputs',False):invoke.uep_named_outputs=True
                            return invoke
                        methods[name]=around(fn,keyname)
                ue.register_mixin_profile(cls,profile,type('ObservedShooterAI'+key+profile,(),methods))
        self.phase_cls=ue.load_class('/ShooterCore/Experiences/Phases/Phase_Warmup.Phase_Warmup_C');self.phase_rooted=not self.phase_cls.is_rooted()
        if self.phase_rooted:self.phase_cls.add_to_root()
        cdo=self.phase_cls.get_cdo();self.phase_defaults=(cdo.get_property('WaitForPlayersDuration'),cdo.get_property('CountdownDuration'));cdo.set_property('WaitForPlayersDuration',2.25);cdo.set_property('CountdownDuration',2)
    def all_bots(self):return policy.one(self.statics.call_function('GetAllActorsOfClass',self.world,self.classes['controller']))
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();bots=[c for c in self.all_bots() if valid(c.get_controlled_pawn()) and policy.inventory(c) is not None];require(bots,'real initialized bot required');self.bot=bots[0];self.subject=self.bot.get_controlled_pawn();self.brain=self.bot.get_property('BrainComponent');self.inventory=policy.inventory(self.bot);self.quickbar=self.bot.get_component_by_type(ue.find_class('LyraQuickBarComponent'));require(valid(self.brain) and valid(self.quickbar),'native bot brain/quickbar missing');self.report['natural_controller_class']=self.bot.get_class().get_name();self.report['natural_controller_ready_possess_and_team_observed']=all(count(self.bot,k)>0 for k in ('ready','possess','team'));self.original_items=policy.items(self.inventory);self.original_slots=list(policy.one(self.quickbar.call_function('GetSlots')));self.original_active=int(self.quickbar.call_function('GetActiveSlotIndex'));self.stat_before={i:(policy.stacks(i,policy.MAGAZINE),policy.stacks(i,policy.SPARE)) for i in self.original_items};self.position=self.subject.get_actor_location();self.rotation=self.subject.get_actor_rotation();self.control_rotation=self.bot.call_function('GetControlRotation');self.move=self.subject.get_component_by_type(ue.find_class('CharacterMovementComponent'));self.move_mode=int(self.move.get_property('MovementMode'));self.custom_mode=int(self.move.get_property('CustomMovementMode'));self.move.call_function('SetMovementMode',0,0);self.subject.call_function('K2_SetActorLocation',NewLocation=ue.FVector(250000.,250000.,3000.),bSweep=False,bTeleport=True);self.bot.call_function('SetControlRotation',ue.FRotator(0.,90.,0.));self.dummy=self.world.actor_spawn(ue.find_class('Actor'));self.actors.append(self.dummy);self.dummy.add_actor_root_component(ue.find_class('SceneComponent'),'UEPAISafeFocus');self.dummy.call_function('K2_SetActorLocation',NewLocation=ue.FVector(250000.,251000.,3000.),bSweep=False,bTeleport=True)
        for name in (policy.FIRE,policy.RELOAD,policy.SLOT):self.listen(name)
        self.zero_items();tree=ue.load_object(ue.find_class('BehaviorTree'),TREE);require(self.bot.call_function('RunBehaviorTree',tree),'native fixture tree start failed');self.brain=self.bot.get_property('BrainComponent');self.brain.call_function('StopLogic','UEP AI direct matrix');self.board=policy.lib('AIBlueprintHelperLibrary').call_function('GetBlackboard',self.bot);require(valid(self.board),'native fixture blackboard missing');self.nodes={}
        for key in ('ammo','reload','focus','shoot','allowed'):
            node=ue.new_object(self.classes[key],self.brain);node.add_to_root();self.manual.append(node);ue.set_mixin_profile(node,self.profile);self.nodes[key]=node
            if key in ('ammo','shoot'):node.set_property('OutOfAmmo',ue.find_struct('BlackboardKeySelector')(SelectedKeyName='OutOfAmmo'))
            if key in ('focus','shoot'):node.set_property('TargetEnnemy',ue.find_struct('BlackboardKeySelector')(SelectedKeyName='TargetEnemy'))
        self.passive_case();self.setup_alternate();self.enter('equipment')
    def listen(self,name):
        proxy=policy.lib('AbilityAsync_WaitGameplayEvent').call_function('WaitGameplayEventToActor',self.subject,GameplayTag(TagName=name),False,True);require(valid(proxy),'native gameplay-event listener missing');proxy.add_to_root()
        def receive(payload):
            if self.armed:self.report['gas_events'].append(dict(tag=name,magnitude=float(payload.EventMagnitude),payload_tag=str(payload.EventTag.TagName),instigator_null=payload.Instigator is None,target_null=payload.Target is None))
        proxy.bind_event('EventReceived',receive);proxy.call_function('Activate');self.actions.append((proxy,receive))
    def set_stat(self,item,name,value):
        old=policy.stacks(item,name)
        if old:item.call_function('RemoveStatTagStack',GameplayTag(TagName=name),old)
        if value:item.call_function('AddStatTagStack',GameplayTag(TagName=name),int(value))
    def set_counts(self,item,mag,spare):self.set_stat(item,policy.MAGAZINE,mag);self.set_stat(item,policy.SPARE,spare)
    def zero_items(self):
        for item in policy.items(self.inventory):self.set_counts(item,0,0)
    def passive_case(self):
        passive=self.world.actor_spawn(self.classes['passive']);pawn=self.world.actor_spawn(ue.find_class('Pawn'));self.actors.extend((passive,passive.get_property('PlayerState'),pawn));passive.call_function('Possess',pawn);before=count(passive,'death');passive.call_function('UnPossess');self.report['passive_empty_overrides_preserved']=count(passive,'ready')==0 and count(passive,'death')==before and passive.get_property('BTAsset') is None
    def setup_alternate(self):
        current=self.quickbar.call_function('GetActiveSlotItem');require(valid(current),'bot active inventory item absent');self.base_item=current;definition=current.get_property('ItemDef');self.created=self.inventory.call_function('AddItemDefinition',definition,1);slot=int(self.quickbar.call_function('GetNextFreeItemSlot'));require(valid(self.created) and slot>=0,'alternate bot item/slot fixture absent');self.created_slot=slot;self.quickbar.call_function('AddItemToSlot',slot,self.created);self.zero_items();self.quickbar.call_function('SetActiveSlotIndex',self.original_active)
    def reset_active(self):self.quickbar.call_function('SetActiveSlotIndex',self.original_active)
    def matrix(self):
        ammo=self.nodes['ammo'];shoot=self.nodes['shoot'];focus=self.nodes['focus'];self.armed=True
        for mag,spare,other in ((0,0,0),(0,7,0),(3,0,0),(0,0,11)):
            self.zero_items();self.set_counts(self.base_item,mag,spare);self.set_counts(self.created,other,0);ammo.set_property('TotalAmmo',999);ammo.call_function('ReceiveTickAI',self.bot,self.subject,.123);out=bool(self.board.call_function('GetValueAsBool','OutOfAmmo'));self.report['ammo_cases'].append(dict(mag=mag,spare=spare,other=other,total=int(ammo.get_property('TotalAmmo')),out=out));require(int(ammo.get_property('TotalAmmo'))==mag+spare+other and out==((mag+spare+other)<=0),'native total-ammo/blackboard mismatch')
        for key,setfocus in (('set',True),('clear',False)):
            self.board.call_function('SetValueAsObject','TargetEnemy',self.dummy);focus.set_property('SetFocus',setfocus);focus.call_function('ReceiveActivationAI',self.bot,self.subject);require(self.bot.call_function('GetFocusActor')==(self.dummy if setfocus else None),'native AI focus differs')
        self.report['native_focus_set_and_clear_match']=True
        for name,mag,spare,other,expected in (('loaded',3,0,0,True),('spare-only',0,7,0,True),('empty',0,0,0,False),('alternate',0,0,5,True),('empty-again',0,0,0,False)):
            self.reset_active();self.zero_items();self.set_counts(self.base_item,mag,spare);self.set_counts(self.created,other,0);self.board.call_function('SetValueAsBool','OutOfAmmo',True);before=len(self.report['gas_events']);can=bool(policy.one(shoot.call_function('GetCurrentWeapon',self.subject,self.bot)));events=self.report['gas_events'][before:];self.report['weapon_cases'].append(dict(name=name,can=can,out=bool(self.board.call_function('GetValueAsBool','OutOfAmmo')),events=events));require(can==expected,'native AI weapon decision differs')
        self.reset_active();self.zero_items();self.set_counts(self.base_item,3,0);before=len(self.report['gas_events']);shoot.call_function('ReceiveTickAI',self.bot,self.subject,.123);self.nodes['reload'].call_function('ReceiveActivationAI',self.bot,self.subject);delivered={e['tag'] for e in self.report['gas_events'][before:]};require(policy.FIRE in delivered and policy.RELOAD in delivered,'native BT fire/reload GAS delivery missing');self.report['native_gas_reload_slot_fire_payloads_observed']=any(e['tag']==policy.SLOT for e in self.report['gas_events']) and policy.FIRE in delivered and policy.RELOAD in delivered;self.report['native_ammo_blackboard_cases_match']=True;self.report['native_weapon_query_and_slot_cases_match']=True;self.zero_items();self.report['tree_started_monotonic']=time.monotonic();self.bot.call_function('RunBehaviorTree',ue.load_object(ue.find_class('BehaviorTree'),TREE));self.enter('tree')
    def observe(self):
        require(time.monotonic()-self.phase_started<15.,'native AI phase timeout: '+self.phase)
        if self.phase=='equipment':self.matrix()
        elif self.phase=='tree':
            instances=list(self.brain.get_property('NodeInstances'));ticks=[t for n in instances if n.get_class()==self.classes['ammo'] for t in self.observed.get((n.get_path_name(),'ammo'),[]) if t>=self.report['tree_started_monotonic']]
            if len(ticks)<4:return
            intervals=[b-a for a,b in zip(ticks[-3:],ticks[-2:])];self.report['native_tree_intervals']=intervals;self.report['native_tree_tick_samples']=len(ticks);self.report['native_tree_service_callbacks_and_intervals_observed']=all(.35<=v<=.75 for v in intervals);self.brain.call_function('StopLogic','UEP AI lifecycle matrix');self.board.call_function('SetValueAsObject','TargetEnemy',self.dummy);before=count(self.bot,'death');self.bot.call_function('UnPossess');self.report['native_unpossess_clears_enemy_and_stops_brain']=count(self.bot,'death')==before+1 and self.board.call_function('GetValueAsObject','TargetEnemy') is None and not self.brain.call_function('IsRunning');before=count(self.bot,'possess');self.bot.call_function('Possess',self.subject);self.brain.call_function('StopLogic','UEP AI restore barrier');self.report['native_repossess_and_team_observer_observed']=count(self.bot,'possess')==before+1 and count(self.bot,'team')>0;self.report['diagnostic_fallbacks']=sum(policy.evidence(n)['diagnostic_fallbacks'] for n in self.manual+[self.bot]);self.finish()
    def cleanup(self):
        self.armed=False
        for proxy,fn in self.actions:
            if valid(proxy):proxy.unbind_event('EventReceived',fn);proxy.call_function('EndAction');proxy.remove_from_root()
        self.report['probe_gameplay_event_actions_closed']=all(not valid(p) or not p.is_rooted() for p,_ in self.actions)
        if hasattr(self,'brain') and valid(self.brain):self.brain.call_function('StopLogic','UEP AI cleanup')
        for node in self.manual:ue.clear_mixin_profile(node);node.remove_from_root()
        if self.created is not None:
            self.quickbar.call_function('SetActiveSlotIndex',self.original_active);self.quickbar.call_function('RemoveItemFromSlot',self.created_slot);self.inventory.call_function('RemoveItemInstance',self.created)
        if hasattr(self,'stat_before'):
            for item,(mag,spare) in self.stat_before.items():self.set_counts(item,mag,spare)
            self.subject.call_function('K2_SetActorLocation',NewLocation=self.position,bSweep=False,bTeleport=True);self.subject.call_function('K2_SetActorRotation',self.rotation,True);self.bot.call_function('SetControlRotation',self.control_rotation);self.move.call_function('SetMovementMode',self.move_mode,self.custom_mode);self.report['inventory_slots_stats_and_transforms_restored']=policy.items(self.inventory)==self.original_items and list(policy.one(self.quickbar.call_function('GetSlots')))==self.original_slots and all((policy.stacks(i,policy.MAGAZINE),policy.stacks(i,policy.SPARE))==v for i,v in self.stat_before.items())
        for actor in reversed(self.actors):
            if valid(actor):actor.actor_destroy()
        restored=True
        for cls,p in self.cdos.items():
            cls.get_cdo().set_property('PythonMixinProfile',p)
        for cls,profiles in self.sources.items():
            for profile,base in profiles.items():ue.register_mixin_profile(cls,profile,base)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];restored &= all(row['profiles'][p]['python_class'] is base for p,base in profiles.items())
        restored &= all(cls.get_cdo().get_property('PythonMixinProfile')==p for cls,p in self.cdos.items())
        self.phase_cls.get_cdo().set_property('WaitForPlayersDuration',self.phase_defaults[0]);self.phase_cls.get_cdo().set_property('CountdownDuration',self.phase_defaults[1])
        for cls in self.class_roots:cls.remove_from_root()
        if self.phase_rooted:self.phase_cls.remove_from_root()
        self.report['profile_selectors_wrappers_and_roots_restored']=restored and all(not n.is_rooted() for n in self.manual+self.class_roots);self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native AI timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SHOOTER_AI_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SHOOTER_AI_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterAIResult=')),None)
if result:
    try:validation=Validation(result)
    except Exception:
        from uep_lyra_network_io import atomic_write
        error=traceback.format_exc();atomic_write(Path(result),dict(status='failed',error=error));ue.log_error('UEP_SHOOTER_AI_STARTUP_FAILED '+error);ue.request_exit()
    else:atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
