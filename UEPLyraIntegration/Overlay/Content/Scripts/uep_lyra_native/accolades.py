"""Accolade filter/order/cancellation policy; native registry/async/timers own IO."""
import unreal_engine as ue
from unreal_engine.structs import PendingAccoladeEntry
from uep_lyra_hud.accolade_widgets_mixin import LyraAccoladeHostPythonProfile as Presentation
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/ShooterCore/UserInterface/Notifications/Accolades/W_AccoladeHostWidget.W_AccoladeHostWidget_C'
LOADS='PendingAccoladeLoads';DISPLAYS='PendingAccoladeDisplays';NEXT='NextDisplaySequenceID';ALLOCATED='AllocatedSequenceID'


def metrics(widget):
    if not hasattr(widget,'_uep_native_accolades'):widget._uep_native_accolades={p+k:0 for p in ('python_','native_') for k in ('notify','row','consider','process','display','pop','clear')}
    return widget._uep_native_accolades


def entries(widget,field):return [e.clone() for e in widget.get_property(field)]


class AccoladePythonProfile(Presentation):
    Construct=Presentation.Construct
    Create=Presentation.Create
    Destroy=Presentation.Destroy

    def OnNotificationMessage(self,Channel,Notification):
        metrics(self)['python_notify']+=1
        if str(Notification.TargetChannel.TagName)!='Lyra.ShooterGame.Accolade':return
        if Notification.TargetPlayer is not None:
            controller=self.call_function('GetOwningPlayer')
            if not valid(controller) or controller.PlayerState!=Notification.TargetPlayer:return
        sequence=int(self.get_property(ALLOCATED));self.set_property(ALLOCATED,sequence+1)
        if not self.call_function('UEPRequestAccoladeRow',Notification.PayloadTag,sequence):self.set_property(ALLOCATED,int(self.get_property(ALLOCATED))-1)

    def UEPQueueAccoladeRow(self,Row,SequenceID):
        metrics(self)['python_row']+=1;loads=entries(self,LOADS);loads.append(PendingAccoladeEntry(Row=Row,SequenceID=int(SequenceID)))
        self.set_property(LOADS,loads);self.call_function('UEPStartAccoladeAssetLoad',int(SequenceID))

    def ConsiderLoadedAccolades(self):
        metrics(self)['python_consider']+=1
        while True:
            loads=entries(self,LOADS);desired=int(self.get_property(NEXT));index=next((i for i,e in enumerate(loads) if e.bFinishedLoading and int(e.SequenceID)==desired),None)
            if index is None:return
            entry=loads[index].clone();loads[index]=loads[-1];loads.pop();self.set_property(LOADS,loads)
            self.call_function('ProcessLoadedAccolade',entry);self.set_property(NEXT,int(self.get_property(NEXT))+1)

    def ProcessLoadedAccolade(self,Entry):
        metrics(self)['python_process']+=1
        if str(Entry.Row.LocationTag.TagName)!=str(self.get_property('LocationName').TagName):return
        recreate=not self.get_property(DISPLAYS);index=0;tags=ue.find_class('BlueprintGameplayTagLibrary').get_cdo()
        while index<len(self.get_property(DISPLAYS)):
            current=entries(self,DISPLAYS)[index]
            if tags.call_function('HasAnyTags',current.Row.AccoladeTags,Entry.Row.CancelAccoladesWithTag,False):
                if valid(current.AllocatedWidget):self.call_function('DestroyAccoladeWidget',current.AllocatedWidget);recreate=True
                displays=entries(self,DISPLAYS);displays.pop(index);self.set_property(DISPLAYS,displays)
            else:index+=1
        displays=entries(self,DISPLAYS);displays.append(Entry.clone());self.set_property(DISPLAYS,displays)
        if recreate:self.call_function('DisplayNextAccolade')

    def DisplayNextAccolade(self):
        metrics(self)['python_display']+=1;displays=entries(self,DISPLAYS)
        if displays:
            entry=displays[0];self.call_function('UEPScheduleAccoladePop',float(entry.Row.DisplayDuration));widget=self.call_function('CreateAccoladeWidget',entry)
            current=entries(self,DISPLAYS)
            if current and int(current[0].SequenceID)==int(entry.SequenceID):current[0].AllocatedWidget=widget;self.set_property(DISPLAYS,current)

    def PopDisplayedAccolade(self):
        metrics(self)['python_pop']+=1;displays=entries(self,DISPLAYS)
        if displays:
            if valid(displays[0].AllocatedWidget):self.call_function('DestroyAccoladeWidget',displays[0].AllocatedWidget)
            current=entries(self,DISPLAYS)
            if current:current.pop(0);self.set_property(DISPLAYS,current)
        self.call_function('DisplayNextAccolade')

    def UEPClearAccoladeState(self):
        metrics(self)['python_clear']+=1
        for entry in entries(self,DISPLAYS):
            if valid(entry.AllocatedWidget):self.call_function('DestroyAccoladeWidget',entry.AllocatedWidget)
        self.set_property(LOADS,[]);self.set_property(DISPLAYS,[]);self.set_property(NEXT,0);self.set_property(ALLOCATED,0)


class AccoladeNativeFallbackProfile(Presentation):
    Construct=Presentation.Construct
    Create=Presentation.Create
    Destroy=Presentation.Destroy
    def OnNotificationMessage(self,Channel,Notification):metrics(self)['native_notify']+=1;self.call_mixin_original('OnNotificationMessage',Channel,Notification)
    def UEPQueueAccoladeRow(self,Row,SequenceID):metrics(self)['native_row']+=1;self.call_mixin_original('UEPQueueAccoladeRow',Row,SequenceID)
    def ConsiderLoadedAccolades(self):metrics(self)['native_consider']+=1;self.call_mixin_original('ConsiderLoadedAccolades')
    def ProcessLoadedAccolade(self,Entry):metrics(self)['native_process']+=1;self.call_mixin_original('ProcessLoadedAccolade',Entry)
    def DisplayNextAccolade(self):metrics(self)['native_display']+=1;self.call_mixin_original('DisplayNextAccolade')
    def PopDisplayedAccolade(self):metrics(self)['native_pop']+=1;self.call_mixin_original('PopDisplayedAccolade')
    def UEPClearAccoladeState(self):metrics(self)['native_clear']+=1;self.call_mixin_original('UEPClearAccoladeState')
