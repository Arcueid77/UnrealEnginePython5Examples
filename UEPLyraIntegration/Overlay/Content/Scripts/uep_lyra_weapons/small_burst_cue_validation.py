"""Real manager/static parent FX, controlled edge arrays and offline heal Play."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayCueNotify_SpawnResult,GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_weapons.hero_burst_cue_validation import Validation as Fixtures,dead,color
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs
from uep_lyra_audio import music_manager_mixin as music
from . import small_burst_cue_mixin as policy
from .small_burst_cue_contract import require,validate,close


def path(value):return value.get_path_name() if valid(value) else None
def calls(cue):return sum(policy.evidence(cue)[key] for key in ('python_burst','fallback_burst'))


class Validation(Fixtures):
    def __init__(self,result):
        super().__init__(result);self.report=dict(status='running',error=None,color_cases=[],melee_cases=[],edge_cases=[],heal_cases=[],manager_cases=[]);self.sources={};self.expected=None;self.events=[];self.static_profiles={};self.heals=[];self.index=0
        for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','hardware_audio_playback_tested','callbacks_replayed','native_timer_properties_written','health_properties_written'):self.report[key]=False
        self.report['controlled_edge_spawn_arrays']=True
    def params(self,instigator):
        return policy.lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=.7,RawMagnitude=17.,EffectContext=GameplayEffectContextHandle(),MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(14000.,-11000.,3000.),Normal=ue.FVector(0.,0.,1.),Instigator=instigator,EffectCauser=None,SourceObject=None,PhysicalMaterial=None,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode);self.health_before=self.healths();self.classes={k:ue.load_class(v) for k,v in policy.CLASSES.items()}
        state=self.statics.call_function('GetGameState',self.world);self.manager=state.get_component_by_type(ue.load_class(music.CLASS));require(valid(self.manager),'actual music manager absent')
        self.observe();self.target=self.own();self.target.add_actor_root_component(ue.find_class('SceneComponent'),'UEPSmallBurstRoot')
        spawner_class=ue.load_class(policy.SPAWNER);definition=ue.load_object(ue.find_class('LyraWeaponPickupDefinition'),'/ShooterCore/Weapons/Rifle/WeaponPickupData_Rifle.WeaponPickupData_Rifle')
        require(valid(definition) and valid(definition.get_property('InventoryItemDefinition')),'actual configured rifle pickup definition required');cdo=spawner_class.get_cdo();previous=cdo.get_property('WeaponDefinition')
        transform=ue.FTransform();transform.translation=ue.FVector(200000.,200000.,3000.)
        self.spawner=self.statics.call_function('BeginDeferredActorSpawnFromClass',self.world,spawner_class,transform,1,None);self.actors.append(self.spawner);self.spawner.set_property('WeaponDefinition',definition)
        self.statics.call_function('FinishSpawningActor',self.spawner,transform)
        require(self.spawner.get_property('WeaponDefinition')==definition,'owned spawner lost explicit instance definition')
        self.report['fixture_weapon_definition']=path(definition);self.report['spawner_default_definition_restored']=cdo.get_property('WeaponDefinition')==previous
        self.spawner.call_function('SetActorEnableCollision',False);self.spawner.call_function('SetActorTickEnabled',False)
        self.grenade=self.world.actor_spawn(ue.load_class(policy.GRENADE),ue.FVector(200000.,200000.,3000.));self.actors.append(self.grenade);self.grenade.call_function('SetActorEnableCollision',False);self.grenade.call_function('SetActorTickEnabled',False)
        self.remote=self.world.actor_spawn(ue.find_class('Pawn'));self.actors.append(self.remote)
        for kind,actor,field in (('pickup',self.spawner,'LightColor'),('grenade',self.grenade,'Team Color')):
            for rgba in ((.12,.34,.56,.78),(.8,.5,.2,1.)):
                actor.set_property(field,ue.FLinearColor(*rgba));expected=color(actor.get_property(field))
                for profile in ('BlueprintFallback','Python'):
                    row=self.request(kind,self.target if kind=='pickup' else self.grenade,self.spawner,profile)
                    row['expected_color']=expected;self.report['color_cases'].append(row)
        for target,label in ((self.pawn,'local'),(self.remote,'remote')):
            for profile in ('BlueprintFallback','Python'):
                row=self.request('melee',target,None,profile);row['player_kind']=label;self.report['melee_cases'].append(row)
        self.edge_trials();self.grenade.actor_destroy();self.prepare_heal()
    def observe(self):
        owner=self
        for kind,cls in self.classes.items():
            ue.register_declared_mixin(cls);binding,=[r for r in ue.get_registered_mixins() if r['target_class']==cls];sources={p:r['python_class'] for p,r in binding['profiles'].items()};self.sources[kind]=sources
            if kind!='heal':self.static_profiles[kind]=str(ue.get_mixin_profile(cls.get_cdo()))
            for profile,source in sources.items():
                def around(handler,label,selected):
                    def invoke(cue,Target,Parameters,SpawnResults):
                        if owner.expected is None or owner.expected['kind']!=label or owner.expected['target']!=Target:return handler(cue,Target,Parameters,SpawnResults)
                        row=dict(kind=label,profile=selected,native_parent_fx_count=len(SpawnResults.FxSystemComponents),color_before=None,color_after=None,native_audio_playing=False,native_audio_sound=None)
                        owner.effects.extend(e for e in SpawnResults.FxSystemComponents if valid(e) and e not in owner.effects)
                        owner.expected['cue']=cue
                        values=owner.expected.get('edge_fx');used=GameplayCueNotify_SpawnResult(FxSystemComponents=values) if values is not None else SpawnResults
                        before=calls(cue);counter=dict(music.evidence(owner.manager));intensity=float(owner.manager.get_property('Alpha_Intensity'))
                        result=handler(cue,Target,Parameters,used)
                        row['entries']=calls(cue)-before;row['music_fire_entries']=sum(music.evidence(owner.manager)[k]-counter[k] for k in ('Receive Weapon Fire_python','Receive Weapon Fire_fallback'))
                        row['intensity_before']=intensity;row['intensity_after']=float(owner.manager.get_property('Alpha_Intensity'))
                        fx=list(used.FxSystemComponents)
                        if label in ('pickup','grenade') and fx and valid(fx[0]) and fx[0].is_a(ue.find_class('NiagaraComponent')):
                            fields=native_outputs('NiagaraComponent','GetVariableColor',fx[0].call_function('GetVariableColor','GunPad_Color' if label=='pickup' else 'Team_Color'))
                            row['color_valid']=bool(fields['bIsValid']);row['color_after']=color(fields['ReturnValue'])
                        if label=='heal':
                            audio=cue.get_property('Audio_OnHeal');row.update(native_audio_playing=bool(valid(audio) and audio.call_function('IsPlaying')),native_audio_sound=path(audio.get_property('Sound')) if valid(audio) else None)
                        for shake in SpawnResults.CameraShakes:
                            if valid(shake):owner.controller.get_property('PlayerCameraManager').call_function('StopCameraShake',shake,True)
                        owner.events.append(row);return result
                    return invoke
                ue.register_mixin_profile(cls,profile,type('ObservedSmallBurst'+kind.title()+profile,(),dict(OnBurst=around(source.OnBurst,kind,profile))))
    def request(self,kind,target,instigator,profile=None,edge_fx=None,actor=None):
        cls=self.classes[kind];cue=actor if actor is not None else cls.get_cdo()
        if profile is not None:ue.set_mixin_profile(cue,profile)
        else:ue.clear_mixin_profile(cue)
        self.expected=dict(kind=kind,target=target,edge_fx=edge_fx);self.events=[]
        if actor is None:policy.lib('GameplayCueFunctionLibrary').call_function('ExecuteGameplayCueOnActor',target,cls.get_cdo().get_property('GameplayCueTag'),self.params(instigator))
        else:actor.call_function('OnExecute',target,self.params(instigator))
        require(len(self.events)==1,'one actual parent OnBurst required: '+kind);row=self.events[0];row['selected_profile']=str(ue.get_mixin_profile(self.expected['cue']));self.expected=None
        if kind=='melee' and target==self.pawn:
            effect=cls.get_cdo().get_property('BurstEffects').BurstForceFeedback.ForceFeedbackEffect
            if valid(effect):self.controller.call_function('ClientStopForceFeedback',effect,'None')
        return row
    def fx(self,name):
        fx=self.target.add_actor_component(ue.find_class('NiagaraComponent'),name,self.target.get_property('RootComponent'));fx.call_function('SetAutoActivate',False);self.effects.append(fx);return fx
    def edge_trials(self):
        first=self.fx('UEPSmallBurstFirst');second=self.fx('UEPSmallBurstSecond');sentinel=ue.FLinearColor(.13,.23,.33,.43)
        for kind,mode,target,values in (('pickup','null-first',self.target,[None,second]),('grenade','null-first',self.grenade,[None,second]),('grenade','wrong-target',self.target,[first,second])):
            name='GunPad_Color' if kind=='pickup' else 'Team_Color'
            for profile in ('BlueprintFallback','Python'):
                for effect in (first,second):effect.call_function('SetVariableLinearColor',name,sentinel)
                row=self.request(kind,target,self.spawner,profile,values);row['mode']=mode
                row['second_color_unchanged']=close(color(native_outputs('NiagaraComponent','GetVariableColor',second.call_function('GetVariableColor',name))['ReturnValue']),color(sentinel))
                row['first_color_unchanged']=close(color(native_outputs('NiagaraComponent','GetVariableColor',first.call_function('GetVariableColor',name))['ReturnValue']),color(sentinel));self.report['edge_cases'].append(row)
    def prepare_heal(self):
        self.heal_target=self.own();self.heal_target.add_actor_root_component(ue.find_class('SceneComponent'),'UEPHealRoot')
        for profile in ('BlueprintFallback','Python'):
            cue=self.world.actor_spawn(self.classes['heal']);self.cues.append(cue);self.heals.append(cue);cue.call_function('SetOwner',self.heal_target);cue.call_function('SetActorHiddenInGame',False)
            self.report['heal_cases'].append(self.request('heal',self.heal_target,None,profile,actor=cue))
        self.heal_start=self.game_time();self.enter('heal-retrigger')
    def heal_retrigger(self):
        if self.game_time()-self.heal_start<.1:return
        self.report['heal_audio_playing_on_later_native_tick']=all(c.get_property('Audio_OnHeal').call_function('IsPlaying') for c in self.heals)
        for cue,profile in zip(self.heals,('BlueprintFallback','Python')):self.report['heal_cases'].append(self.request('heal',self.heal_target,None,profile,actor=cue))
        self.last_heal=self.game_time();self.enter('heal-lifetime')
    def heal_lifetime(self):
        elapsed=self.game_time()-self.last_heal
        if elapsed<4.8:
            require(all(c.call_function('GetOwner')==self.heal_target for c in self.heals),'heal native parent lifetime ended too early');return
        if any(c.call_function('GetOwner')==self.heal_target for c in self.heals):require(elapsed<8.,'heal native parent did not return to pool');return
        self.report['heal_parent_minimum_five_second_lifetime_and_pool_return']=elapsed>=4.9
        for cue in self.heals:ue.clear_mixin_profile(cue)
        self.default_managers();self.finish()
    def default_managers(self):
        for kind in ('pickup','melee','grenade'):
            target=self.target
            if kind=='grenade':
                target=self.world.actor_spawn(ue.load_class(policy.GRENADE),ue.FVector(200000.,200000.,3000.));self.actors.append(target);target.call_function('SetActorEnableCollision',False)
            row=self.request(kind,target,self.spawner);self.report['manager_cases'].append(row)
            if kind=='grenade':target.actor_destroy()
        for cue in ue.tobject_iterator(self.classes['heal']):
            if valid(cue) and cue.get_world()==self.world and cue.call_function('GetOwner') is None:ue.clear_mixin_profile(cue)
        self.expected=dict(kind='heal',target=self.heal_target,edge_fx=None);self.events=[]
        policy.lib('GameplayCueFunctionLibrary').call_function('ExecuteGameplayCueOnActor',self.heal_target,self.classes['heal'].get_cdo().get_property('GameplayCueTag'),self.params(None));require(len(self.events)==1,'real heal manager default entry absent')
        self.report['manager_cases'].append(self.events[0]);cue=self.expected['cue'];self.cues.append(cue);self.expected=None;ue.clear_mixin_profile(cue);cue.call_function('K2_EndGameplayCue')
    def cleanup(self):
        for kind,sources in self.sources.items():
            for profile,source in sources.items():ue.register_mixin_profile(self.classes[kind],profile,source)
        for kind in self.static_profiles:ue.clear_mixin_profile(self.classes[kind].get_cdo())
        for cue in self.cues:
            if not dead(cue):
                audio=cue.get_property('Audio_OnHeal')
                if valid(audio):audio.call_function('Stop')
                ue.clear_mixin_profile(cue);cue.call_function('K2_EndGameplayCue')
        for effect in self.effects:
            if valid(effect):effect.call_function('K2_DestroyComponent',effect.call_function('GetOwner'))
        for actor in self.actors:
            if not dead(actor):actor.actor_destroy()
        self.report.update(owned_actors_destroyed=all(dead(a) for a in self.actors),owned_effects_removed=all(not valid(e) for e in self.effects),original_health_unchanged=self.healths()==self.health_before,
            production_profiles_restored=all(any(r['target_class']==self.classes[kind] and all(r['profiles'][p]['python_class'] is source and len(r['profiles'][p]['functions'])==1 for p,source in sources.items()) for r in ue.get_registered_mixins()) for kind,sources in self.sources.items()))
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native small Burst total timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='heal-retrigger':self.heal_retrigger()
            elif self.phase=='heal-lifetime':self.heal_lifetime()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write();(ue.log_error if error else ue.log)('UEP_SMALL_BURST_CUE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_SMALL_BURST_CUE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPSmallBurstCueResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
