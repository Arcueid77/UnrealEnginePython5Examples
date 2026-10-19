"""Feedback call order, native clock/RPC boundaries and local audio selection."""
import importlib
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts'))
native=types.ModuleType('unreal_engine');native.find_class=lambda n:n;native.load_object=lambda cls,p:p
enums=types.ModuleType('unreal_engine.enums');enums.ETimelineDirection=types.SimpleNamespace(Forward=0,Backward=1)
validity=types.ModuleType('uep_lyra_world.effect_pad_mixin');validity.valid=lambda x:x is not None
outputs=types.ModuleType('uep_lyra_abilities.melee_trace_mixin');outputs.native_outputs=lambda *a:a[-1]
libs=types.ModuleType('uep_lyra_weapons.hero_burst_cue_mixin');libs.lib=lambda n:None
state=types.ModuleType('uep_lyra_world.control_point_state_mixin');state.CLASS='volume-class';state.one=lambda x:x[0] if isinstance(x,tuple) else x
base=type('State',(),{n:lambda self:None for n in ('Construct','Check','Contest','Recapture','Ready','Enter','Exit','Recompute')});state.LyraControlPointStatePythonProfile=state.LyraControlPointStateBlueprintFallbackProfile=base
package=importlib.import_module('uep_lyra_world')
spec=importlib.util.spec_from_file_location('uep_lyra_world._feedback_policy_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_world/control_point_feedback_mixin.py');policy=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.enums':enums,'uep_lyra_world.effect_pad_mixin':validity,'uep_lyra_abilities.melee_trace_mixin':outputs,'uep_lyra_weapons.hero_burst_cue_mixin':libs,'uep_lyra_world.control_point_state_mixin':state}),patch.object(package,'control_point_state_mixin',state,create=True):spec.loader.exec_module(policy)


