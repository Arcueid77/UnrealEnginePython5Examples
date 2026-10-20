"""Performance/build/user display policies with opaque native FText rendering."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASSES={k:'/Game/'+v+'.'+v.rsplit('/',1)[-1]+'_C' for k,v in dict(graph='UI/PerfStats/W_SingleGraphStat',text='UI/PerfStats/W_SingleTextStat',build='UI/Menu/W_BuildConfiguration',watermark='UI/Menu/W_UserWatermark').items()}
METHODS=dict(graph=('pre','tick'),text=('pre','tick'),build=('construct',),watermark=('tick',))
GATES={k:{m:'UEPDiagnostic'+k.title()+m.title() for m in methods} for k,methods in METHODS.items()}
NATIVE_PRE='UEPDiagnosticNativePre'
NATIVE_VALUE='UEPDiagnosticNativeValue'
NATIVE_BUILD='UEPDiagnosticNativeBuild'
NATIVE_NAME='UEPDiagnosticNativeName'
NATIVE_USER='UEPDiagnosticNativeUser'
NATIVE_MISSING='UEPDiagnosticNativeMissing'

def evidence(w):
    if not hasattr(w,'_uep_diagnostic_widgets'):w._uep_diagnostic_widgets={p+'_'+k+'_'+m:0 for p in ('python','fallback') for k,methods in METHODS.items() for m in methods}
    return w._uep_diagnostic_widgets
def mark(w,k,m):evidence(w)['python_'+k+'_'+m]+=1
def display_player_number(n):return (int(n)+1+2**31)%2**32-2**31
def invoke(w,k,m):
    mark(w,k,m)
    if k in ('graph','text'):
        if m=='pre':
            w.call_function(NATIVE_PRE)
            if k=='text':w.get_property('StatValueSizer').call_function('SetWidthOverride',w.get_property('ValuePaddingWidth'))
        else:
            scale=w.get_property('ScaleFactor')
            if k=='graph':w.call_function('UpdateGraphData',scale)
            value=w.call_function('FetchStatValue');w.call_function(NATIVE_VALUE,float(scale)*float(value))
        return False
    if k=='build':
        system=lib('KismetSystemLibrary');version=system.call_function('GetBuildVersion');configuration=system.call_function('GetBuildConfiguration');w.call_function(NATIVE_BUILD,version,configuration);return False
    number=int(w.get_property('PlayerNumber'));display=display_player_number(number);controller=lib('GameplayStatics').call_function('GetPlayerController',w,number)
    if valid(controller):
        subsystem=lib('SubsystemBlueprintLibrary').call_function('GetGameInstanceSubsystem',w,ue.find_class('CommonUserSubsystem'));user=subsystem.call_function('GetUserInfoForLocalPlayerIndex',number)
        if valid(user):
            # ECommonUserOnlineContext::Game is the first enumerator (0).
            nickname=user.call_function('GetNickname',0);debug=user.call_function('GetDebugString');w.call_function(NATIVE_USER,nickname,debug,display);return False
    w.call_function(NATIVE_MISSING,display);return False
def method(k,m,fallback):
    def apply(self,*a):
        if fallback:evidence(self)['fallback_'+k+'_'+m]+=1;return True
        return invoke(self,k,m)
    apply.override=GATES[k][m];return apply
for label,methods in METHODS.items():
    for name,fallback_profile in (('Python',False),('BlueprintFallback',True)):
        clsname='LyraDiagnostic'+label.title()+name+'Profile';globals()[clsname]=type(clsname,(),{m:method(label,m,fallback_profile) for m in methods})
