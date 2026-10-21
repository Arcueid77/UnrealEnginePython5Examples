"""Arena list callbacks and countdown decisions; native UMG/FText clocks remain."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid
LIST='/TopDownArena/UserInterface/W_TopDownPlayers.W_TopDownPlayers_C'
TIMER='/TopDownArena/UserInterface/W_RoundTimer.W_RoundTimer_C'
TILE='/TopDownArena/UserInterface/Player/W_PlayerTile.W_PlayerTile_C'
MODE='/TopDownArena/Game/Modes/B_TopDownArena_GameComponent_Base.B_TopDownArena_GameComponent_Base_C'
READY='OnReady_A6E13A06464ABBA60E698BB56C799828'
BIND='UEPBindArenaRoundExperience'
RENDER='UEPArenaRoundRenderTime'
def lib(name):return ue.find_class(name).get_cdo()
def one(value):return value[0] if isinstance(value,tuple) and len(value)==1 else value
def evidence(w):
    value=getattr(w,'_uep_arena_hud',None)
    if value is None:
        value={p+k:0 for p in ('python_','fallback_') for k in ('select','configure','construct','ready','tick')};value.update(configured_tiles=0,invalid_widgets=0,invalid_modes=0,factories=0,activations=0,renders=0);w._uep_arena_hud=value
    return value
class LyraArenaListPythonProfile:
    def OnGetWidgetClassForData_0(self,DataItem):evidence(self)['python_select']+=1;return ue.load_class(TILE)
    def OnConfigureWidgetForData_0(self,Widget,DataItem):
        value=evidence(self);value['python_configure']+=1
        if not valid(Widget) or not Widget.is_a(ue.load_class(TILE)):value['invalid_widgets']+=1;return
        state=DataItem if valid(DataItem) and DataItem.is_a(ue.find_class('LyraPlayerState')) else None
        Widget.call_function('Configure',state);value['configured_tiles']+=1
class LyraArenaListBlueprintFallbackProfile:
    def OnGetWidgetClassForData_0(self,DataItem):evidence(self)['fallback_select']+=1;return self.call_mixin_original('OnGetWidgetClassForData_0',DataItem)
    def OnConfigureWidgetForData_0(self,Widget,DataItem):evidence(self)['fallback_configure']+=1;self.call_mixin_original('OnConfigureWidgetForData_0',Widget,DataItem)
class LyraArenaRoundPythonProfile:
    def Construct(self):
        value=evidence(self);value['python_construct']+=1;action=lib('AsyncAction_ExperienceReady').call_function('WaitForExperienceReady',self)
        if not valid(action):return
        value['factories']+=1;self.call_function(BIND,action);action.call_function('Activate');value['activations']+=1
    def ExperienceReady(self):
        evidence(self)['python_ready']+=1;state=lib('GameplayStatics').call_function('GetGameState',self);self.set_property('TopDownArenaMode',state.call_function('GetComponentByClass',ue.load_class(MODE)))
    ExperienceReady.override=READY
    def Tick(self,MyGeometry,InDeltaTime):
        value=evidence(self);value['python_tick']+=1;mode=self.get_property('TopDownArenaMode')
        if not valid(mode):value['invalid_modes']+=1;return
        seconds=float(one(mode.call_function('GetRoundTimeRemaining')));minutes=lib('KismetMathLibrary').call_function('Divide_DoubleDouble',seconds,60.);remainder=lib('KismetMathLibrary').call_function('Percent_FloatFloat',seconds,60.);self.call_function(RENDER,minutes,remainder);value['renders']+=1
class LyraArenaRoundBlueprintFallbackProfile:
    def Construct(self):evidence(self)['fallback_construct']+=1;self.call_mixin_original('Construct')
    def ExperienceReady(self):evidence(self)['fallback_ready']+=1;self.call_mixin_original(READY)
    ExperienceReady.override=READY
    def Tick(self,MyGeometry,InDeltaTime):evidence(self)['fallback_tick']+=1;self.call_mixin_original('Tick',MyGeometry,InDeltaTime)
