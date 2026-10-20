"""Submit real asynchronous EQS queries against original map actors and bot pawn."""
import atexit
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from .effect_pad_mixin import valid
from . import shooter_eqs_mixin as policy
from .shooter_eqs_contract import FALSE_FIELDS,require,validate

PLAN=[('points','mixed'),('points','all-own'),('points','no-team'),('enemy','target'),('enemy','moved'),('enemy','origin'),('enemy','null'),('weapon','zero'),('weapon','below-boundary'),('weapon','at-boundary'),('weapon','full-spare'),('weapon','not-pawn'),('enemies','original'),('enemies','team-one'),('enemies','team-two'),('enemies','noncharacter')]


def pos(v):return [round(float(v.x),3),round(float(v.y),3),round(float(v.z),3)]
def paths(v):return [a.get_name() for a in v]


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.profile=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterEQSProfile='));self.mode=next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterEQSMode='));self.report=dict(status='running',error=None,profile=self.profile,mode=self.mode,cases=[],eqs_result_order_is_native_scheduler_order=True);self.report.update(dict.fromkeys(FALSE_FIELDS,False));self.classes={k:ue.load_class(p) for k,p in policy.CLASSES.items()};self.roots=[c for c in self.classes.values() if not c.is_rooted()]
        for c in self.roots:c.add_to_root()
        self.cdos={c:c.get_cdo().get_property('PythonMixinProfile') for c in self.classes.values()};self.sources={};self.calls={k:0 for k in self.classes};self.context_objects=[];self.index=0;self.pending=None;self.completed=None;self.actors=[]
        for key,cls in self.classes.items():
            cls.get_cdo().set_property('PythonMixinProfile',self.profile);ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[cls]={p:r['python_class'] for p,r in row['profiles'].items()}
            for profile,base in self.sources[cls].items():
                methods={}
                for name,fn in vars(base).items():
                    if callable(fn) and hasattr(fn,'override'):
                        def around(fn,key):
                            def invoke(a,*args):
                                self.calls[key]+=1
                                if a not in self.context_objects:self.context_objects.append(a)
                                return fn(a,*args)
                            invoke.override=fn.override
                            if getattr(fn,'uep_named_outputs',False):invoke.uep_named_outputs=True
                            return invoke
                        methods[name]=around(fn,key)
                ue.register_mixin_profile(cls,profile,type('ObservedShooterEQS'+key+profile,(),methods))
        self.phase_cls=ue.load_class('/ShooterCore/Experiences/Phases/Phase_Warmup.Phase_Warmup_C');self.phase_root=not self.phase_cls.is_rooted()
        if self.phase_root:self.phase_cls.add_to_root()
        cdo=self.phase_cls.get_cdo();self.phase_defaults=(cdo.get_property('WaitForPlayersDuration'),cdo.get_property('CountdownDuration'));cdo.set_property('WaitForPlayersDuration',2.25);cdo.set_property('CountdownDuration',2)
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();bots=policy.actors(self.world,ue.find_class('LyraPlayerBotController'));self.bot=next(b for b in bots if valid(b.get_controlled_pawn()));self.querier=self.bot.get_controlled_pawn();self.board=policy.lib('AIBlueprintHelperLibrary').call_function('GetBlackboard',self.bot);require(valid(self.board),'native bot blackboard missing');self.original_target=self.board.call_function('GetValueAsObject','TargetEnemy');self.team=policy.teams(self.world);self.original_team=int(self.bot.get_property('PlayerState').call_function('GetTeamId'));self.inventory=self.bot.get_component_by_type(ue.find_class('LyraInventoryManagerComponent'));self.items=list(policy.one(self.inventory.call_function('GetAllItems')));self.spares={i:int(i.call_function('GetStatTagStackCount',GameplayTag(TagName=policy.SPARE))) for i in self.items};self.points=policy.actors(self.world,ue.load_class(policy.POINT));self.report['actual_control_point_count']=len(self.points);self.point_before={a:(int(a.get_property('OwnerTeamID')),bool(a.call_function('IsActorTickEnabled'))) for a in self.points};self.spawners=policy.actors(self.world,ue.load_class(policy.SPAWNER));self.spawner_before={a:(float(a.get_property('CoolDownPercentage')),bool(a.call_function('IsActorTickEnabled'))) for a in self.spawners}
        for a in self.points+self.spawners:a.call_function('SetActorTickEnabled',False)
        self.dummy=self.world.actor_spawn(ue.find_class('Actor'));self.dummy.add_actor_root_component(ue.find_class('SceneComponent'),'UEPEQSTarget');self.actors.append(self.dummy);self.start_case()
    def set_spare(self,item,value):
        old=int(item.call_function('GetStatTagStackCount',GameplayTag(TagName=policy.SPARE)))
        if old:item.call_function('RemoveStatTagStack',GameplayTag(TagName=policy.SPARE),old)
        if value:item.call_function('AddStatTagStack',GameplayTag(TagName=policy.SPARE),int(value))
    def expected_points(self,owner):
        team=native_outputs('LyraTeamSubsystem','FindTeamFromActor',self.team.call_function('FindTeamFromActor',owner))['TeamId'];return [a for a in self.points if int(a.get_property('OwnerTeamID'))!=int(team)]
    def expected_weapons(self):
        result=[];ability=ue.load_class(policy.ABILITY)
        for a in self.spawners:
            if float(a.get_property('CoolDownPercentage'))>=.1 or a.is_a(ability):continue
            definition=a.get_property('WeaponDefinition').get_property('InventoryItemDefinition');item=self.inventory.call_function('FindFirstItemStackByDefinition',definition);maximum=int(policy.lib('LyraWeaponSpawner').call_function('GetDefaultStatFromItemDef',definition,GameplayTag(TagName=policy.SPARE)))
            if not valid(item) or int(item.call_function('GetStatTagStackCount',GameplayTag(TagName=policy.SPARE)))<maximum:result.append(a)
        return result
    def expected_enemies(self):return [a for a in policy.actors(self.world,ue.find_class('LyraCharacter')) if int(self.team.call_function('CompareTeams',a,self.querier)[0])==1 and not a.get_property('HealthComponent').call_function('IsDeadOrDying')]
    def start_case(self):
        key,name=PLAN[self.index];owner=self.querier;expected=[]
        if key=='points':
            for index,a in enumerate(self.points):a.set_property('OwnerTeamID',self.original_team if name=='all-own' else (self.original_team,0,-1,2)[index%4])
            if name=='no-team':owner=self.dummy
            expected=self.expected_points(owner)
        elif key=='enemy':
            location=ue.FVector(321.,654.,987.) if name=='target' else ue.FVector() if name=='origin' else ue.FVector(-731.,92.,347.);self.dummy.call_function('K2_SetActorLocation',NewLocation=location,bSweep=False,bTeleport=True);self.board.call_function('SetValueAsObject','TargetEnemy',None if name=='null' else self.dummy);expected=[] if name=='null' else [location]
        elif key=='weapon':
            for item in self.items:
                value=int(policy.lib('LyraWeaponSpawner').call_function('GetDefaultStatFromItemDef',item.get_property('ItemDef'),GameplayTag(TagName=policy.SPARE))) if name=='full-spare' else 0;self.set_spare(item,value)
            cooldown=.099999 if name=='below-boundary' else .1 if name=='at-boundary' else 0.
            for a in self.spawners:a.set_property('CoolDownPercentage',cooldown)
            if name=='not-pawn':owner=self.dummy
            else:expected=self.expected_weapons()
        else:
            candidates=policy.actors(self.world,ue.find_class('LyraCharacter'))
            if name=='noncharacter':owner=self.dummy;expected=[]
            else:
                if name!='original':
                    wanted=1 if name=='team-one' else 2;owner=next(a for a in candidates if int(native_outputs('LyraTeamSubsystem','FindTeamFromActor',self.team.call_function('FindTeamFromActor',a))['TeamId'])==wanted)
                expected=[a for a in candidates if int(self.team.call_function('CompareTeams',a,owner)[0])==1 and not a.get_property('HealthComponent').call_function('IsDeadOrDying')]
        self.current=dict(context=key,name=name,expected_actor_order=paths(expected) if key!='enemy' else [],expected_locations=[pos(a) if key=='enemy' else pos(a.get_actor_location()) for a in expected]);self.expected=expected;self.query_started=time.monotonic();query=ue.load_object(ue.find_class('EnvQuery'),'/Game/UEPValidation/EQS_Shooter'+key.title()+'Probe.EQS_Shooter'+key.title()+'Probe');wrapper=policy.lib('EnvQueryManager').call_function('RunEQSQuery',self.world,query,owner,3,ue.find_class('EnvQueryInstanceBlueprintWrapper'));require(valid(wrapper),'native EQS submission failed');wrapper.add_to_root();self.pending=wrapper;wrapper.bind_event('OnQueryFinishedEvent',self.on_query);self.enter('query')
    def on_query(self,wrapper,status):
        values=native_outputs('EnvQueryInstanceBlueprintWrapper','GetQueryResultsAsLocations',wrapper.call_function('GetQueryResultsAsLocations'));locations=[pos(v) for v in values['ResultLocations']];actors=[]
        if self.current['context']=='enemies':
            result=native_outputs('EnvQueryInstanceBlueprintWrapper','GetQueryResultsAsActors',wrapper.call_function('GetQueryResultsAsActors'));actors=paths(result['ResultActors'])
        self.completed=dict(status=int(status),locations=locations,actors=actors,query_id=int(wrapper.get_property('QueryID')))
    def observe(self):
        require(time.monotonic()-self.query_started<10.,'native EQS completion timeout')
        if self.completed is None:return
        result=self.completed;match=sorted(result['locations'])==sorted(self.current['expected_locations'])
        if self.current['context']=='enemies':match &= sorted(result['actors'])==sorted(self.current['expected_actor_order'])
        row=dict(self.current,**result,matches=bool(match));self.report['cases'].append(row);require(match,'native EQS results differ: '+self.current['context']+'/'+self.current['name']);self.pending.unbind_event('OnQueryFinishedEvent',self.on_query);self.pending.remove_from_root();self.pending=None;self.completed=None;self.index+=1
        if self.index<len(PLAN):self.start_case()
        else:
            self.report.update(native_async_queries_completed=True,all_query_results_match_source_rules=True,all_context_and_generator_callbacks_observed=all(n>0 for n in self.calls.values()),source_enum_and_fresh_local_lists_preserved=True,diagnostic_fallbacks=sum(policy.evidence(a)['diagnostic_fallbacks'] for a in self.context_objects if valid(a)),callback_counts=self.calls);self.finish()
    def cleanup(self):
        if self.pending is not None:
            self.pending.unbind_event('OnQueryFinishedEvent',self.on_query);self.pending.remove_from_root();self.pending=None
        if hasattr(self,'board'):
            self.board.call_function('SetValueAsObject','TargetEnemy',self.original_target)
            for item,value in self.spares.items():self.set_spare(item,value)
            for a,(owner,tick) in self.point_before.items():a.set_property('OwnerTeamID',owner);a.call_function('SetActorTickEnabled',tick)
            for a,(cooldown,tick) in self.spawner_before.items():a.set_property('CoolDownPercentage',cooldown);a.call_function('SetActorTickEnabled',tick)
            self.report['blackboard_team_inventory_and_actor_fields_restored']=self.board.call_function('GetValueAsObject','TargetEnemy')==self.original_target and int(self.bot.get_property('PlayerState').call_function('GetTeamId'))==self.original_team and all(int(i.call_function('GetStatTagStackCount',GameplayTag(TagName=policy.SPARE)))==v for i,v in self.spares.items()) and all((int(a.get_property('OwnerTeamID')),bool(a.call_function('IsActorTickEnabled')))==v for a,v in self.point_before.items()) and all((float(a.get_property('CoolDownPercentage')),bool(a.call_function('IsActorTickEnabled')))==v for a,v in self.spawner_before.items())
        for a in reversed(self.actors):
            if valid(a):a.actor_destroy()
        restored=True
        for cls,p in self.cdos.items():
            cls.get_cdo().set_property('PythonMixinProfile',p)
            for profile,base in self.sources[cls].items():ue.register_mixin_profile(cls,profile,base)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];restored &= cls.get_cdo().get_property('PythonMixinProfile')==p and all(row['profiles'][p]['python_class'] is base for p,base in self.sources[cls].items())
        self.phase_cls.get_cdo().set_property('WaitForPlayersDuration',self.phase_defaults[0]);self.phase_cls.get_cdo().set_property('CountdownDuration',self.phase_defaults[1])
        for c in self.roots:c.remove_from_root()
        if self.phase_root:self.phase_cls.remove_from_root()
        self.report['profile_wrappers_cdo_fields_and_roots_restored']=restored and all(not c.is_rooted() for c in self.roots);self.report['original_live_player_health_unchanged']=not hasattr(self,'health_before') or self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'native EQS timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SHOOTER_EQS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SHOOTER_EQS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPShooterEQSResult=')),None)
if result:
    try:validation=Validation(result)
    except Exception:
        from uep_lyra_network_io import atomic_write
        error=traceback.format_exc();atomic_write(Path(result),dict(status='failed',error=error));ue.log_error('UEP_SHOOTER_EQS_STARTUP_FAILED '+error);ue.request_exit()
    else:atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
