"""Natural UMG construction, full reflected styles, typed messages and Cue manager."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,LyraVerbMessage
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from uep_lyra_world.effect_pad_mixin import valid
from . import match_message_mixin as match,waiting_message_mixin as waiting,cue_widget_mixin as cue
from .cue_widget_validation import CHILDREN,dead
from .message_widget_contract import require,validate

CHANNEL='ShooterGame.GamePhase.MatchBeginCountdown'


def model(value):
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if isinstance(value,dict):return {k:model(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [model(v) for v in value]
    if hasattr(value,'get_path_name'):return value.get_path_name()
    if hasattr(value,'as_dict'):return model(value.as_dict())
    if all(hasattr(value,k) for k in ('r','g','b','a')):return [float(getattr(value,k)) for k in ('r','g','b','a')]
    if hasattr(value,'x') and hasattr(value,'y'):return [float(getattr(value,k)) for k in ('x','y','z','w') if hasattr(value,k)]
    return str(value)


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.widgets=[];self.waiters=[];self.actors=[];self.classes={};self.sources={};self.stingers=[]
        self.report=dict(status='running',error=None,style_pairs=[],result_pairs=[],waiting_cases=[],localized_text_pairs=[],manager_cases=[])
        for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','native_invalid_material_index_tested','native_no_team_initialization_tested','callbacks_replayed','python_subscription_roots_added','native_proxies_cancelled_by_probe','health_properties_written'):self.report[key]=False
    def proxies(self):return {p.get_path_name():p for p in ue.tobject_iterator(ue.find_class('AsyncAction_ListenForGameplayMessage')) if valid(p)}
    def gi_proxies(self):return {p.get_path_name() for p in self.game.get_property('ReferencedObjects') if valid(p) and p.is_a(ue.find_class('AsyncAction_ListenForGameplayMessage'))}
    def broadcast(self,channel=CHANNEL):self.probe.call_function('BroadcastVerb',self.router,GameplayTag(TagName=channel),LyraVerbMessage(Magnitude=7.))
    def begin(self):
        bridge=match.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world);self.report['native_mode']=str(bridge.call_function('CaptureSnapshot').NetMode)
        self.health_before=self.healths();self.game=self.statics.call_function('GetGameInstance',self.world)
        self.router=match.lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',self.world,ue.find_class('GameplayMessageSubsystem'))
        self.probe=ue.load_class('/Game/UEPValidation/BP_MessageWidgetProbe.BP_MessageWidgetProbe_C').get_cdo();self.probe.add_to_root()
        for label,path in (('match',match.CLASS),('waiting',waiting.CLASS)):
            cls=ue.load_class(path);self.classes[label]=cls;ue.register_declared_mixin(cls)
        self.cdo_profiles={label:str(ue.get_mixin_profile(cls.get_cdo())) for label,cls in self.classes.items()}
        music_cls=ue.load_class('/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C')
        self.music=self.statics.call_function('GetGameState',self.world).get_component_by_type(music_cls);self.music_cls=music_cls
        self.music_fields={n:self.music.get_property(n) for n in ('Music System','Alpha_Intensity','Alpha_Mvmt','bIsMenu')};self.music.set_property('Music System',None)
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==music_cls];self.music_sources={n:r['python_class'] for n,r in row['profiles'].items()};owner=self
        for name,source in self.music_sources.items():
            methods={n:fn for n,fn in vars(source).items() if not n.startswith('__') and callable(fn)}
            def around(handler):
                def invoke(component,Positive):
                    if component==owner.music:owner.stingers.append(bool(Positive))
                    return handler(component,Positive)
                invoke.override='Fire Stinger';return invoke
            methods['Stinger']=around(source.Stinger);ue.register_mixin_profile(music_cls,name,type('ObservedMessageStinger'+name,(),methods))
        self.styles();self.results();self.start_waiting()
    def create(self,label,profile,latch=False):
        cls=self.classes[label];cdo=cls.get_cdo();previous=cdo.get_property('PythonMixinProfile');old_latch=cdo.get_property('CountdownStarted') if label=='waiting' else None
        try:
            cdo.set_property('PythonMixinProfile',profile)
            if label=='waiting':cdo.set_property('CountdownStarted',latch)
            widget=match.lib('WidgetBlueprintLibrary').call_function('Create',self.world,cls,self.controller)
        finally:
            cdo.set_property('PythonMixinProfile',previous)
            if label=='waiting':cdo.set_property('CountdownStarted',old_latch)
        require(valid(widget),'native message widget creation failed');self.widgets.append(widget)
        require(str(ue.get_mixin_profile(widget))==profile,'native creation did not inherit the selected Profile field')
        if label=='waiting':
            counts=waiting.evidence(widget);require(counts['python_init' if profile=='Python' else 'fallback_init']==1 and counts['fallback_init' if profile=='Python' else 'python_init']==0,'natural OnInitialized used the wrong Profile')
        ue.set_mixin_profile(widget,profile);widget.call_function('AddToPlayerScreen',0);return widget
    def capture(self,widget):
        return dict(team=int(widget.get_property('Team')),text=str(widget.get_property('VictoryMessage').call_function('GetText')),
            font=model(widget.get_property('VictoryMessage').get_property('Font')),
            brushes={field:model(widget.get_property(field).get_property('Brush')) for field,_,_ in match.IMAGES},
            victory=bool(widget.call_function('IsAnimationPlaying',widget.get_property('VictoryIntro'))),defeat=bool(widget.call_function('IsAnimationPlaying',widget.get_property('DefeatIntro'))))
    def seed(self,widget):
        control=widget.get_property('VictoryMessage');font=control.get_property('Font');font.Size=37.5;font.LetterSpacing=17;font.SkewAmount=.375;font.bForceMonospaced=True;font.bMaterialIsStencil=True;font.MonospacedWidth=.75;control.call_function('SetFont',font)
        for index,(field,_,_) in enumerate(match.IMAGES):
            image=widget.get_property(field);brush=image.get_property('Brush');brush.ImageType=2;brush.Tiling=3;brush.Mirroring=1
            brush.Margin=ue.find_struct('Margin')(Left=.1+index*.01,Top=.2,Right=.3,Bottom=.4)
            brush.TintColor=ue.find_struct('SlateColor')(SpecifiedColor=ue.FLinearColor(.2,.3,.4,.5),ColorUseRule=0)
            image.call_function('SetBrush',brush)
    def styles(self):
        for team in (0,1,2):
            for seeded in (False,True):
                states=[];entries=original_entries=0
                for profile in ('BlueprintFallback','Python'):
                    widget=self.create('match',profile);widget.set_property('Team',team)
                    if seeded:self.seed(widget)
                    before=dict(match.evidence(widget));widget.call_function('SetTeamMaterials')
                    if profile=='Python':entries=match.evidence(widget)['python_materials']-before['python_materials']
                    else:original_entries=match.evidence(widget)['fallback_materials']-before['fallback_materials']
                    states.append(self.capture(widget));widget.call_function('RemoveFromParent')
                self.report['style_pairs'].append(dict(team=team,seeded=seeded,original=states[0],python=states[1],python_material_entries=entries,original_material_entries=original_entries))
    def params(self,ability,raw):
        from unreal_engine.structs import GameplayTagContainer,GameplayEffectContextHandle
        return match.lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=.25,RawMagnitude=raw,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(),Normal=ue.FVector(0.,0.,1.),Instigator=self.controller.PlayerState,EffectCauser=None,SourceObject=None,PhysicalMaterial=None,GameplayEffectLevel=1,AbilityLevel=ability,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def results(self):
        probe=self.create('match','Python');_,index=match.team(probe);probe.call_function('RemoveFromParent')
        for kind,ability,raw in (('draw',0,800.),('victory',index,-55.),('defeat',2 if index!=2 else 1,float(index)),('draw',0,-.5)):
            states=[];observed=[];entries=literal=original_entries=0
            for profile in ('BlueprintFallback','Python'):
                widget=self.create('match',profile);self.stingers=[];before=dict(match.evidence(widget));widget.call_function('ConstructFromCueParams',self.params(ability,raw))
                states.append(self.capture(widget));observed.append(list(self.stingers))
                if profile=='Python':entries=match.evidence(widget)['python_construct']-before['python_construct'];literal=match.evidence(widget)['literal_calls']-before['literal_calls']
                else:original_entries=match.evidence(widget)['fallback_construct']-before['fallback_construct']
                widget.call_function('StopAllAnimations');widget.call_function('RemoveFromParent')
            self.report['result_pairs'].append(dict(kind=kind,ability=ability,raw=raw,original=states[0],python=states[1],original_stingers=observed[0],python_stingers=observed[1],python_construct_entries=entries,python_literal_entries=literal,original_construct_entries=original_entries))
    def start_waiting(self):
        before=set(self.proxies());self.owned_proxies={}
        for profile,latch,switch in (('BlueprintFallback',False,False),('Python',False,False),('BlueprintFallback',True,False),('Python',True,False),('BlueprintFallback',False,True),('Python',False,True)):
            old=set(self.proxies());widget=self.create('waiting',profile,latch);added={k:v for k,v in self.proxies().items() if k not in old};self.owned_proxies.update(added)
            expected=('Python' if profile=='BlueprintFallback' else 'BlueprintFallback') if switch else profile
            if switch:ue.set_mixin_profile(widget,expected)
            counts=waiting.evidence(widget);self.waiters.append(dict(widget=widget,profile=profile,expected=expected,latch=latch,proxy_count=len(added),init=counts['python_init']+counts['fallback_init'],before=counts['python_messages']+counts['fallback_messages']))
        for index in (0,1,2):
            values=[]
            for profile in ('BlueprintFallback','Python'):
                widget=next(r['widget'] for r in self.waiters if r['profile']==profile and not r['latch']);widget.call_function(waiting.TEXT,index);values.append(str(widget.get_property('TeamNotification').call_function('GetText')))
            self.report['localized_text_pairs'].append(dict(index=index,original=values[0],python=values[1]))
        self.broadcast('ShooterGame.GamePhase')
        for row in self.waiters:
            counts=waiting.evidence(row['widget']);row['parent_count']=counts['python_messages']+counts['fallback_messages']-row['before']
        self.broadcast()
        for row in self.waiters:row['first_animation']=bool(row['widget'].call_function('IsAnimationPlaying',row['widget'].get_property('CountDown')))
        self.broadcast()
        for row in self.waiters:row['widget'].call_function('RemoveFromParent')
        self.broadcast()
        for row in self.waiters:
            widget=row['widget'];counts=waiting.evidence(widget)
            self.report['waiting_cases'].append(dict(initial_profile=row['profile'],expected_callback_profile=row['expected'],selected_callback_profile=str(ue.get_mixin_profile(widget)),initial_latch=row['latch'],natural_initializations=row['init'],native_proxies_added=row['proxy_count'],after_parent_messages=row['parent_count'],matching_callbacks=counts['python_messages']+counts['fallback_messages']-row['before'],countdown_started=bool(widget.get_property('CountdownStarted')),first_message_animation=row['first_animation'],latch_preserved_after_repeat_and_remove=bool(widget.get_property('CountdownStarted'))))
            widget.call_function('StopAllAnimations')
        self.report['owned_proxy_gi_refs_before_gc']=len(set(self.owned_proxies)&self.gi_proxies());self.gc_widgets=[r['widget'] for r in self.waiters];self.waiters=[];self.widgets=[]
        self.gc_ticks=0;match.lib('KismetSystemLibrary').call_function('CollectGarbage');self.enter('gc')
    def after_gc(self):
        self.broadcast();self.report['native_gc_boundary_observed']=True
        self.report['owned_proxy_gi_refs_after_gc_and_message']=len(set(self.owned_proxies)&self.gi_proxies())
        self.report['owned_proxies_inactive_after_gc_and_message']=all(not p.call_function('IsActive') for p in self.owned_proxies.values() if valid(p))
        self.manager_index=0;self.manager_next()
    def manager_next(self):
        self.manager_label=('match','waiting')[self.manager_index];self.target=self.world.actor_spawn(ue.find_class('Actor'));self.actors.append(self.target)
        self.target.add_actor_root_component(ue.find_class('SceneComponent'),'UEPMessageWidgetTarget')
        cls=ue.load_class(CHILDREN[self.manager_label]);self.tag=cls.get_cdo().get_property('GameplayCueTag');self.manager_params=self.params(1,0.)
        base=ue.load_class(cue.CLASS);self.manager_before={a.get_path_name():cue.evidence(a)['python_start'] for a in self.world.all_actors() if valid(a) and a.is_a(base)}
        match.lib('GameplayCueFunctionLibrary').call_function('AddGameplayCueOnActor',self.target,self.tag,self.manager_params);self.enter('manager')
    def manager(self):
        require(time.monotonic()-self.phase_started<15.,'real message Cue did not activate')
        actors=[a for a in self.world.all_actors() if valid(a) and a.is_a(ue.load_class(cue.CLASS)) and a.call_function('GetOwner')==self.target]
        if not actors:return
        actor,=actors;widget=actor.get_property('SpawnedWidget');require(valid(widget),'real Cue widget absent');self.widgets.append(widget)
        counts=match.evidence(widget) if self.manager_label=='match' else waiting.evidence(widget)
        dispatch=counts['python_construct'] if self.manager_label=='match' else counts['python_init'];added=bool(widget.call_function('IsInViewport'))
        match.lib('GameplayCueFunctionLibrary').call_function('RemoveGameplayCueOnActor',self.target,self.tag,self.manager_params)
        self.report['manager_cases'].append(dict(**{'class':self.manager_label},default_python_message_dispatch=dispatch==1,added=added,removed=not widget.call_function('IsInViewport'),native_parent_gate_entries=cue.evidence(actor)['python_start']-self.manager_before.get(actor.get_path_name(),0)))
        self.manager_index+=1
        if self.manager_index==2:self.finish()
        else:self.manager_next()
    def cleanup(self):
        for widget in self.widgets:
            if valid(widget):widget.call_function('StopAllAnimations');widget.call_function('RemoveFromParent')
        for actor in self.actors:
            if not dead(actor):actor.call_function('K2_DestroyActor')
        self.report['all_owned_widgets_removed']=all(not valid(w) or not w.call_function('IsInViewport') for w in self.widgets+getattr(self,'gc_widgets',[]))
        self.report['profiles_and_cdo_selectors_restored']=all(str(ue.get_mixin_profile(cls.get_cdo()))==self.cdo_profiles[label] for label,cls in self.classes.items())
        if hasattr(self,'music_fields'):
            for name,value in self.music_fields.items():self.music.set_property(name,value)
            for name,source in self.music_sources.items():ue.register_mixin_profile(self.music_cls,name,source)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.music_cls]
            self.report['music_fields_and_provider_family_restored']=all(self.music.get_property(k)==v for k,v in self.music_fields.items()) and all(row['profiles'][n]['python_class'] is source for n,source in self.music_sources.items())
        if hasattr(self,'probe'):self.probe.remove_from_root();self.report['probe_unrooted']=not self.probe.is_rooted()
        self.report['health_unchanged']=hasattr(self,'health_before') and self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<220.,'message widget native timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='gc':
                self.gc_ticks+=1
                if self.gc_ticks>=3:self.after_gc()
            elif self.phase=='manager':self.manager()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_MESSAGE_WIDGET_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_MESSAGE_WIDGET_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPMessageWidgetResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
