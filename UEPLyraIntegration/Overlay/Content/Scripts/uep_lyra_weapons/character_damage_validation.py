"""Native parent effects, typed messages, actual number/lens/decal state and timer."""
import atexit
import sys
import time
import traceback
import unreal_engine as ue
from unreal_engine.structs import GameplayTag,GameplayTagContainer,GameplayEffectContextHandle
from uep_lyra_abilities.auto_respawn_helpers_validation import Validation as Ready
from uep_lyra_abilities.grenade_activation_validation import Validation as Health
from uep_lyra_world.effect_pad_mixin import valid
from uep_lyra_abilities.melee_trace_mixin import native_outputs,break_hit
from uep_lyra_audio.music_manager_lifecycle_mixin import DAMAGE
from .weapon_fire_fx_validation import parameter
from . import character_damage_mixin as policy
from .character_damage_contract import require,validate

ACTION='/Game/Characters/Heroes/Mannequin/Animations/Actions/'
FAMILIES=dict(front=['AM_MM_HitReact_Front_Lgt_01','AM_MM_HitReact_Front_Lgt_02','AM_MM_HitReact_Front_Med_01','AM_MM_HitReact_Front_Med_02'],
    back=['AM_MM_HitReact_Back_Med_01','AM_MM_HitReact_Front_Med_02'],right=['AM_MM_HitReact_Right_Med_01','AM_MM_HitReact_Front_Lgt_02'],left=['AM_MM_HitReact_Left_Med_01','AM_MM_HitReact_Front_Lgt_02'])


def vec(v):return [float(v.x),float(v.y),float(v.z)]
def path(obj):return obj.get_path_name() if valid(obj) else None
def dead(actor):return not valid(actor) or actor.call_function('IsActorBeingDestroyed')


