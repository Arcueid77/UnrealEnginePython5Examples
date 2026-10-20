"""Original toast item/icon policy with native FText and TimerManager transport."""
import unreal_engine as ue
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/ShooterExplorer/UserInterface/W_ItemAcquiredToastRow.W_ItemAcquiredToastRow_C'
ENTRY='/ShooterExplorer/UserInterface/ItemAcquiredToastEntry.ItemAcquiredToastEntry_C'
WRITE='UEPExplorerToastWriteNativeText'
START='UEPExplorerToastBeginNativeTimer'

def evidence(w):
    if not hasattr(w,'_uep_explorer_toast'):w._uep_explorer_toast=dict(python_item=0,fallback_item=0,python_icon=0,fallback_icon=0,python_expired=0,fallback_expired=0,invalid_items=0,native_text_writes=0,native_timer_requests=0)
    return w._uep_explorer_toast
def item(w,obj):
    counts=evidence(w);counts['python_item']+=1
    if not valid(obj) or not obj.is_a(ue.load_class(ENTRY)):counts['invalid_items']+=1;return
    w.set_property('ItemPtr',obj);w.call_function('SetIcon',obj.get_property('IconToShow'));w.call_function(WRITE,obj);counts['native_text_writes']+=1;w.call_function(START,obj);counts['native_timer_requests']+=1
def icon(w,texture):
    evidence(w)['python_icon']+=1;image=w.get_property('ItemIconWidget');image.call_function('SetBrushFromTexture',texture,False);image.call_function('SetVisibility',0 if valid(texture) else 2)
def expired(w):evidence(w)['python_expired']+=1;w.broadcast('OnToastExpired',w.get_property('ItemPtr'))
class LyraExplorerToastPythonProfile:
    def OnListItemObjectSet(self,ListItemObject):item(self,ListItemObject)
    def SetIcon(self,Texture):icon(self,Texture)
    def OnTimerElapsed(self):expired(self)
class LyraExplorerToastBlueprintFallbackProfile:
    def OnListItemObjectSet(self,ListItemObject):evidence(self)['fallback_item']+=1;self.call_mixin_original('OnListItemObjectSet',ListItemObject)
    def SetIcon(self,Texture):evidence(self)['fallback_icon']+=1;self.call_mixin_original('SetIcon',Texture)
    def OnTimerElapsed(self):evidence(self)['fallback_expired']+=1;self.call_mixin_original('OnTimerElapsed')
