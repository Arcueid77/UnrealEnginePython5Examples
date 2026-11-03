"""Same-entrypoint timing and twenty-minute native gameplay/GC activity."""
import gc
import statistics
import time
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayEventData
from uep_lyra_world.effect_pad_mixin import valid,ability_system
from uep_lyra_network_bots import isolate_bots
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
    self.next_activity=0.;self.next_reset=20.;self.next_sample=0.;self.collect_at=None;self.waiting_pawn=None;self.reset_at=None;self.settle_until=0.;self.gc_pass=0;self.travel_started=None;self.expired_host=None;self.probed_expired_host=False;self.forced_travel=False
    self.report.update(duration_requested=self.duration,queries=0,native_resets=0,completed_respawns=0,respawns=[],runtime_started_seconds=time.monotonic()-self.started,post_gc_samples=[],warmup_seconds=120.,world_transitions=[],travel_wait_seconds=0.,phase='soak')
    self.phase='soak'

def rebind_soak_world(self,elapsed):
    if self.travel_started is None:
        self.require(self.waiting_pawn is None,'native Reset was interrupted by world travel')
        self.travel_started=time.monotonic();self.collect_at=None;self.expired_host=self.host;self.probed_expired_host=False
        # Public selectors must reject the dead wrapper before touching its
        # raw native pointer. Keep this in the real world teardown exercise.
    if not self.probed_expired_host and not valid(self.expired_host):
            rejected=0
            for call in (lambda:ue.get_mixin_profile(self.expired_host),lambda:ue.set_mixin_profile(self.expired_host,'Python'),lambda:ue.clear_mixin_profile(self.expired_host)):
                try:call()
                except (TypeError,RuntimeError):rejected+=1
            self.require(rejected==3,'expired world policy wrapper was accepted by a selector')
            self.report['expired_selector_rejections']=self.report.get('expired_selector_rejections',0)+rejected
            self.probed_expired_host=True
    self.require(time.monotonic()-self.travel_started<120.,'world travel did not restore native readiness')
    for world in ue.all_worlds():
        if not valid(world) or world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
        bridge=ue.find_class('UEPLyraBridgeLibrary').get_cdo().call_function('GetBridgeForWorld',world)
        if not valid(bridge):continue
        snap=bridge.call_function('CaptureSnapshot')
        if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
        controller=self.statics.call_function('GetPlayerController',world,0);mode=self.statics.call_function('GetGameMode',world)
        teams=ue.find_class('SubsystemBlueprintLibrary').get_cdo().call_function('GetWorldSubsystem',world,ue.find_class('LyraTeamSubsystem'))
        if not all(valid(v) for v in (controller,mode,teams)):continue
        host=ue.find_class('UEPNativeGameplayPolicySubsystem').get_cdo().call_function('GetPolicyForContext',world)
        if not valid(host):continue
        wait=time.monotonic()-self.travel_started
        self.report['world_transitions'].append(dict(active_elapsed=elapsed-wait,wait_seconds=wait,old_world_invalid=not valid(self.world),new_world=world.get_path_name()))
        self.report['travel_wait_seconds']+=wait;self.mode_started+=wait;self.travel_started=None
        self.world=world;self.controller=controller;self.pawn=controller.get_controlled_pawn();self.state=controller.PlayerState;self.game_mode=mode;self.teams=teams
        self.host=host;self.original_profile=str(ue.get_mixin_profile(host));ue.set_mixin_profile(host,'Python')
        isolate_bots(self.statics,world,ue.find_class('AIController'))
        self.next_sample=elapsed-wait+1.;self.next_reset=elapsed-wait+20.;self.settle_until=elapsed-wait+1.
        return


def soak_step(self):
    elapsed=time.monotonic()-self.mode_started
    if self.travel_started is not None or not all(valid(v) for v in (self.world,self.controller,self.game_mode,self.teams,self.host)) or self.controller.get_world()!=self.world:
        rebind_soak_world(self,elapsed);return
    pawn=self.controller.get_controlled_pawn()
    travel_after=float(self.arg('UEPHardeningTravelAfter','0'))
    if travel_after and elapsed>=travel_after and not self.forced_travel and self.waiting_pawn is None:
        self.forced_travel=True;self.require(self.world.server_travel('/ShooterMaps/Maps/L_Expanse?NumBots=3'),'forced native travel was rejected');return
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
