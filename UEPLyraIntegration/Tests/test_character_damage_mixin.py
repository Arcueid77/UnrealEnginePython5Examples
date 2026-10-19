"""Exact weak-spot, direction, context-instigator and native-shell policy branches."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs');enums=types.ModuleType('unreal_engine.enums')
structs.GameplayTag=lambda **kw:types.SimpleNamespace(**kw);enums.EAttachLocation=types.SimpleNamespace(KeepRelativeOffset=0)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
trace=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');trace.break_hit=lambda x:x;trace.native_outputs=lambda cls,fn,value:value
spec=importlib.util.spec_from_file_location('_character_damage_policy',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_weapons/character_damage_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':trace}):spec.loader.exec_module(policy)


class Class:
    def __init__(self,name,owner):self.name,self.owner=name,owner
    def get_cdo(self):return types.SimpleNamespace(call_function=lambda method,*a,**kw:self.owner.backend(method,a,kw))


class CharacterDamagePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.normal=(1.,0.,0.);self.critical=False;self.tags_exact=True;self.local=True;self.has_pop=True
        self.hit=dict(Location=(1.,2.,3.),Normal=(0.,0.,1.),ImpactNormal=(0.,1.,0.),HitBoneName='head',PhysMat=None,HitActor=None,TraceStart=(5.,6.,7.),TraceEnd=(1.,2.,3.))
        self.pop=types.SimpleNamespace(call_function=lambda *a:self.calls.append(('popup',*a)))
        self.controller=types.SimpleNamespace(get_component_by_type=lambda cls:self.pop if self.has_pop else None)
        self.pawn=types.SimpleNamespace(call_function=lambda method:self.local if method=='IsLocallyControlled' else self.controller)
        self.instigator=types.SimpleNamespace(is_a=lambda cls:cls.name=='PlayerState',call_function=lambda name:self.pawn)
        self.data={'Target':None,'Montage':None};self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.invoke,
            call_mixin_original=lambda *a:('original-montage',))
        native.find_class=lambda name:Class(name,self);native.load_class=lambda name:Class(name,self);native.load_object=lambda cls,path:path
        native.find_struct=lambda name:lambda **kw:types.SimpleNamespace(**kw);native.FVector=lambda *a:a
        self.params=types.SimpleNamespace(EffectContext='context',RawMagnitude=4.5,AggregatedSourceTags='source-tags',AggregatedTargetTags='target-tags',Instigator='decoy')
    def write(self,name,value):self.data[name]=value;self.calls.append(('write',name,value))
    def invoke(self,name,*args):
        self.calls.append(('actor',name,args))
        if name==policy.SELECT:return ('chosen-montage',)
        if name=='EvaluateWeakSpot':return (self.critical,)
        if name in (policy.LONG,policy.SIDE):return 'native-random-montage'
    def backend(self,name,args,kwargs):
        self.calls.append(('native',name,args,kwargs))
        if name=='HasTag':return self.tags_exact
        if name in ('GetHitResult','EffectContextGetHitResult'):return self.hit
        if name=='EffectContextGetInstigatorActor':return self.instigator
        if name=='Dot_VectorVector':return sum(a*b for a,b in zip(*args))
        if name=='InRange_FloatFloat':return args[1]<=args[0]<=args[2]
        if name=='Round':return 5
        if name=='CueParametersToVerbMessage':return types.SimpleNamespace(Target='old-target',Magnitude=4.5)
        if name=='GetGameInstanceSubsystem':return 'message-router'
        if name=='GetAbilitySystemComponent':return 'asc' if self.data['Target'] is not None else None
        if name=='Subtract_VectorVector':return tuple(a-b for a,b in zip(*args))
        if name=='Normal':
            length=sum(x*x for x in args[0])**.5
            return tuple(x/length for x in args[0]) if length else (0.,0.,0.)
    def basis(self):return types.SimpleNamespace(call_function=lambda name:(1.,0.,0.) if name=='GetActorForwardVector' else (0.,1.,0.))
    def test_plain_material_and_none_are_not_tagged_weak_spots(self):
        self.assertFalse(policy.weak(self.actor,None)['DidHitWeakSpot'])
        self.assertFalse(policy.weak(self.actor,types.SimpleNamespace(is_a=lambda cls:False))['DidHitWeakSpot'])
    def test_tagged_material_requires_exact_weak_tag(self):
        obj=types.SimpleNamespace(is_a=lambda cls:True,get_property=lambda field:'tags');self.assertTrue(policy.weak(self.actor,obj)['DidHitWeakSpot'])
        entry=next(c for c in self.calls if c[:2]==('native','HasTag'));self.assertEqual(entry[2][1].TagName,'Gameplay.Zone.WeakSpot');self.assertIs(entry[2][2],True)
    def test_parent_or_child_tag_does_not_override_native_exact_result(self):
        self.tags_exact=False;obj=types.SimpleNamespace(is_a=lambda cls:True,get_property=lambda field:'tags');self.assertFalse(policy.weak(self.actor,obj)['DidHitWeakSpot'])
    def test_inclusive_right_dot_bounds_use_front_back_group(self):
        for right in (-.5,.5):
            self.calls=[];policy.select(self.actor,(1.,right,0.),self.basis());self.assertIn(('actor',policy.LONG,(True,)),self.calls)
    def test_strict_zero_forward_chooses_back_data(self):
        policy.select(self.actor,(0.,0.,0.),self.basis());self.assertIn(('actor',policy.LONG,(False,)),self.calls)
    def test_positive_right_chooses_authored_right_group(self):
        policy.select(self.actor,(0.,.5001,0.),self.basis());self.assertIn(('actor',policy.SIDE,(True,)),self.calls)
    def test_negative_right_chooses_authored_left_group(self):
        policy.select(self.actor,(0.,-.5001,0.),self.basis());self.assertIn(('actor',policy.SIDE,(False,)),self.calls)
    def test_selector_does_not_normalize_input_or_replace_native_rng(self):
        policy.select(self.actor,(4.,6.,0.),self.basis());self.assertEqual(policy.evidence(self.actor)['last_selection']['right'],6.)
        self.assertFalse(any(c[:2] in (('native','Normal'),('native','RandomIntegerInRange')) for c in self.calls))
    def test_named_output_keeps_native_selected_montage(self):self.assertEqual(policy.select(self.actor,self.normal,self.basis()),{'Hit Montage':'native-random-montage'})
    def test_broadcast_overwrites_converted_target_and_uses_target_world(self):
        target=object();policy.broadcast(self.actor,target,self.params);entry=next(c for c in self.calls if c[:2]==('actor',policy.BROADCAST))
        self.assertIs(entry[2][2].Target,target);self.assertEqual(entry[2][1].TagName,'Lyra.Damage.Taken.Message')
    def test_execute_casts_context_instigator_instead_of_cue_instigator(self):
        self.instigator=None;self.assertFalse(policy.execute_body(self.actor,'target',self.params));self.assertEqual(self.calls,[('native','EffectContextGetInstigatorActor',('context',),{})])
    def test_missing_number_pop_stops_local_branch(self):
        self.has_pop=False;policy.execute_body(self.actor,'target',self.params);self.assertFalse(any(c[0]=='popup' or c[:2]==('native','PlaySound2D') for c in self.calls))
    def test_popup_preserves_native_round_location_tags_and_critical(self):
        self.critical=True;policy.execute_body(self.actor,'target',self.params);request=next(c[2] for c in self.calls if c[:2]==('popup','AddNumberPop'))
        self.assertEqual((request.WorldLocation,request.SourceTags,request.TargetTags,request.NumberToDisplay,request.bIsCriticalDamage),((1.,2.,3.),'source-tags','target-tags',5,True))
    def test_invalid_hit_actor_stops_given_sound_after_popup(self):
        policy.execute_body(self.actor,'target',self.params);self.assertEqual(policy.evidence(self.actor)['number_pops'],1);self.assertEqual(policy.evidence(self.actor)['sounds'],0)
    def test_missing_instigator_pawn_delegates_native_diagnostics(self):self.pawn=None;self.assertIs(policy.execute_body(self.actor,None,self.params),True)
    def test_rpc_body_calls_native_character_play_only(self):
        character=types.SimpleNamespace(call_function=lambda *a:self.calls.append(a));self.assertIs(policy.play_montage(self.actor,character,'montage'),False);self.assertEqual(self.calls,[('PlayAnimMontage','montage',1.,'None')])
    def test_rpc_invalid_character_preserves_original_shell_body(self):self.assertIs(policy.play_montage(self.actor,None,'montage'),True)
    def test_missing_target_animation_does_not_call_selector_or_rpc(self):
        policy.animation(self.actor);self.assertFalse(any(c[0]=='actor' for c in self.calls))
    def test_source_sound_arguments_keep_ui_and_defaults(self):
        policy.sound(self.actor,'DamageTaken',True);entry=next(c for c in self.calls if c[:2]==('native','PlaySound2D'))
        self.assertIn('DamageTakenWeakSpot_nl_meta',entry[3]['Sound']);self.assertEqual((entry[3]['VolumeMultiplier'],entry[3]['PitchMultiplier'],entry[3]['StartTime'],entry[3]['bIsUISound']),(1.,1.,0.,True))
    def test_lens_interface_is_read_only_through_native_accessors(self):
        component=types.SimpleNamespace(call_function=lambda *a:self.calls.append(('lens',*a)))
        lens=types.SimpleNamespace(is_a=lambda cls:True,get_property=lambda name:component)
        target=types.SimpleNamespace(is_a=lambda cls:True)
        previous=self.actor.call_function
        def invoke(name,*args):
            if name==policy.LENS_COUNT:return 1
            if name==policy.LENS_OBJECT:return lens
            return previous(name,*args)
        self.actor.call_function=invoke
        policy.burst(self.actor,target,self.params,object())
        self.assertEqual([c[1] for c in self.calls if c[0]=='lens'],['SetVariableVec3','SetVariablePosition'])
        self.assertIn(('lens','SetVariablePosition','AttackWorldPosition',(5.,6.,7.)),self.calls)
    def test_non_character_burst_still_broadcasts_and_stores_target(self):
        target=types.SimpleNamespace(is_a=lambda cls:False);policy.burst(self.actor,target,self.params,object())
        self.assertIs(self.data['Target'],target);self.assertTrue(any(c[:2]==('actor','BroadcastDamageTaken') for c in self.calls));self.assertFalse(any(c[:2]==('actor',policy.ANIMATE) for c in self.calls))
    def test_given_kill_sound_uses_native_health_normalized_boundary(self):
        for health,expected in ((0.,2),(-.1,2),(.001,1)):
            self.calls=[]
            victim=types.SimpleNamespace(get_component_by_type=lambda cls:types.SimpleNamespace(call_function=lambda name:health));self.hit['HitActor']=victim
            policy.execute_body(self.actor,victim,self.params)
            self.assertEqual(sum(c[:2]==('native','PlaySound2D') for c in self.calls),expected)
    def test_nonlocal_instigator_uses_target_locally_viewed_not_local_control(self):
        self.local=False;self.critical=True;prior=self.backend
        viewed=types.SimpleNamespace(call_function=lambda name:name=='IsLocallyViewed');pc=types.SimpleNamespace(call_function=lambda name:viewed)
        self.backend=lambda name,args,kwargs:pc if name=='GetPlayerControllerFromObject' else prior(name,args,kwargs)
        policy.execute_body(self.actor,object(),self.params)
        self.assertTrue(any(c[:2]==('native','PlaySound2D') and 'DamageTakenWeakSpot' in c[3]['Sound'] for c in self.calls));self.assertFalse(any(c[0]=='popup' for c in self.calls))
    def test_nonlocal_unviewed_target_does_not_play_taken_sound(self):
        self.local=False;prior=self.backend
        viewed=types.SimpleNamespace(call_function=lambda name:False);pc=types.SimpleNamespace(call_function=lambda name:viewed)
        self.backend=lambda name,args,kwargs:pc if name=='GetPlayerControllerFromObject' else prior(name,args,kwargs)
        policy.execute_body(self.actor,object(),self.params);self.assertFalse(any(c[:2]==('native','PlaySound2D') for c in self.calls))
