import importlib.util,sys,types,unittest
from pathlib import Path
from unittest.mock import patch

def load():
    unreal=types.ModuleType('unreal_engine');unreal.FLinearColor=lambda *v:v;structs=types.ModuleType('unreal_engine.structs');structs.SlateColor=lambda **kw:types.SimpleNamespace(**kw);valid=types.ModuleType('uep_lyra_world.effect_pad_mixin');valid.valid=lambda obj:obj is not None
    spec=importlib.util.spec_from_file_location('arena_tile_test',Path(__file__).resolve().parents[1]/'Overlay/Content/Scripts/uep_lyra_hud/arena_player_tile_mixin.py');policy=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{'unreal_engine':unreal,'unreal_engine.structs':structs,'uep_lyra_world.effect_pad_mixin':valid}):spec.loader.exec_module(policy)
    return policy

class ArenaPlayerTilePolicyTests(unittest.TestCase):
    def test_configure_preserves_name_monitor_and_three_stat_order(self):
        p=load();events=[];ps=types.SimpleNamespace(call_function=lambda name:'Player-甲');p.lib=lambda name:types.SimpleNamespace(call_function=lambda name,value:value);label=types.SimpleNamespace(call_function=lambda *a:events.append(('name',)+a));w=types.SimpleNamespace(get_property=lambda n:label,call_function=lambda *a:events.append(a));p.LyraArenaPlayerTilePythonProfile.Configure(w,ps)
        self.assertEqual(events,[('name','SetText','Player-甲'),(p.MONITOR,ps),('UEPArenaTileConfigureBomb',ps),('UEPArenaTileConfigureRange',ps),('UEPArenaTileConfigureSpeed',ps)])
    def test_monitor_cancels_binds_activates_then_stores_native_proxy(self):
        p=load();events=[];old=types.SimpleNamespace(call_function=lambda name:events.append('old-'+name));new=types.SimpleNamespace(call_function=lambda name:events.append('new-'+name));p.lib=lambda name:types.SimpleNamespace(call_function=lambda *a:(events.append('factory'),new)[1]);w=types.SimpleNamespace(get_property=lambda name:old,call_function=lambda *a:events.append(a[0]),set_property=lambda *a:events.append('store'));p.LyraArenaPlayerTilePythonProfile.MonitorTeamChange(w,object());self.assertEqual(events,['old-Cancel','factory',p.BIND,'new-Activate','store'])
    def test_null_factory_leaves_cancelled_original_handle_as_source(self):
        p=load();calls=[];old=types.SimpleNamespace(call_function=lambda n:calls.append(n));p.lib=lambda name:types.SimpleNamespace(call_function=lambda *a:None);w=types.SimpleNamespace(get_property=lambda n:old,set_property=lambda *a:calls.append('store'));p.LyraArenaPlayerTilePythonProfile.MonitorTeamChange(w,None);self.assertEqual(calls,['Cancel'])
    def test_actual_team_colors_and_unset_noop(self):
        p=load();calls=[];image=types.SimpleNamespace(call_function=lambda name,color:calls.append(color.SpecifiedColor));w=types.SimpleNamespace(get_property=lambda n:image)
        p.LyraArenaPlayerTilePythonProfile.ObservedTeam(w,False,-1);self.assertEqual(calls,[])
        for team in (1,2,3,4):p.LyraArenaPlayerTilePythonProfile.ObservedTeam(w,True,team)
        self.assertEqual(calls,[p.COLORS[i] for i in (1,2,3,4)])
    def test_fallback_aliases_forward_original_signatures(self):
        p=load();calls=[];ps=object();w=types.SimpleNamespace(call_mixin_original=lambda *a:calls.append(a));p.LyraArenaPlayerTileBlueprintFallbackProfile.Configure(w,ps);p.LyraArenaPlayerTileBlueprintFallbackProfile.MonitorTeamChange(w,ps);p.LyraArenaPlayerTileBlueprintFallbackProfile.ObservedTeam(w,True,3);self.assertEqual(calls,[('Configure',ps),(p.MONITOR,ps),(p.BOUND,True,3)]);self.assertEqual(p.LyraArenaPlayerTilePythonProfile.ObservedTeam.override,p.BOUND)