class Validation(Ready):
    healths=Health.healths
    def __init__(self,result):
        super().__init__(result);self.require_auto_active=False;self.actors=[];self.cues=[];self.materials=[];self.decals=[];self.sources={};self.group_calls=[];self.messages=[]
        self.report=dict(status='running',error=None,weak_cases=[],selector_cases=[],parent_cases=[],timer_cases=[])
        for key in ('full_acceptance','network_acceptance','packaged_runtime','pixels_tested','audio_playback_tested','health_properties_written','native_rng_values_injected','rpc_function_overridden','parent_effects_disabled','native_timer_properties_written'):self.report[key]=False
    def own(self,cls='Actor'):
        actor=self.world.actor_spawn(ue.find_class(cls));actor.call_function('SetReplicates',False);self.actors.append(actor);return actor
    def spawn(self,profile):
        actor=self.world.actor_spawn(self.cls);self.cues.append(actor);ue.set_mixin_profile(actor,profile);actor.call_function('SetActorHiddenInGame',False);return actor
    def native_decals(self):return {d.get_path_name():d for d in ue.tobject_iterator(ue.find_class('DecalComponent')) if valid(d)}
    def begin(self):
        self.report['native_mode']=str(policy.lib('UEPLyraBridgeLibrary').call_function('GetBridgeForWorld',self.world).call_function('CaptureSnapshot').NetMode)
        self.health_before=self.healths();self.cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(self.cls)
        self.probe=ue.load_class('/Game/UEPValidation/BP_CharacterDamageProbe.BP_CharacterDamageProbe_C').get_cdo();self.probe.add_to_root()
        self.foreign=self.own();self.foreign.add_actor_root_component(ue.find_class('SceneComponent'),'UEPDamageForeign')
        self.basis=self.own();self.basis.add_actor_root_component(ue.find_class('SceneComponent'),'UEPDamageBasis')
        self.pop=self.controller.get_component_by_type(ue.find_class('LyraNumberPopComponent'));self.owned_pop=None
        if not valid(self.pop):
            self.pop=self.controller.add_actor_component(ue.load_class('/Game/Effects/Blueprints/B_NiagaraNumberPopComponent.B_NiagaraNumberPopComponent_C'),'UEPDamageNumberPop');self.owned_pop=self.pop
        require(self.pop.is_a(ue.find_class('LyraNumberPopComponent_NiagaraText')),'actual Niagara number-pop component required')
        self.style=self.pop.get_property('Style');require(valid(self.style),'native number-pop style absent')
        self.original_pop_component=self.pop.get_property('NiagaraComp');self.original_pop_values=self.pop_values()
        self.original_pop_active=bool(self.original_pop_component.call_function('IsActive')) if valid(self.original_pop_component) else False
        self.original_pop_location=self.original_pop_component.call_function('K2_GetComponentLocation') if valid(self.original_pop_component) else None
        self.setup_materials();self.observe();self.helpers();self.parents();self.timer_index=0;self.start_timer()
    def setup_materials(self):
        self.mats={None:None}
        for name,tag,surface in (('plain',None,0),('tagged-none',None,0),('weak','Gameplay.Zone.WeakSpot',2),('parent','Gameplay.Zone',1),('ordinary','Status.Death.Dying',0)):
            cls=ue.find_class('PhysicalMaterial' if name=='plain' else 'PhysicalMaterialWithTags');obj=ue.new_object(cls);obj.add_to_root();obj.set_property('SurfaceType',surface)
            if name!='plain':obj.set_property('Tags',GameplayTagContainer(GameplayTags=[GameplayTag(TagName=tag)] if tag else []))
            self.materials.append(obj);self.mats[name]=obj
    def observe(self):
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.sources={n:r['python_class'] for n,r in row['profiles'].items()};owner=self
        for name,source in self.sources.items():
            methods={n:fn for n,fn in vars(source).items() if not n.startswith('__') and callable(fn)}
            def group(method):
                def invoke(actor,Positive):
                    owner.group_calls.append((method,bool(Positive)));return actor.call_mixin_original(method,Positive)
                invoke.override=method;return invoke
            methods['NativeLong']=group(policy.LONG);methods['NativeSide']=group(policy.SIDE)
            ue.register_mixin_profile(self.cls,name,type('ObservedDamageRng'+name,(),methods))
        self.music_cls=ue.load_class('/Game/Audio/Blueprints/B_MusicManagerComponent_Base.B_MusicManagerComponent_Base_C')
        self.music=self.statics.call_function('GetGameState',self.world).get_component_by_type(self.music_cls)
        self.music_fields={n:self.music.get_property(n) for n in ('Music System','Alpha_Intensity','Alpha_Mvmt','bIsMenu')};self.music.set_property('Music System',None)
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.music_cls];self.music_sources={n:r['python_class'] for n,r in row['profiles'].items()}
        for name,source in self.music_sources.items():
            methods={n:fn for n,fn in vars(source).items() if not n.startswith('__') and callable(fn)}
            def around(handler):
                def invoke(component,Payload):
                    if component==owner.music:owner.messages.append(dict(target=path(Payload.Target),instigator=path(Payload.Instigator),magnitude=float(Payload.Magnitude),verb=str(Payload.Verb.TagName)))
                    return handler(component,Payload)
                invoke.override=DAMAGE;return invoke
            methods['DamageMessage']=around(source.DamageMessage);ue.register_mixin_profile(self.music_cls,name,type('ObservedDamageVerb'+name,(),methods))
    def helpers(self):
        for profile in ('BlueprintFallback','Python'):
            actor=self.spawn(profile);selected='python' if profile=='Python' else 'fallback'
            for name in (None,'plain','tagged-none','weak','parent','ordinary'):
                for caller in ('direct','blueprint'):
                    before=policy.evidence(actor)[selected+'_weak'];value=(actor.call_function('EvaluateWeakSpot',self.mats[name]) if caller=='direct' else self.probe.call_function('Weak',actor,self.mats[name]))[0]
                    self.report['weak_cases'].append(dict(profile=profile,path=caller,name=str(name),actual=bool(value),expected=name=='weak',dispatch_entries=policy.evidence(actor)[selected+'_weak']-before))
            normals=[(x,y,0.) for x,y in ((1.,0.),(-1.,0.),(0.,0.),(1.,.5),(1.,-.5),(1.,.500000001),(1.,-.500000001),(0.,.5001),(0.,-.5001),(2.,7.),(-3.,-8.),(1.,.25),(1.,-.25),(0.,1.),(0.,-1.),(-1.,.3))]
            for normal in normals:
                vector=policy.lib('KismetMathLibrary').call_function('MakeVector',*normal);front,right=normal[:2]
                straight=bool(policy.lib('KismetMathLibrary').call_function('InRange_FloatFloat',right,-.5,.5,True,True));positive=front>0. if straight else right>0.
                group=policy.LONG if straight else policy.SIDE;family=('front' if positive else 'back') if straight else ('right' if positive else 'left')
                for caller in ('direct','blueprint'):
                    self.group_calls=[];before=policy.evidence(actor)[selected+'_select']
                    montage=(actor.call_function(policy.SELECT,vector,self.basis) if caller=='direct' else self.probe.call_function('Select',actor,vector,self.basis))[0]
                    require(len(self.group_calls)==1,'selector must invoke one original native RNG data group');actual_group,actual_positive=self.group_calls[0]
                    self.report['selector_cases'].append(dict(profile=profile,path=caller,normal=list(normal),returned=path(montage),allowed=[ACTION+s+'.'+s for s in FAMILIES[family]],actual_native_group=actual_group,actual_positive=actual_positive,expected_group=group,expected_positive=positive,dispatch_entries=policy.evidence(actor)[selected+'_select']-before))
            actor.call_function('K2_EndGameplayCue')
    def hit(self,material):
        point=self.pawn.get_property('Mesh').call_function('GetSocketLocation','head')
        return policy.lib('GameplayStatics').call_function('MakeHitResult',bBlockingHit=True,bInitialOverlap=False,Time=.5,Distance=5.,Location=point,ImpactPoint=ue.FVector(point.x+50.,point.y,point.z),Normal=ue.FVector(1.,0.,0.),ImpactNormal=ue.FVector(0.,0.,1.),
            PhysMat=material,HitActor=self.pawn,HitComponent=self.pawn.get_property('Mesh'),HitBoneName='head',BoneName='head',HitItem=0,ElementIndex=0,FaceIndex=-1,TraceStart=ue.FVector(point.x+100.,point.y+200.,point.z+50.),TraceEnd=point)
    def params(self,material,decoy=False,raw=4.5):
        context=self.asc.call_function('MakeEffectContext');hit=self.hit(material);policy.lib('AbilitySystemBlueprintLibrary').call_function('EffectContextAddHitResult',context,hit,True)
        value=policy.lib('AbilitySystemBlueprintLibrary').call_function('MakeGameplayCueParameters',NormalizedMagnitude=.25,RawMagnitude=raw,EffectContext=context,MatchedTagName=GameplayTag(),OriginalTag=GameplayTag(TagName='Lyra.Damage.Taken.Message'),AggregatedSourceTags=GameplayTagContainer(),AggregatedTargetTags=GameplayTagContainer(),Location=ue.FVector(-500.,-600.,-700.),Normal=ue.FVector(0.,-1.,0.),Instigator=self.foreign if decoy else self.controller.PlayerState,EffectCauser=self.foreign,SourceObject=None,PhysicalMaterial=material,GameplayEffectLevel=1,AbilityLevel=1,TargetAttachComponent=None,bReplicateLocationWhenUsingMinimalRepProxy=False)
        return value,break_hit(hit)
    def pop_values(self):
        comp=self.pop.get_property('NiagaraComp')
        if not valid(comp):return []
        return list(policy.lib('NiagaraDataInterfaceArrayFunctionLibrary').call_function('GetNiagaraArrayVector4',comp,self.style.get_property('NiagaraArrayName')))
    def parents(self):
        allowed={ACTION+s+'.'+s for values in FAMILIES.values() for s in values}
        for profile in ('BlueprintFallback','Python'):
            selected='python' if profile=='Python' else 'fallback'
            for critical in (False,True):
                for decoy in (False,True):
                    actor=self.spawn(profile);params,hit=self.params(self.mats['weak' if critical else 'plain'],decoy)
                    before=dict(policy.evidence(actor));before_pops=self.pop_values();old=self.native_decals();self.messages=[]
                    returned=actor.call_function('OnExecute',self.pawn,params);after=policy.evidence(actor);values=self.pop_values();new=[d for k,d in self.native_decals().items() if k not in old];self.decals.extend(new)
                    comp=self.pop.get_property('NiagaraComp');expected=policy.lib('KismetMathLibrary').call_function('Round',params.RawMagnitude)*(-1 if critical else 1)
                    spawn_result=actor.get_property('BurstSpawnResults');lens_list=[actor.call_function(policy.LENS_OBJECT,spawn_result,i) for i in range(actor.call_function(policy.LENS_COUNT,spawn_result))];lens_parameters=True;lens_count=0
                    math=policy.lib('KismetMathLibrary');direction=math.call_function('Normal',math.call_function('Subtract_VectorVector',hit['TraceStart'],hit['TraceEnd']),.0001)
                    for lens in lens_list:
                        if lens is not None and lens.is_a(ue.load_class(policy.LENS)):
                            nc=lens.get_property('NiagaraComponent');a=native_outputs('NiagaraComponent','GetVariableVec3',nc.call_function('GetVariableVec3','HitDirection'))
                            b=native_outputs('NiagaraComponent','GetVariablePosition',nc.call_function('GetVariablePosition','AttackWorldPosition'))
                            if not b.get('bIsValid'):b=native_outputs('NiagaraComponent','GetVariableVec3',nc.call_function('GetVariableVec3','AttackWorldPosition'))
                            lens_count+=1;lens_parameters &= bool(a.get('bIsValid')) and bool(b.get('bIsValid')) and all(abs(x-y)<.0001 for x,y in zip(vec(a['ReturnValue']),vec(direction))) and all(abs(x-y)<.0001 for x,y in zip(vec(b['ReturnValue']),vec(hit['TraceStart'])))
                    decal_ok=True
                    rotation=math.call_function('Conv_VectorToRotator',math.call_function('Multiply_VectorVector',hit['ImpactNormal'],ue.FVector(-1.,-1.,-1.)))
                    transformed=native_outputs('SkinnedMeshComponent','TransformToBoneSpace',self.pawn.get_property('Mesh').call_function('TransformToBoneSpace',hit['HitBoneName'],hit['Location'],rotation))
                    for decal in new:
                        decal_ok &= decal.call_function('GetAttachParent')==self.pawn.get_property('Mesh') and str(decal.call_function('GetAttachSocketName'))=='head' and path(decal.get_property('DecalMaterial'))==policy.DECAL and vec(decal.get_property('DecalSize'))==[5.,8.,8.] and float(decal.get_property('FadeStartDelay'))==5. and float(decal.get_property('FadeDuration'))==5.
                        actual_rot=decal.get_property('RelativeRotation');expected_rot=transformed['OutRotation']
                        decal_ok &= all(abs(a-b)<.0001 for a,b in zip(vec(decal.get_property('RelativeLocation')),vec(transformed['OutPosition']))) and all(abs(getattr(actual_rot,k)-getattr(expected_rot,k))<.0001 for k in ('roll','pitch','yaw'))
                    montage=actor.get_property('Montage');playing=bool(self.pawn.get_property('Mesh').call_function('GetAnimInstance').call_function('Montage_IsPlaying',montage))
                    self.report['parent_cases'].append(dict(profile=profile,surface=2 if critical else 0,cue_instigator_decoy=decoy,native_return=returned,
                        burst_entries=after[selected+'_burst']-before[selected+'_burst'],execute_entries=after[selected+'_execute']-before[selected+'_execute'],rpc_body_entries=after[selected+'_rpc_body']-before[selected+'_rpc_body'],actual_messages=len(self.messages),message_target_matches=len(self.messages)==1 and self.messages[0]['target']==path(self.pawn),number_pop_added=len(values)-len(before_pops),native_pop_value=float(values[-1].w) if values else None,expected_pop_value=float(expected),native_pop_location=vec(values[-1]) if values else None,expected_pop_location=vec(hit['Location']),context_instigator_is_local_state=policy.lib('AbilitySystemBlueprintLibrary').call_function('EffectContextGetInstigatorActor',params.EffectContext)==self.controller.PlayerState,selected_montage_in_allowed_set=path(montage) in allowed,native_character_montage_playing=playing,actual_new_decals=len(new),decal_attachment_and_native_properties_match=bool(decal_ok),actual_lens_updates=lens_count,actual_native_lens_parameters_match=bool(lens_parameters)))
                    actor.call_function('K2_EndGameplayCue');self.pawn.call_function('StopAnimMontage',montage)
    def start_timer(self):
        self.timer_profile=('BlueprintFallback','Python')[self.timer_index];self.timer_actor=self.spawn(self.timer_profile);params,_=self.params(self.mats['plain']);self.timer_actor.call_function('OnExecute',self.pawn,params)
        self.timer_start=self.game_time();self.before_deadline=False;self.enter('timer')
    def timer(self):
        elapsed=self.game_time()-self.timer_start
        if 1.1<=elapsed<4.:self.before_deadline=not bool(self.timer_actor.get_property('bHidden'))
        if not self.timer_actor.get_property('bHidden'):require(elapsed<7.5,'native minimum lifetime did not recycle Cue');return
        self.report['timer_cases'].append(dict(profile=self.timer_profile,visible_before_deadline=self.before_deadline,native_recycled_after_minimum_lifetime=True,elapsed=elapsed));self.timer_index+=1
        if self.timer_index<2:self.start_timer()
        else:self.start_manager()
    def start_manager(self):
        self.manager_target=self.own();self.manager_target.add_actor_root_component(ue.find_class('SceneComponent'),'UEPNaturalDamageTarget')
        self.manager_before={a.get_path_name():dict(policy.evidence(a)) for a in self.world.all_actors() if valid(a) and a.is_a(self.cls)}
        self.messages=[];params,_=self.params(self.mats['plain']);tag=self.cls.get_cdo().get_property('GameplayCueTag')
        policy.lib('GameplayCueFunctionLibrary').call_function('ExecuteGameplayCueOnActor',self.manager_target,tag,params);self.enter('manager')
    def manager(self):
        require(time.monotonic()-self.phase_started<15.,'real damage Cue manager did not execute')
        found=[a for a in self.world.all_actors() if valid(a) and a.is_a(self.cls) and a.call_function('GetOwner')==self.manager_target]
        if not found:return
        actor,=found;self.cues.append(actor);before=self.manager_before.get(actor.get_path_name(),{});after=policy.evidence(actor)
        self.report.update(natural_manager_python_burst_entries=after['python_burst']-before.get('python_burst',0),natural_manager_python_execute_entries=after['python_execute']-before.get('python_execute',0),natural_manager_typed_message_entries=len(self.messages));self.finish()
    def cleanup(self):
        for d in self.decals:
            if valid(d):d.call_function('K2_DestroyComponent',d.call_function('GetOwner'))
        self.report['owned_decal_components_removed']=all(not valid(d) for d in self.decals)
        for actor in self.cues:
            if not dead(actor):actor.call_function('K2_EndGameplayCue')
        for actor in self.actors:
            if not dead(actor):actor.call_function('K2_DestroyActor')
        for obj in self.materials:obj.remove_from_root()
        self.report['owned_material_roots_released']=all(not obj.is_rooted() for obj in self.materials)
        if hasattr(self,'original_pop_values'):
            current=self.pop.get_property('NiagaraComp')
            if valid(self.original_pop_component):
                policy.lib('NiagaraDataInterfaceArrayFunctionLibrary').call_function('SetNiagaraArrayVector4',current,self.style.get_property('NiagaraArrayName'),self.original_pop_values)
                current.call_function('K2_SetWorldLocation',self.original_pop_location,False,True)
                if not self.original_pop_active:current.call_function('Deactivate')
                self.report['number_pop_state_restored']=[(v.x,v.y,v.z,v.w) for v in self.pop_values()]==[(v.x,v.y,v.z,v.w) for v in self.original_pop_values]
            else:
                if valid(current):current.call_function('K2_DestroyComponent',current.call_function('GetOwner'))
                self.pop.set_property('NiagaraComp',None);self.report['number_pop_state_restored']=self.pop.get_property('NiagaraComp') is None
            if self.owned_pop is not None:self.owned_pop.call_function('K2_DestroyComponent',self.controller)
        for name,source in self.sources.items():ue.register_mixin_profile(self.cls,name,source)
        if self.sources:
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.cls];self.report['production_profiles_restored']=all(row['profiles'][n]['python_class'] is source and len(row['profiles'][n]['functions'])==7 for n,source in self.sources.items())
        if hasattr(self,'music_sources'):
            for name,value in self.music_fields.items():self.music.set_property(name,value)
            for name,source in self.music_sources.items():ue.register_mixin_profile(self.music_cls,name,source)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==self.music_cls];self.report['music_fields_and_providers_restored']=all(self.music.get_property(k)==v for k,v in self.music_fields.items()) and all(row['profiles'][n]['python_class'] is source for n,source in self.music_sources.items())
        if hasattr(self,'probe'):self.probe.remove_from_root();self.report['probe_unrooted']=not self.probe.is_rooted()
        self.report['original_health_unchanged']=hasattr(self,'health_before') and self.healths()==self.health_before
    def tick(self,seconds):
        if self.finished:return False
        try:
            require(time.monotonic()-self.started<240.,'native character damage timeout')
            if self.phase=='ready':self.ready()
            elif self.phase=='timer':self.timer()
            elif self.phase=='manager':self.manager()
            self.report['phase']=self.phase;self.write();return not self.finished
        except Exception:self.finish(traceback.format_exc());return False
    def finish(self,error=None):
        if self.finished:return
        self.finished=True
        try:self.cleanup()
        except Exception:error=(error or '')+traceback.format_exc()
        self.report.update(status='failed' if error else 'awaiting_shutdown',error=error);self.write()
        (ue.log_error if error else ue.log)('UEP_CHARACTER_DAMAGE_DIFFERENTIAL_'+('FAILED '+error if error else 'PASSED'));ue.request_exit()
    def finalize(self):
        if self.report['status']=='awaiting_shutdown':
            try:self.report['status']='passed';validate(self.report)
            except Exception:self.report.update(status='failed',error=traceback.format_exc())
        self.write();(ue.log if self.report['status']=='passed' else ue.log_error)('UEP_CHARACTER_DAMAGE_SHUTDOWN_'+self.report['status'].upper())


result=next((v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPCharacterDamageResult=')),None)
if result:
    validation=Validation(result);atexit.register(validation.finalize);ticker=ue.add_ticker(validation.tick)
