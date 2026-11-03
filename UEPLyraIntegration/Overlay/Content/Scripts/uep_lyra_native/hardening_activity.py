"""Same-entrypoint timing and twenty-minute native gameplay/GC activity."""
import gc
import statistics
import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from . import global_policy,rule_policies,world_policies

def start_benchmark(self):
    self.teams=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
    self.game_mode=self.statics.call_function('GetGameMode',self.world)
    self.report['timing_scope']='same native reflected fixture entrypoint; native fallback includes installed bridge admission; no bare-engine or rendered-FPS claim'
    self.report['benchmarks']=[]
    for family in ('Damage','Pawn'):
        samples={p:[] for p in ('Native','Python')};observed={p:0 for p in samples};batch=300
        def invoke():
            if family=='Damage':return self.fixture.call_function('DamageAllowed',self.teams,self.pawn,self.pawn,True)
            return self.fixture.call_function('PawnData',self.game_mode,self.controller)
        for mode in ('Native','Python'):
            ue.set_mixin_profile(self.host,family+mode)
            for _ in range(200):self.require(bool(invoke()),'benchmark warmup native result missing')
        for iteration in range(12):
            for mode in (('Native','Python') if iteration%2==0 else ('Python','Native')):
                ue.set_mixin_profile(self.host,family+mode)
                start=time.perf_counter_ns()
                for _ in range(batch):answer=invoke()
                elapsed=time.perf_counter_ns()-start;self.require(bool(answer),'benchmark native result differs')
                samples[mode].append(elapsed/batch);observed[mode]+=batch
        def stats(values):
            ordered=sorted(values)
            return dict(samples=len(values),calls=observed['Native'],median_ns_per_call=statistics.median(values),p95_batch_ns_per_call=ordered[-1],minimum_ns_per_call=min(values),maximum_ns_per_call=max(values))
        native,python=(stats(samples[k]) for k in ('Native','Python'))
        self.report['benchmarks'].append(dict(family=family,order_interleaved=True,batch_calls=batch,native=native,python=python,python_to_native_ratio=python['median_ns_per_call']/native['median_ns_per_call']))
    self.finish()

def start_soak(self):
    self.duration=float(self.arg('UEPHardeningDuration','1200'));self.teams=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',self.world,ue.find_class('LyraTeamSubsystem'))
    self.game_mode=self.statics.call_function('GetGameMode',self.world);ue.set_mixin_profile(self.host,'Python')
    self.next_activity=0.;self.next_reset=20.;self.next_sample=0.;self.collect_at=None;self.waiting_pawn=None;self.reset_at=None;self.settle_until=0.;self.gc_pass=0
    self.report.update(duration_requested=self.duration,queries=0,native_resets=0,completed_respawns=0,respawns=[],runtime_started_seconds=time.monotonic()-self.started,post_gc_samples=[],warmup_seconds=120.,phase='soak')
    self.phase='soak'

def soak_step(self):
    elapsed=time.monotonic()-self.mode_started;pawn=self.controller.get_controlled_pawn()
    if self.waiting_pawn is not None:
        self.require(elapsed-self.reset_at<15.,'native respawn exceeded scoped stability deadline')
        if valid(pawn) and pawn.get_path_name()!=self.waiting_pawn and valid(ability_system(pawn)):
            self.require(self.controller.PlayerState==self.state,'native Reset replaced persistent PlayerState')
            self.report['respawns'].append(dict(old=self.waiting_pawn,new=pawn.get_path_name(),same_player_state=True));self.report['completed_respawns']+=1;self.waiting_pawn=None;self.pawn=pawn;self.settle_until=elapsed+1.
    if self.collect_at is not None:
        if elapsed<self.collect_at:return
        gc.collect();ue.py_gc()
        if self.gc_pass==1:
            ue.find_class('KismetSystemLibrary').get_cdo().call_function('CollectGarbage');self.gc_pass=2;self.collect_at=elapsed+.25;return
        contexts=[v for v in ue.tobject_iterator(ue.find_class('UEPNativePolicyContext')) if valid(v) and not v.get_name().startswith('Default__')]
        self.report['post_gc_samples'].append(dict(elapsed=elapsed,contexts=len(contexts),actors=len(self.world.all_actors()),registrations=len(ue.get_registered_mixins()),rule_trace=len(rule_policies.metrics(self.host)['trace']),world_trace=len(world_policies.metrics(self.host)['trace']),reset_trace=len(global_policy.metrics(self.host)['trace'])))
        self.collect_at=None;self.next_sample=elapsed+10.
        if elapsed>=self.duration and self.waiting_pawn is None:
            self.report['runtime_elapsed_seconds']=elapsed;self.report['native_player_state_preserved']=self.controller.PlayerState==self.state;self.finish()
        return
    if elapsed>=self.next_sample and self.waiting_pawn is None and elapsed>=self.settle_until:
        ue.find_class('KismetSystemLibrary').get_cdo().call_function('CollectGarbage');self.collect_at=elapsed+.25;self.gc_pass=1;return
    if elapsed>=self.next_activity and valid(pawn) and self.waiting_pawn is None:
        for _ in range(50):self.require(self.fixture.call_function('DamageAllowed',self.teams,pawn,pawn,True),'sustained native query changed its result')
        self.report['queries']+=50;self.next_activity=elapsed+1.
    if elapsed>=self.next_reset and valid(pawn) and self.waiting_pawn is None and elapsed<self.duration-15:
        self.waiting_pawn=pawn.get_path_name();self.reset_at=elapsed
        tag=GameplayTag(TagName='GameplayEvent.RequestReset');ue.find_class('AbilitySystemBlueprintLibrary').get_cdo().call_function('SendGameplayEventToActor',self.state,tag,GameplayEventData(EventTag=tag,Instigator=self.state,Target=self.state))
        self.report['native_resets']+=1;self.next_reset=elapsed+20.
    self.report['runtime_elapsed_seconds']=elapsed
    if elapsed>=self.duration and self.waiting_pawn is None and self.collect_at is None:
        self.require(self.report['native_resets']==self.report['completed_respawns'],'native reset/respawn count differs')
        self.report['native_player_state_preserved']=self.controller.PlayerState==self.state;self.finish()

def install(cls,arg):
    def require(value,message):
        if not value:raise AssertionError(message)
    cls.arg=staticmethod(arg);cls.require=staticmethod(require)
    cls.start_benchmark=start_benchmark;cls.start_soak=start_soak;cls.soak_step=soak_step
