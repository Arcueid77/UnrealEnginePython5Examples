"""Paired live hosts, native registry/asset callbacks, timers and UMG lifecycle."""
import atexit
import copy
import json
from pathlib import Path
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,LyraNotificationMessage,LyraVerbMessage
from uep_lyra_network_io import atomic_write
from uep_lyra_network_bots import isolate_bots
from uep_lyra_world.effect_pad_mixin import valid
from .message_validation import arg
from . import accolades as policy
from .accolade_validation_contract import require,validate

ROOT='Lyra.ShooterGame.Accolade'


def tag(value):return GameplayTag(TagName=value)
def lib(name):return ue.find_class(name).get_cdo()


class Validation:
    def __init__(self):
        self.path=Path(arg('UEPNativeAccoladeResult'));self.started=time.monotonic();self.finished=False;self.phase='ready';self.widgets=[];self.events=[];self.boot=[];self.foreign=None;self.recording=False
        self.report=dict(status='running',error=None,cases=[],timer_callbacks_replayed=False,native_registry_replaced=False,localized_text_roundtripped=False,network_acceptance=False)
        atexit.register(self.finalize)

    def now(self):return float(lib('GameplayStatics').call_function('GetTimeSeconds',self.world))
    def enter(self,phase):self.phase=phase;self.phase_started=time.monotonic()
    def event(self,w,kind,entry=None):
        if self.recording and w in self.widgets:
            row=dict(profile=str(ue.get_mixin_profile(w)),kind=kind,time=self.now())
            if entry is not None:
                row.update(sequence=int(entry.SequenceID),text=lib('KismetTextLibrary').call_function('Conv_TextToString',entry.Row.DisplayName),duration=float(entry.Row.DisplayDuration))
            self.events.append(row)

    def setup(self):
        for world in ue.all_worlds():
            if world.get_world_type() not in (1,3) or 'L_Expanse' not in world.get_name():continue
            isolate_bots(lib('GameplayStatics'),world,ue.find_class('AIController'))
            bridge=lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',world)
            if not valid(bridge):continue
            snap=bridge.call_function('CaptureSnapshot')
            if not (snap.bExperienceLoaded and snap.bHeroInputReady and snap.bAbilitySystemReady and snap.bHealthReady and snap.Health>0 and not snap.bDamageImmune):continue
            self.world=world;self.controller=lib('GameplayStatics').call_function('GetPlayerController',world,0);self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
            self.previous=self.cls.get_cdo().get_property('PythonMixinProfile')
            if not self.cls.is_rooted():self.cls.add_to_root();self.boot=[self.cls]
            registered,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={p:v['python_class'] for p,v in registered['profiles'].items()}
            for profile,base in self.sources.items():
                attrs={k:v for k,v in vars(base).items() if not k.startswith('__')}
                def around(fn,kind):
                    def invoke(widget,*args):
                        self.event(widget,kind,args[0] if kind=='create' else None);result=fn(widget,*args)
                        if kind=='create' and widget in self.widgets:
                            entry=args[0];toast=widget.get_property('MyToast');payload=dict(text_equal=bool(lib('KismetTextLibrary').call_function('EqualEqual_TextText',toast.get_property('TextWidget').call_function('GetText'),entry.Row.DisplayName)),icon_equal=toast.get_property('IconWidget').get_property('Brush').ResourceObject==entry.Icon,widget_owned=result.get('Widget')==toast)
                            require(all(payload.values()),'native accolade text/icon/widget ownership differs');self.report.setdefault('presentation_samples',[]).append(payload)
                        return result
                    invoke.override=fn.override;invoke.uep_named_outputs=bool(getattr(fn,'uep_named_outputs',False));return invoke
                attrs['Create']=around(base.Create,'create');attrs['Destroy']=around(base.Destroy,'destroy')
                ue.register_mixin_profile(self.cls,profile,type('ObservedNativeAccolade'+profile,(),attrs))
            table=ue.load_object(ue.find_class('DataTable'),'/ShooterCore/Accolades/DT_BasicShooterAccolades.DT_BasicShooterAccolades');self.rows=table.data_table_as_dict()
            self.chain2=self.row('EliminationChain.2x');self.chain3=self.row('EliminationChain.3x');self.streak=self.row('EliminationStreak.5')
            self.sender=ue.load_class('/Game/UEPValidation/BP_AccoladeRelayProbe.BP_AccoladeRelayProbe_C').get_cdo();self.sender_root=not self.sender.is_rooted()
            if self.sender_root:self.sender.add_to_root()
            self.router=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',world,ue.find_class('GameplayMessageSubsystem'));self.foreign=world.actor_spawn(ue.find_class('PlayerState'))
            for profile in ('NativeFallback','Python'):
                w=lib('WidgetBlueprintLibrary').call_function('Create',world,self.cls,self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,profile);w.call_function('AddToPlayerScreen',0)
                require(str(w.LocationName.TagName)==str(self.chain2.LocationTag.TagName),'native host/data location differs')
            self.reset();self.filters();self.events=[];self.recording=True;self.publish('EliminationChain.2x');self.publish('EliminationStreak.5');self.enter('fifo');return True
        return False

    def row(self,suffix):return next(r.clone() for key,r in self.rows.items() if str(key).endswith(suffix))
    def text(self,row):return lib('KismetTextLibrary').call_function('Conv_TextToString',row.DisplayName)
    def selected_events(self,w):return [e for e in self.events if e['profile']==str(ue.get_mixin_profile(w))]
    def empty(self):return all(not w.get_property(policy.LOADS) and not w.get_property(policy.DISPLAYS) for w in self.widgets)
    def reset(self):
        self.recording=False
        for w in self.widgets:
            w.call_function('RemoveFromParent');require(not w.get_property(policy.LOADS) and not w.get_property(policy.DISPLAYS),'native destruct left pending entries')
            w.call_function('AddToPlayerScreen',0)
        self.events=[];self.recording=True

    def filters(self):
        results=[]
        for w in self.widgets:
            before=int(w.get_property(policy.ALLOCATED))
            for channel,target in (('Lyra.Elimination.Message',None),(ROOT,self.foreign)):
                w.call_function('OnNotificationMessage',tag('Lyra.AddNotification.Message'),LyraNotificationMessage(TargetChannel=tag(channel),TargetPlayer=target,PayloadTag=tag(ROOT+'.EliminationChain.2x')))
            orphan=ue.new_object(self.cls);orphan.add_to_root()
            try:
                ue.set_mixin_profile(orphan,str(ue.get_mixin_profile(w)));require(orphan.call_function('GetOwningPlayer') is None,'ownerless fixture unexpectedly has a player context')
                orphan.call_function('OnNotificationMessage',tag('Lyra.AddNotification.Message'),LyraNotificationMessage(TargetChannel=tag(ROOT),TargetPlayer=self.controller.PlayerState,PayloadTag=tag(ROOT+'.EliminationChain.2x')))
                results.append(int(w.get_property(policy.ALLOCATED))==before and not w.get_property(policy.LOADS) and int(orphan.get_property(policy.ALLOCATED))==0 and not orphan.get_property(policy.LOADS))
            finally:orphan.remove_from_root()
        self.report['cases'].append(dict(name='filter_channel_foreign_and_no_owner',results=results));require(all(results),'native notification filter differs')

    def publish(self,suffix,source=None):
        full=ROOT+'.'+suffix;self.sender.call_function('BroadcastVerb',self.router,tag(full),LyraVerbMessage(Verb=tag(full),Instigator=self.controller.PlayerState if source is None else source))
    def queue(self,row,sequence):
        for w in self.widgets:w.call_function('UEPQueueAccoladeRow',row,sequence)
    def simple(self,row,duration=.25):
        value=row.clone();value.DisplayDuration=duration;value.AccoladeTags=GameplayTagContainer();value.CancelAccoladesWithTag=GameplayTagContainer();return value
    def record(self,name,expected):
        pairs=[]
        for w in self.widgets:
            events=self.selected_events(w);creates=[e for e in events if e['kind']=='create'];destroys=[e for e in events if e['kind']=='destroy']
            actual=[e['text'] for e in creates];require(actual==expected,'native accolade create order differs: '+name+' '+str(actual))
            pairs.append(dict(profile=str(ue.get_mixin_profile(w)),create_order=actual,kinds=[e['kind'] for e in events],sequences=[e['sequence'] for e in creates],duration_checks=len(creates)==len(destroys) and all(a['duration']-.05<=b['time']-a['time']<=a['duration']+.4 for a,b in zip(creates,destroys))))
        self.report['cases'].append(dict(name=name,pairs=pairs))

    def observe(self):
        self.report['live_events']=list(self.events)
        self.report['live_hosts']=[dict(profile=str(ue.get_mixin_profile(w)),metrics=copy.deepcopy(policy.metrics(w)),allocated=int(w.get_property(policy.ALLOCATED)),next=int(w.get_property(policy.NEXT)),loads=[dict(sequence=int(e.SequenceID),finished=bool(e.bFinishedLoading)) for e in w.get_property(policy.LOADS)],displays=[int(e.SequenceID) for e in w.get_property(policy.DISPLAYS)]) for w in self.widgets]
        require(time.monotonic()-self.phase_started<35.,'native accolade phase timed out: '+self.phase)
        if self.phase=='fifo':
            if not self.empty() or any(len(self.selected_events(w))<4 for w in self.widgets):return
            self.record('real_registry_fifo',[self.text(self.chain2),self.text(self.streak)]);self.reset();self.queue(self.simple(self.chain3),2);self.queue(self.simple(self.streak),1);self.enter('out_of_order_pending')
        elif self.phase=='out_of_order_pending':
            if not all(len(w.get_property(policy.LOADS))==2 and all(e.bFinishedLoading for e in w.get_property(policy.LOADS)) for w in self.widgets):return
            require(not self.events and all(not w.get_property(policy.DISPLAYS) for w in self.widgets),'future async sequence displayed early')
            self.queue(self.simple(self.chain2),0);self.enter('out_of_order')
        elif self.phase=='out_of_order':
            if not self.empty() or any(len(self.selected_events(w))<6 for w in self.widgets):return
            self.record('out_of_order_2_1_0',[self.text(self.chain2),self.text(self.streak),self.text(self.chain3)]);self.reset();self.queue(self.chain2,0);self.enter('cancel_start')
        elif self.phase=='cancel_start':
            if any(not self.selected_events(w) for w in self.widgets):return
            self.queue(self.chain3,1);self.enter('cancel')
        elif self.phase=='cancel':
            if not self.empty() or any(len(self.selected_events(w))<4 for w in self.widgets):return
            self.record('cancel_current',[self.text(self.chain2),self.text(self.chain3)]);self.reset();self.queue(self.simple(self.streak,.5),0);self.queue(self.chain2,1);self.enter('cancel_pending_start')
        elif self.phase=='cancel_pending_start':
            if not all(len(w.get_property(policy.DISPLAYS))==2 for w in self.widgets):return
            self.queue(self.chain3,2);self.enter('cancel_pending')
        elif self.phase=='cancel_pending':
            if not self.empty() or any(len(self.selected_events(w))<4 for w in self.widgets):return
            self.record('cancel_pending',[self.text(self.streak),self.text(self.chain3)]);self.reset();wrong=self.simple(self.chain2);wrong.LocationTag=tag('UI.Layer.Menu');self.queue(wrong,0);self.queue(self.simple(self.streak),1);self.enter('location')
        elif self.phase=='location':
            if not self.empty() or any(len(self.selected_events(w))<2 for w in self.widgets):return
            self.record('location_skip_advances_sequence',[self.text(self.streak)]);self.reset();self.queue(self.simple(self.chain2,.5),0);self.enter('destroy_visible')
        elif self.phase=='destroy_visible':
            if not all(w.get_property(policy.DISPLAYS) for w in self.widgets):return
            self.recording=False
            for w in self.widgets:w.call_function('RemoveFromParent')
            self.after_remove=[copy.deepcopy(policy.metrics(w)) for w in self.widgets];self.enter('destroyed_wait')
        elif self.phase=='destroyed_wait':
            if time.monotonic()-self.phase_started<.8:return
            require(self.empty() and all(policy.metrics(w)==m for w,m in zip(self.widgets,self.after_remove)),'native pop/async callback after widget removal')
            self.report['cases'].append(dict(name='removed_visible_timer_cancelled',passed=True));self.reset()
            # A cached accolade finishes FAsyncMixin inline. Import only a cold
            # soft texture reference into a transient fixture table; do not load
            # it through the UObject getter before the native async request.
            table=ue.load_object(ue.find_class('DataTable'),'/Game/UEPValidation/DT_NativeAccoladeCold.DT_NativeAccoladeCold');rows=table.data_table_as_dict();path=None;cold=None
            for entry in json.loads(table.data_table_as_json()):
                candidate=entry['Icon']
                if "'" in candidate:candidate=candidate.split("'",2)[1]
                try:ue.find_object(candidate)
                except Exception as exc:
                    if not str(exc).startswith('unable to find object '):raise
                    path=candidate;cold=rows[entry['Name']].clone();break
            require(path is not None,'no unloaded native async fixture texture available');self.report['cold_native_asset']=path
            cold.DisplayDuration=.25;cold.LocationTag=self.chain2.LocationTag
            self.queue(cold,0)
            pending=[any(not e.bFinishedLoading for e in w.get_property(policy.LOADS)) for w in self.widgets]
            before_rows=[sum(policy.metrics(w)[p+'row'] for p in ('native_','python_')) for w in self.widgets]
            self.publish('EliminationChain.2x')
            self.report['registry_pending_at_rebuild']=[int(w.get_property(policy.ALLOCATED))==1 and sum(policy.metrics(w)[p+'row'] for p in ('native_','python_'))==count for w,count in zip(self.widgets,before_rows)]
            self.recording=False
            for w in self.widgets:w.call_function('RemoveFromParent');w.call_function('AddToPlayerScreen',0)
            self.after_rebuild=[copy.deepcopy(policy.metrics(w)) for w in self.widgets];self.report['async_pending_at_rebuild']=pending;self.enter('rebuild_wait')
        elif self.phase=='rebuild_wait':
            if time.monotonic()-self.phase_started<.5:return
            require(self.empty() and all(policy.metrics(w)==m for w,m in zip(self.widgets,self.after_rebuild)),'stale native async callback crossed widget lifetime')
            self.report['cases'].append(dict(name='pending_async_cancel_and_rebuild',passed=True));self.events=[];self.recording=True;self.publish('EliminationChain.2x',self.foreign);self.enter('foreign_broadcast')
        elif self.phase=='foreign_broadcast':
            if time.monotonic()-self.phase_started<.3:return
            require(not self.events and self.empty(),'native foreign-player notification reached host queue')
            self.report['cases'].append(dict(name='real_native_foreign_notification_filtered',passed=True));self.publish('EliminationChain.2x');self.enter('remount')
        elif self.phase=='remount':
            if not self.empty() or any(len(self.selected_events(w))<2 for w in self.widgets):return
            self.record('single_listener_after_rebuild',[self.text(self.chain2)]);self.reset()
            for w in self.widgets:w.call_function('OnNotificationMessage',tag('Lyra.AddNotification.Message'),LyraNotificationMessage(TargetChannel=tag(ROOT),PayloadTag=GameplayTag()))
            self.report['cases'].append(dict(name='invalid_registry_id_rolls_back',allocated=[int(w.get_property(policy.ALLOCATED)) for w in self.widgets],empty=self.empty()))
            require(self.empty() and all(int(w.get_property(policy.ALLOCATED))==0 for w in self.widgets),'native registry acquire failure counter rollback differs')
            self.report['metrics']=[dict(profile=str(ue.get_mixin_profile(w)),metrics=copy.deepcopy(policy.metrics(w))) for w in self.widgets];self.finish()

    def cleanup(self):
        self.recording=False
        for w in self.widgets:
            if valid(w):w.call_function('RemoveFromParent');w.remove_from_root()
        self.report['widgets_removed_and_unrooted']=all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets)
        if hasattr(self,'sources'):
            for profile,base in self.sources.items():ue.register_mixin_profile(self.cls,profile,base)
            self.cls.get_cdo().set_property('PythonMixinProfile',self.previous)
        if hasattr(self,'sender') and self.sender_root:self.sender.remove_from_root()
        if valid(self.foreign):self.foreign.call_function('K2_DestroyActor')
        for cls in self.boot:cls.remove_from_root()
        self.report['profile_classes_restored']=not hasattr(self,'sources') or any(r['target_class']==self.cls and all(r['profiles'][p]['python_class'] is b for p,b in self.sources.items()) for r in ue.get_registered_mixins())

    def tick(self,delta):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native accolade validation timed out')
            if self.phase=='ready':self.setup()
            else:self.observe()
            self.report['phase']=self.phase;atomic_write(self.path,self.report);return not self.finished
        except Exception:self.finish(traceback.format_exc());return False

    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);atomic_write(self.path,self.report);(ue.log_error if error else ue.log)('UEP_NATIVE_ACCOLADE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()

    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        atomic_write(self.path,self.report);(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_NATIVE_ACCOLADE_SHUTDOWN_'+self.report['status'].upper())


if any(v.startswith('-UEPNativeAccoladeResult=') for v in __import__('sys').argv):
    validation=Validation();ticker=ue.add_ticker(validation.tick)
