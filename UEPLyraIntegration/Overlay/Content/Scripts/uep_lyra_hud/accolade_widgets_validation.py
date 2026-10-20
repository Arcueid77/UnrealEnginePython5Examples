"""Real parent registry/queue/timer callbacks, native UMG and opaque row text."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,PendingAccoladeEntry,LyraVerbMessage
from unreal_engine.enums import ESlateVisibility
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Ready,dead
from uep_lyra_world.effect_pad_mixin import valid
from . import accolade_widgets_mixin as policy
from .accolade_widgets_contract import PROFILES,require,validate

ROOT='Lyra.ShooterGame.Accolade'


def tag(s):return GameplayTag(TagName=s)
def path(o):return o.get_path_name() if valid(o) else None
def count(w,name):return sum(policy.evidence(w)[p+'_'+name] for p in ('python','fallback'))


class Validation(Ready):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,pairs=[]);self.widgets=[];self.events=[];self.sources={};self.queued=False;self.repeats=[]
        for k in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_energy_measured','native_registry_or_queue_replaced','timer_or_animation_callbacks_replayed','health_properties_written','localized_text_roundtripped'):self.report[k]=False
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        for label,cls in self.classes.items():
            ue.register_declared_mixin(cls);row,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];self.sources[label]={p:r['python_class'] for p,r in row['profiles'].items()}
        for profile,base in self.sources['host'].items():
            def around(fn,action):
                def invoke(w,*args):
                    if self.queued and w in self.widgets:
                        item=dict(widget=w,action=action,time=self.game_time())
                        if action=='create':item.update(entry=args[0],display=policy.lib('KismetTextLibrary').call_function('Conv_TextToString',args[0].Row.DisplayName),duration=float(args[0].Row.DisplayDuration))
                        self.events.append(item)
                    return fn(w,*args)
                invoke.override=getattr(fn,'override');invoke.uep_named_outputs=bool(getattr(fn,'uep_named_outputs',False));return invoke
            ue.register_mixin_profile(self.classes['host'],profile,type('ObservedAccoladeHost'+profile,(),dict(Construct=base.Construct,Create=around(base.Create,'create'),Destroy=around(base.Destroy,'destroy'))))
        table=ue.load_object(ue.find_class('DataTable'),'/ShooterCore/Accolades/DT_BasicShooterAccolades.DT_BasicShooterAccolades');self.rows=table.data_table_as_dict();self.report['table_rows']={str(k):dict(text=policy.lib('KismetTextLibrary').call_function('Conv_TextToString',r.DisplayName),duration=float(r.DisplayDuration),location=str(r.LocationTag.TagName)) for k,r in self.rows.items()}
        self.chain2=self.row('EliminationChain.2x');self.chain3=self.row('EliminationChain.3x');self.streak=self.row('EliminationStreak.5')
        self.router=policy.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'));self.sender=ue.load_class('/Game/UEPValidation/BP_AccoladeRelayProbe.BP_AccoladeRelayProbe_C').get_cdo();self.sender_root=not self.sender.is_rooted()
        if self.sender_root:self.sender.add_to_root()
        self.foreign=self.world.actor_spawn(ue.find_class('PlayerState'));self.actors.append(self.foreign)
        self.icon=ue.load_object(ue.find_class('Texture'),'/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture');self.sound=ue.load_object(ue.find_class('SoundBase'),'/Game/Audio/Sounds/SFX/Lyra_ControlPoint_CapturedByFriendly_01.Lyra_ControlPoint_CapturedByFriendly_01')
        for profile in PROFILES:
            w=policy.lib('WidgetBlueprintLibrary').call_function('Create',self.world,self.classes['host'],self.controller);w.add_to_root();self.widgets.append(w);ue.set_mixin_profile(w,profile);toast=w.get_property('MyToast');ue.set_mixin_profile(toast,profile);w.call_function('AddToPlayerScreen',0)
            require(str(w.get_property('LocationName').TagName)==str(self.chain2.LocationTag.TagName)==str(self.streak.LocationTag.TagName),'fixture row/host original location differs')
            p=dict(profile=profile,initial_collapsed=int(toast.call_function('GetVisibility'))==int(ESlateVisibility.Collapsed),direct_cases=[],all_queued_native_text_icon_and_allocation_match=True);self.report['pairs'].append(p)
            for has_sound in (False,True):
                entry=PendingAccoladeEntry(Row=self.chain2,Sound=self.sound if has_sound else None,Icon=self.icon if has_sound else None);returned=w.call_function('CreateAccoladeWidget',entry);p['direct_cases'].append(dict(has_sound=has_sound,returned_owned_toast=returned==toast,**self.presentation(w,entry)))
        for i,w in enumerate(self.widgets):
            other=self.widgets[1-i].get_property('MyToast');before=int(other.call_function('GetVisibility'));w.call_function('DestroyAccoladeWidget',other);self.report['pairs'][i]['destroy_ignores_foreign_argument']=int(w.get_property('MyToast').call_function('GetVisibility'))==int(ESlateVisibility.Collapsed) and int(other.call_function('GetVisibility'))==before
            w.call_function('CreateAccoladeWidget',PendingAccoladeEntry(Row=self.chain2,Sound=None,Icon=None))
        self.enter('repeat')
    def row(self,suffix):return next(r for name,r in self.rows.items() if str(name).endswith(suffix))
    def presentation(self,w,entry):
        toast=w.get_property('MyToast');text=toast.get_property('TextWidget').call_function('GetText');brush=toast.get_property('IconWidget').get_property('Brush')
        return dict(native_text_matches=bool(policy.lib('KismetTextLibrary').call_function('EqualEqual_TextText',text,entry.Row.DisplayName)),icon_matches=brush.ResourceObject==entry.Icon,visible=int(toast.call_function('GetVisibility'))==int(ESlateVisibility.HitTestInvisible),animation_playing=bool(toast.call_function('IsAnimationPlaying',toast.get_property('IntroOutro'))))
    def publish(self,suffix,source=None):
        full=ROOT+'.'+suffix;self.sender.call_function('BroadcastVerb',self.router,tag(full),LyraVerbMessage(Verb=tag(full),Instigator=self.controller.PlayerState if source is None else source))
    def queued_events(self,w):return [e for e in self.events if e['widget']==w]
    def queue_empty(self):return all(not w.get_property('PendingAccoladeLoads') and not w.get_property('PendingAccoladeDisplays') for w in self.widgets)
    def samples(self):
        for w,p in zip(self.widgets,self.report['pairs']):
            for entry in w.get_property('PendingAccoladeDisplays'):
                if valid(entry.AllocatedWidget):p['all_queued_native_text_icon_and_allocation_match'] &= self.presentation(w,entry)['native_text_matches'] and self.presentation(w,entry)['icon_matches'] and entry.AllocatedWidget==w.get_property('MyToast')
    def observe(self):
        require(time.monotonic()-self.phase_started<35.,'native accolade widget phase timeout: '+self.phase);self.samples()
        if self.phase=='repeat':
            if time.monotonic()-self.phase_started<.2:return
            for w,p in zip(self.widgets,self.report['pairs']):
                toast=w.get_property('MyToast');a=toast.get_property('IntroOutro');before=float(toast.call_function('GetAnimationCurrentTime',a));toast.call_function('PlayIntroOutro');after=float(toast.call_function('GetAnimationCurrentTime',a));self.repeats.append([before,after]);p['repeat_animation_still_playing']=bool(toast.call_function('IsAnimationPlaying',a));toast.call_function('StopAllAnimations')
            self.report['animation_repeat_pairs_match']=abs((self.repeats[0][1]-self.repeats[0][0])-(self.repeats[1][1]-self.repeats[1][0]))<.05;self.queued=True;self.events=[];self.publish('EliminationChain.2x');self.publish('EliminationStreak.5');self.enter('fifo')
        elif self.phase=='fifo':
            if not self.queue_empty() or any(len(self.queued_events(w))<4 for w in self.widgets):return
            for w,p in zip(self.widgets,self.report['pairs']):
                events=self.queued_events(w);creates=[e for e in events if e['action']=='create'];destroys=[e for e in events if e['action']=='destroy'];p['fifo_create_order']=[e['display'] for e in creates];p['expected_fifo']=[self.text(self.chain2),self.text(self.streak)];p['fifo_native_allocated_widget_matches']=p['all_queued_native_text_icon_and_allocation_match'];p['fifo_duration_checks']=len(creates)==len(destroys)==2 and all(float(a['duration'])-.05<=b['time']-a['time']<=float(a['duration'])+.3 for a,b in zip(creates,destroys))
            self.events=[];self.publish('EliminationChain.2x');self.enter('cancel-start')
        elif self.phase=='cancel-start':
            if any(not self.queued_events(w) for w in self.widgets):return
            self.publish('EliminationChain.3x');self.enter('cancel')
        elif self.phase=='cancel':
            if not self.queue_empty() or any(len(self.queued_events(w))<4 for w in self.widgets):return
            for w,p in zip(self.widgets,self.report['pairs']):
                events=self.queued_events(w);p['cancel_order']=[e['action'] for e in events];p['cancel_create_order']=[e['display'] for e in events if e['action']=='create'];p['expected_cancel']=[self.text(self.chain2),self.text(self.chain3)]
            self.events=[];self.publish('EliminationChain.2x',self.foreign);self.enter('foreign')
        elif self.phase=='foreign':
            if time.monotonic()-self.phase_started<.3:return
            for w,p in zip(self.widgets,self.report['pairs']):p['foreign_target_ignored']=not self.queued_events(w);w.call_function('RemoveFromParent')
            self.events=[];self.publish('EliminationChain.2x');self.enter('unmounted')
        elif self.phase=='unmounted':
            if time.monotonic()-self.phase_started<.3:return
            for w,p in zip(self.widgets,self.report['pairs']):p['unmounted_message_ignored']=not self.queued_events(w);w.call_function('AddToPlayerScreen',0);p['remount_collapsed']=int(w.get_property('MyToast').call_function('GetVisibility'))==int(ESlateVisibility.Collapsed)
            self.events=[];self.publish('EliminationChain.2x');self.enter('remount')
        elif self.phase=='remount':
            if not self.queue_empty() or any(len(self.queued_events(w))<2 for w in self.widgets):return
            for w,p in zip(self.widgets,self.report['pairs']):p.update(single_create_after_remount=[e['action'] for e in self.queued_events(w)]==['create','destroy'],natural_constructs=count(w,'construct'),diagnostic_fallbacks=policy.evidence(w)['diagnostic_fallbacks']+policy.evidence(w.get_property('MyToast'))['diagnostic_fallbacks'])
            self.finish()
    def text(self,row):return policy.lib('KismetTextLibrary').call_function('Conv_TextToString',row.DisplayName)
    def cleanup(self):
        self.queued=False
        for w in self.widgets:
            require(not w.get_property('PendingAccoladeDisplays'),'native queue still active during cleanup');ue.clear_mixin_profile(w);ue.clear_mixin_profile(w.get_property('MyToast'));w.call_function('RemoveFromParent');w.remove_from_root()
        for label,profiles in self.sources.items():
            for p,base in profiles.items():ue.register_mixin_profile(self.classes[label],p,base)
        if hasattr(self,'sender') and self.sender_root:self.sender.remove_from_root()
        if hasattr(self,'foreign') and not dead(self.foreign):self.foreign.actor_destroy()
        self.report.update(widget_profile_families_restored=all(any(r['target_class']==self.classes[label] and all(r['profiles'][p]['python_class'] is base for p,base in profiles.items()) for r in ue.get_registered_mixins()) for label,profiles in self.sources.items()),owned_widgets_removed_unrooted=bool(self.widgets) and all(not w.is_rooted() and not w.call_function('IsInViewport') for w in self.widgets),sender_root_removed=hasattr(self,'sender') and (not self.sender_root or not self.sender.is_rooted()),owned_foreign_player_destroyed=hasattr(self,'foreign') and dead(self.foreign),original_health_unchanged=self.healths()==self.health_before)
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<260.,'native accolade widgets total timeout')
            if self.phase=='ready':self.ready()
            else:self.observe()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_ACCOLADE_WIDGETS_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_ACCOLADE_WIDGETS_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPAccoladeWidgetsResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
