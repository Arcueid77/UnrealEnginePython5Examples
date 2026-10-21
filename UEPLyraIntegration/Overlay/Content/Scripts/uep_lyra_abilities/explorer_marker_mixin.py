"""Original marker HasActor decision; native instant targeting and debug draw."""
from uep_lyra_weapons.hero_burst_cue_mixin import lib
CLASS='/ShooterExplorer/Input/Abilities/GA_ToggleMarkerInWorld.GA_ToggleMarkerInWorld_C'
START='UEPExplorerMarkerBeginNativeTargetData'
DATA='UEPExplorerMarkerValidTargetData'
DRAW='UEPExplorerMarkerDrawNativeSphere'
def evidence(a):
    if not hasattr(a,'_uep_explorer_marker'):a._uep_explorer_marker={p+'_'+n:0 for p in ('python','fallback') for n in ('activate','data','draw')};a._uep_explorer_marker.update(last_data=None,last_center=None,native_end_requests=0,no_actor=0)
    return a._uep_explorer_marker
def activate(a):evidence(a)['python_activate']+=1;a.call_function(START)
def data(a,Data):
    values=evidence(a);values['python_data']+=1;values['last_data']=Data.clone()
    if not lib('AbilitySystemBlueprintLibrary').call_function('TargetDataHasActor',Data,0):values['no_actor']+=1;return False
    center=lib('AbilitySystemBlueprintLibrary').call_function('GetTargetDataEndPoint',Data,0);a.call_function(DRAW,center);a.call_function('K2_EndAbility');values['native_end_requests']+=1;return False
def draw(a,center,prefix):evidence(a)[prefix+'_draw']+=1;evidence(a)['last_center']=[float(center.x),float(center.y),float(center.z)];a.call_mixin_original(DRAW,center)
class LyraExplorerMarkerPythonProfile:
    def K2_ActivateAbility(self):activate(self)
    def ValidTargetData(self,Data):return data(self,Data)
    ValidTargetData.override=DATA
    def DrawNativeSphere(self,Center):draw(self,Center,'python')
    DrawNativeSphere.override=DRAW
class LyraExplorerMarkerBlueprintFallbackProfile:
    def K2_ActivateAbility(self):evidence(self)['fallback_activate']+=1;self.call_mixin_original('K2_ActivateAbility')
    def ValidTargetData(self,Data):evidence(self)['fallback_data']+=1;evidence(self)['last_data']=Data.clone();return True
    ValidTargetData.override=DATA
    def DrawNativeSphere(self,Center):draw(self,Center,'fallback')
    DrawNativeSphere.override=DRAW
