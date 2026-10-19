"""Result fields, source style resets and one-shot countdown decisions."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

native=types.ModuleType('unreal_engine');structs=types.ModuleType('unreal_engine.structs')
structs.SlateBrush=lambda **kwargs:types.SimpleNamespace(**kwargs)
root=Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud'
spec=importlib.util.spec_from_file_location('_match_message_policy',root/'match_message_mixin.py');match=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'unreal_engine':native,'unreal_engine.structs':structs}):spec.loader.exec_module(match)
spec=importlib.util.spec_from_file_location('uep_lyra_hud._waiting_policy_test',root/'waiting_message_mixin.py');waiting=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'uep_lyra_hud.match_message_mixin':match}):spec.loader.exec_module(waiting)


class MessagePolicyTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.index=1;self.found=True
        font=types.SimpleNamespace(FontObject='font',FontMaterial='old',OutlineSettings='outline',TypefaceFontName='face',Size=37.5,LetterSpacing=17)
        self.text=types.SimpleNamespace(get_property=lambda name:font,call_function=lambda *a:self.calls.append(('text',*a)))
        brush=types.SimpleNamespace(TintColor='tint',DrawAs='draw',Tiling='tile',Mirroring='mirror',ImageSize='size',Margin='margin',OutlineSettings='outline')
        self.data={'Team':1,'VictoryMessage':self.text,'VictoryIntro':'victory','DefeatIntro':'defeat','CountDown':'countdown','CountdownStarted':False}
        for field,_,_ in match.IMAGES:self.data[field]=types.SimpleNamespace(get_property=lambda name:brush,call_function=lambda *a,f=field:self.calls.append((f,*a)))
        self.widget=types.SimpleNamespace(get_property=self.data.get,set_property=self.write,call_function=self.widget_call,call_mixin_original=lambda *a:self.calls.append(('original',*a)))
        native.find_class=lambda cls:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda name,*a,**kw:self.backend(name,a,kw)))
        native.load_object=lambda cls,path:path;native.load_class=lambda cls:types.SimpleNamespace(get_cdo=lambda:types.SimpleNamespace(call_function=lambda *a:self.calls.append(('static',*a))))
    def write(self,key,value):self.data[key]=value;self.calls.append(('write',key,value))
    def widget_call(self,*args):
        self.calls.append(('widget',*args))
        if args[0]=='GetOwningPlayer':return 'controller'
    def backend(self,name,args,kwargs):
        self.calls.append(('native',name,args,kwargs))
        if name=='MakeSlateFontInfo':return types.SimpleNamespace(**kwargs)
        if name=='GetWorldSubsystem':return types.SimpleNamespace(call_function=lambda *a:(self.found,self.index))
    def params(self,ability,raw):return types.SimpleNamespace(AbilityLevel=ability,RawMagnitude=raw)
    def test_neutral_team_clears_font_and_brush_materials(self):
        self.data['Team']=0;match.materials(self.widget)
        self.assertIs(next(c[2].FontMaterial for c in self.calls if c[:2]==('text','SetFont')),None)
        self.assertTrue(all(c[2].ResourceObject is None for c in self.calls if len(c)>1 and c[1]=='SetBrush'))
    def test_style_reuses_designer_layout_tint_and_outline(self):
        match.materials(self.widget);brush=next(c[2] for c in self.calls if c[:2]==('TextShadow','SetBrush'))
        self.assertEqual((brush.TintColor,brush.DrawAs,brush.Tiling,brush.Mirroring,brush.ImageSize,brush.Margin,brush.OutlineSettings),('tint','draw','tile','mirror','size','margin','outline'))
    def test_font_preserves_source_fields_and_resets_new_fields(self):
        match.materials(self.widget);kw=next(c[3] for c in self.calls if c[:2]==('native','MakeSlateFontInfo'))
        self.assertEqual((kw['Size'],kw['LetterSpacing'],kw['SkewAmount'],kw['bForceMonospaced'],kw['bMaterialIsStencil'],kw['MonospacedWidth']),(37.5,17,0.,False,False,1.))
    def test_material_resources_match_both_team_indices(self):
        for team,color in ((1,'Red'),(2,'Blue')):
            self.data['Team']=team;self.calls=[];match.materials(self.widget)
            font=next(c[2] for c in self.calls if c[:2]==('text','SetFont'));self.assertIn('Text_'+color,font.FontMaterial)
    def test_invalid_material_index_keeps_original_diagnostics(self):
        self.data['Team']=-1;match.materials(self.widget);self.assertEqual(self.calls,[('original','SetTeamMaterials')])
    def test_source_font_then_five_brush_write_order(self):
        match.materials(self.widget);self.assertEqual([c[0] for c in self.calls if len(c)>1 and c[1] in ('SetFont','SetBrush')],['text',* [r[0] for r in match.IMAGES]])
    def test_ability_zero_draw_ignores_conflicting_raw_magnitude(self):
        match.construct(self.widget,self.params(0,1.));self.assertIn(('widget',match.TEXT_ENTRIES[0]),self.calls)
    def test_victory_uses_ability_level_even_when_raw_is_negative(self):
        match.construct(self.widget,self.params(1,-55.));self.assertIn(('widget',match.TEXT_ENTRIES[1]),self.calls)
    def test_defeat_does_not_use_raw_magnitude_equal_to_local_team(self):
        match.construct(self.widget,self.params(2,1.));self.assertIn(('widget',match.TEXT_ENTRIES[2]),self.calls)
        self.assertFalse(any(c[0]=='static' for c in self.calls))
    def test_match_stores_team_even_if_native_membership_bool_is_false(self):
        self.found=False;self.index=-1;match.construct(self.widget,self.params(0,0.));self.assertEqual(self.data['Team'],-1)
    def test_draw_and_victory_forward_positive_stinger(self):
        for ability in (0,1):
            self.calls=[];match.construct(self.widget,self.params(ability,100.));self.assertIn(('static','FireStinger',True,self.widget),self.calls)
    def test_sound_dispatch_keeps_original_ui_defaults(self):
        match.construct(self.widget,self.params(2,0.));kw=next(c[3] for c in self.calls if c[:2]==('native','PlaySound2D'))
        self.assertIn('Defeat_01',kw['Sound']);self.assertEqual((kw['VolumeMultiplier'],kw['PitchMultiplier'],kw['StartTime'],kw['ConcurrencySettings'],kw['OwningActor'],kw['bIsUISound']),(1.,1.,0.,None,None,True))
    def test_literal_gate_stops_native_fallthrough_only_for_python(self):
        self.assertIs(match.LyraMatchMessagePythonProfile.AfterText(self.widget,0),False)
        self.assertIs(match.LyraMatchMessageBlueprintFallbackProfile.AfterText(self.widget,0),True)
    def test_waiting_no_team_selects_neutral_even_with_nonzero_id(self):
        self.found=False;self.index=2;waiting.initialize(self.widget);self.assertIn(('widget',waiting.TEXT,0),self.calls)
    def test_waiting_member_selects_team_and_starts_original_listener(self):
        waiting.initialize(self.widget);self.assertEqual([c for c in self.calls if c[0]=='widget'],[('widget','GetOwningPlayer'),('widget',waiting.TEXT,1),('widget',waiting.LISTEN)])
    def test_waiting_initialization_preserves_existing_countdown_latch(self):
        self.data['CountdownStarted']=True;waiting.initialize(self.widget);self.assertTrue(self.data['CountdownStarted']);self.assertFalse(any(c[:2]==('write','CountdownStarted') for c in self.calls))
    def test_countdown_sets_latch_before_native_animation(self):
        waiting.countdown(self.widget);self.assertEqual(self.calls,[('write','CountdownStarted',True),('widget','PlayAnimationForward','countdown',1.,False)])
    def test_repeated_countdown_message_cannot_restart_animation(self):
        waiting.countdown(self.widget);waiting.countdown(self.widget);self.assertEqual(waiting.evidence(self.widget)['countdown_starts'],1);self.assertEqual(waiting.evidence(self.widget)['ignored_started'],1)
    def test_fallback_preserves_native_initialization_and_callback(self):
        waiting.LyraWaitingMessageBlueprintFallbackProfile.OnInitialized(self.widget);self.assertEqual(self.calls,[('original','OnInitialized')]);self.assertIs(waiting.LyraWaitingMessageBlueprintFallbackProfile.CountdownMessage(self.widget),True)
