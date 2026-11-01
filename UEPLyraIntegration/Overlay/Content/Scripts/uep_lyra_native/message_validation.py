"""Actual native subscriptions and fixed-step boundaries; messages are test inputs."""
import atexit
import copy
from pathlib import Path
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,LyraVerbMessage
from uep_runtime import SubscriptionScope
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from . import message_processors as policy
from .message_validation_contract import require,validate

ELIM='Lyra.Elimination.Message';DAMAGE='Lyra.Damage.Message';ASSIST='Lyra.Assist.Message'


def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))
def tags(value):return sorted(str(t.TagName) for t in value.GameplayTags)


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeMessageResult'));self.profile=arg('UEPNativeMessageProfile')
        require(self.profile in ('Python','NativeFallback'),'explicit native rule profile required')
        self.started=time.monotonic();self.ready=False;self.finished=False;self.scope=None;self.saved=[]
        self.profiles=[];self.classes={};self.components={};self.phase=0;self.phase_events=[];self.monitoring=False
        self.calls={k:dict(elimination=0,damage=0) for k in policy.CLASSES}
        self.report=dict(status='running',error=None,profile=self.profile,world_mode='Standalone',
            synthetic_native_messages=True,actual_damage_or_network_acceptance=False,nested_damage_sent=False,
            inputs=[],phases=[],end_play={k:[] for k in policy.CLASSES},scope_closed=False,
            callbacks_after_destroy=-1,selectors_restored=False,profiles_restored=False,step=1/64)
        for kind,path in policy.CLASSES.items():
            cls=ue.load_class(path);self.classes[kind]=cls;ue.register_declared_mixin(cls)
            self.saved.append((cls,cls.get_cdo().get_property('PythonMixinProfile')))
            cls.get_cdo().set_property('PythonMixinProfile',self.profile)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls]
            base=row['profiles'][self.profile]['python_class'];self.profiles.append((cls,base))
            methods={n:v for n,v in vars(base).items() if callable(v)}
            for name,key in ((policy.ELIMINATION,'elimination'),(policy.DAMAGE,'damage')):
                if name in methods:methods[name]=self.observe(kind,key,methods[name])
            original_end=methods['ReceiveEndPlay']
            def end(component,EndPlayReason,fn=original_end,k=kind):
                result=fn(component,EndPlayReason)
                self.report['end_play'][k].append(not policy.state(component))
                return result
            methods['ReceiveEndPlay']=end
            ue.register_mixin_profile(cls,self.profile,type('ObservedNativeMessage'+kind+self.profile,(),methods))
        atexit.register(self.finalize)

    def observe(self,kind,key,original):
        def callback(component,Channel,Payload):
            if self.monitoring:self.calls[kind][key]+=1
            return original(component,Channel,Payload)
        return callback

    def model(self,p):
        return dict(verb=str(p.Verb.TagName),instigator=self.labels.get(p.Instigator,'other') if p.Instigator is not None else None,
            target=self.labels.get(p.Target,'other') if p.Target is not None else None,magnitude=float(p.Magnitude),
            instigator_tags=tags(p.InstigatorTags),target_tags=tags(p.TargetTags),context_tags=tags(p.ContextTags))

    def receive(self,channel,payload):
        self.phase_events.append(self.model(payload))
        if str(channel.TagName)==ASSIST and not self.report['nested_damage_sent']:
            self.report['nested_damage_sent']=True
            self.send(DAMAGE,'C','D',4.)

    def send(self,channel,instigator,target,magnitude=1.):
        self.report['inputs'].append(dict(channel=channel,instigator=instigator,target=target,magnitude=magnitude))
        payload=LyraVerbMessage(Verb=GameplayTag(TagName=channel),Instigator=self.objects[instigator],
            Target=self.objects[target],Magnitude=magnitude,
            InstigatorTags=GameplayTagContainer(GameplayTags=[GameplayTag(TagName=ELIM)]),
            TargetTags=GameplayTagContainer(GameplayTags=[GameplayTag(TagName=DAMAGE)]),
            ContextTags=GameplayTagContainer(GameplayTags=[GameplayTag(TagName=ASSIST)]))
        self.adapter.call_function('BroadcastVerb',self.router,GameplayTag(TagName=channel),payload)

    def setup(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            state=policy.lib('GameplayStatics').call_function('GetGameState',world)
            if not valid(state):continue
            found={}
            for kind,cls in self.classes.items():
                rows=[c for c in ue.tobject_iterator(cls) if valid(c) and c.get_world()==world and valid(c.call_function('GetOwner'))]
                if len(rows)!=1:break
                found[kind]=rows[0]
            if len(found)!=3:continue
            players=[p for p in state.get_property('PlayerArray') if valid(p) and p.is_a(ue.find_class('PlayerState'))]
            if len(players)<4:continue
            self.world=world;self.components=found
            self.players=sorted(players,key=lambda p:(int(p.call_function('GetPlayerId')),p.get_path_name()))[:4]
            self.objects=dict(zip(('A','B','C','D'),self.players));self.objects['state']=state
            self.labels={p:k for k,p in self.objects.items()}
            self.report['isolated_bots']=isolate_bots(policy.lib('GameplayStatics'),world,ue.find_class('AIController'))
            for c in found.values():ue.set_mixin_profile(c,self.profile)
            self.report['window']=float(found['chain'].get_property('ChainTimeLimit'))
            self.report['thresholds']={k:{str(i):str(tag.TagName) for i,tag in found[k].get_property(field).items()}
                for k,field in (('streak','ElimStreakTags'),('chain','ElimChainTags'))}
            self.adapter=ue.load_class(policy.ADAPTER).get_cdo()
            self.router=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',world,ue.find_class('GameplayMessageSubsystem'))
            self.scope=SubscriptionScope()
            channels={ASSIST,*self.report['thresholds']['streak'].values(),*self.report['thresholds']['chain'].values()}
            def reader(proxy):
                payload,ok=self.adapter.call_function('ReadVerb',proxy);require(ok,'typed native reward extraction failed');return payload
            for channel in sorted(channels):
                self.scope.listen_gameplay_message(world,channel,ue.find_struct('LyraVerbMessage'),reader,self.receive)
            self.before={k:copy.deepcopy(policy.metrics(c)) for k,c in found.items()}
            self.ready=True;self.monitoring=True;return True
        return False

    def capture(self,name,clock,expected):
        self.report['phases'].append(dict(name=name,clock=clock,expected_clock=expected,emissions=self.phase_events))
        self.phase_events=[]

    def initial(self):
        now=policy.clock(self.components['chain']);require(now>0,'positive native server time required')
        self.start_clock=now
        self.send(DAMAGE,'C','D',.1);self.send(DAMAGE,'C','D',.2);self.send(DAMAGE,'A','D',10.)
        for _ in range(5):self.send(ELIM,'A','D')
        self.send(ELIM,'B','A');self.send(ELIM,'A','A');self.send(ELIM,'state','D')
        self.send(ELIM,'B','D');self.send(ELIM,'C','D')
        self.capture('initial',now,now);self.phase=1

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<180,'native message fixture timed out')
            if not self.ready:
                if not self.setup():return True
            if self.phase==0:self.initial()
            else:
                offset={1:-1/64,2:0.,3:1/64}[self.phase]
                expected=self.start_clock+self.report['window']+offset
                now=policy.clock(self.components['chain'])
                if now<expected:return True
                require(now==expected,'fixed native clock skipped exact boundary')
                name={1:'before',2:'equal',3:'after'}[self.phase]
                self.send(ELIM,{1:'A',2:'B',3:'C'}[self.phase],'D')
                self.capture(name,now,expected);self.phase+=1
                if self.phase==4:self.finish()
            atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def cleanup(self):
        if not self.ready:return
        self.report['metrics']={k:{n:value-self.before[k][n] for n,value in policy.metrics(c).items()} for k,c in self.components.items()}
        self.scope.close();self.scope.close();self.report['scope_closed']=self.scope.closed and self.scope.count==0
        for component in self.components.values():component.call_function('K2_DestroyComponent',component.call_function('GetOwner'))
        before=copy.deepcopy(self.calls)
        self.send(DAMAGE,'C','D',1.);self.send(ELIM,'A','D')
        self.report['callbacks_after_destroy']=sum(self.calls[k][n]-before[k][n] for k in before for n in before[k])
        for cls,base in self.profiles:ue.register_mixin_profile(cls,self.profile,base)
        self.report['profiles_restored']=all(next(r for r in ue.get_registered_mixins() if r['target_class']==cls)['profiles'][self.profile]['python_class'] is base for cls,base in self.profiles)
        for cls,previous in self.saved:cls.get_cdo().set_property('PythonMixinProfile',previous)
        self.report['selectors_restored']=all(cls.get_cdo().get_property('PythonMixinProfile')==previous for cls,previous in self.saved)

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error)
        atomic_write(self.path,self.report)
        (ue.log_error if error else ue.log)('UEP_NATIVE_MESSAGE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'))
        ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report)
        (ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_MESSAGE_SHUTDOWN_'+self.report['status'].upper())


if any(value.startswith('-UEPNativeMessageResult=') for value in sys.argv):
    validation=Validation()
    ticker=ue.add_ticker(validation.tick)