def rgba(*v):return types.SimpleNamespace(**dict(zip(('r','g','b','a'),v)))


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.authority=True;self.audio_active=True;self.local=True;self.local_team=1;self.pawns=[];self.teams={}
        self.components={n:self.obj(n) for n in ('Cube','NS_CapturePointCounter','NS_CapturePoint','Audio_CPProgress','Audio_CPComplete','PointLight','TL_ConvertPoint','ControlPointGameMode')}
        self.data=dict(self.components,OverlappingTeams=[1],OverlappingPawns=['pawn-a'],OwnerTeamID=-1,OwningTeamColor=rgba(1,1,1,1),TargetColor=rgba(0,0,1,1),StaticMeshList=[],SM_Components=[],LightList=[])
        self.actor=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.actor_call);policy.lib=lambda name:types.SimpleNamespace(call_function=lambda f,*a:self.backend(name,f,a));native.load_class=lambda p:types.SimpleNamespace(get_cdo=lambda:self.obj('GeneralAudio'))
    def obj(self,name,properties=None):return types.SimpleNamespace(get_property=lambda k:(properties or {}).get(k),call_function=lambda f,*a:self.component(name,f,a))
    def write(self,k,v):self.data[k]=v;self.calls.append(('write',k,v))
    def actor_call(self,f,*a):
        if f=='HasAuthority':return self.authority
        self.calls.append(('actor',f,*a))
    def component(self,n,f,a):
        self.calls.append((n,f,*a))
        if f=='IsActive':return self.audio_active
        if f=='IsLocallyViewed':return self.local
        if f=='GetTeamColor':return (rgba(0,1,0,1),)
    def backend(self,n,f,a):
        if f=='LinearColorLerp':return rgba(*[getattr(a[0],k)+(getattr(a[1],k)-getattr(a[0],k))*a[2] for k in ('r','g','b','a')])
        if f=='Conv_LinearColorToVector':return tuple(getattr(a[0],k) for k in ('r','g','b'))
        if f=='GetAllActorsOfClass':return {'OutActors':self.pawns}
        if f=='GetWorldSubsystem':return types.SimpleNamespace(call_function=lambda f,*a:dict(bIsPartOfTeam=self.teams.get(id(a[0])) is not None,TeamId=self.teams.get(id(a[0]),-1)))
        if f=='GetPlayerPawn':return self.local_pawn
    def test_mesh_collection_keeps_existing_and_adds_unique_in_source_order(self):
        a,b=self.obj('a'),self.obj('b');self.data.update(SM_Components=[a],StaticMeshList=[self.obj('ma',{'StaticMeshComponent':b}),self.obj('mb',{'StaticMeshComponent':a})]);self.assertIs(policy.meshes(self.actor),False);self.assertEqual(self.data['SM_Components'],[a,b])
    def test_invalid_mesh_list_falls_back_before_any_partial_writes(self):
        self.data['StaticMeshList']=[None];self.assertIs(policy.meshes(self.actor),True);self.assertFalse(self.calls)
    def test_timeline_updates_all_native_targets_with_raw_scalar_and_srgb_lights(self):
        self.data['SM_Components']=[self.obj('extra')];self.data['LightList']=[self.obj('light-actor',{'LightComponent':self.obj('extra-light')})];policy.update(self.actor,.25)
        self.assertEqual(self.calls[0],('Cube','SetVectorParameterValueOnMaterials','Color',(.75,.75,1.)))
        self.assertIn(('NS_CapturePointCounter','SetVariableFloat','RibbonProgression',.25),self.calls);self.assertIn(('extra','SetVectorParameterValueOnMaterials','Color',(.75,.75,1.)),self.calls)
        self.assertTrue(all(x[-1] is True for x in self.calls if x[1]=='SetLightColor'));self.assertEqual(self.calls[-1],('Audio_CPProgress','SetFloatParameter','Progress',.25))
    def test_forward_finish_owner_capture_color_reset_clock_rpc_message_order(self):
        self.assertIs(policy.finish(self.actor,0),False)
        keys=[(x[0],x[1]) for x in self.calls];self.assertEqual(keys,[('write','OwnerTeamID'),('ControlPointGameMode','CapturePoint'),('ControlPointGameMode','GetTeamColor'),('write','OwningTeamColor'),('NS_CapturePointCounter','SetVariableFloat'),('NS_CapturePointCounter','Deactivate'),('TL_ConvertPoint','SetNewTime'),('actor','Capture Audio'),('actor',policy.MESSAGE)])
        self.assertEqual(self.calls[-3],('TL_ConvertPoint','SetNewTime',0.));self.assertEqual(self.data['OverlappingPawns'],['pawn-a'])
    def test_remote_forward_finish_does_not_score_or_rewind(self):
        self.authority=False;self.assertIs(policy.finish(self.actor,0),False);self.assertFalse(self.calls)
    def test_missing_team_uses_original_diagnostics_without_partial_capture(self):
        self.data['OverlappingTeams']=[];self.assertIs(policy.finish(self.actor,0),True);self.assertFalse(self.calls)
    def test_reverse_finish_rpc_precedes_native_clock_reset(self):
        policy.finish(self.actor,1);self.assertEqual(self.calls,[('actor','Clean Up VFX'),('TL_ConvertPoint','SetNewTime',0.)])
    def test_enter_local_sets_parameter_before_play(self):
        policy.enter(self.actor,self.obj('pawn'));self.assertEqual(self.calls[-2:],[('Audio_CPProgress','SetBoolParameter','LocalPlayerInside',True),('Audio_CPProgress','Play',0.)])
    def test_remote_and_null_enter_do_not_change_audio(self):
        self.local=False;policy.enter(self.actor,self.obj('pawn'));policy.enter(self.actor,None);self.assertFalse(any(x[0]=='Audio_CPProgress' for x in self.calls))
    def test_exit_active_local_uses_authored_half_second_delayed_stop(self):
        policy.exit_audio(self.actor,self.obj('pawn'));self.assertEqual(self.calls[-2:],[('Audio_CPProgress','SetBoolParameter','LocalPlayerInside',False),('Audio_CPProgress','StopDelayed',.5)])
    def test_exit_inactive_keeps_parameters_unchanged(self):
        self.audio_active=False;policy.exit_audio(self.actor,self.obj('pawn'));self.assertFalse(any(x[1]=='SetBoolParameter' for x in self.calls))
    def test_capture_audio_visits_every_local_pawn_without_break(self):
        a,b,c=[self.obj(n) for n in ('a','b','c')];self.pawns=[a,b,c];self.teams={id(a):1,id(b):2};policy.capture_audio(self.actor,1)
        self.assertEqual([x[-1] for x in self.calls if x[1]=='SetSound'],[policy.FRIENDLY,policy.ENEMY]);self.assertEqual(sum(x[1]=='Play' for x in self.calls),2)
    def test_music_duplicates_still_fire_once_only_when_local_pawn_inside(self):
        self.local_pawn='local';self.data['OverlappingPawns']=['local','local'];policy.music(self.actor);self.assertEqual(self.calls,[('GeneralAudio','FireStinger',True,self.actor)])
    def test_music_foreign_pawn_does_not_fire(self):
        self.local_pawn='foreign';policy.music(self.actor);self.assertFalse(self.calls)
    def test_clean_sets_zero_before_deactivation(self):
        policy.clean(self.actor);self.assertEqual(self.calls,[('NS_CapturePointCounter','SetVariableFloat','RibbonProgression',0.),('NS_CapturePointCounter','Deactivate')])
    def test_profiles_explicitly_publish_full_seventeen_method_family(self):
        for cls in (policy.LyraControlPointFeedbackPythonProfile,policy.LyraControlPointFeedbackBlueprintFallbackProfile):self.assertEqual(len([v for k,v in vars(cls).items() if callable(v) and not k.startswith('_')]),17)
    def test_fallback_preserves_native_business_and_records_direction(self):
        self.assertIs(policy.LyraControlPointFeedbackBlueprintFallbackProfile.Finished(self.actor,1),True);self.assertEqual(policy.evidence(self.actor)['finish_directions'],[1]);self.assertFalse(self.calls)
