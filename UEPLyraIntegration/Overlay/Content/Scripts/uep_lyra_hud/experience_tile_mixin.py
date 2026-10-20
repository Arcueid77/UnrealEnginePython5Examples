"""Experience tile policy; native opaque labels and latent click remain intact."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/Game/UI/Menu/W_LyraExperienceTileButton.W_LyraExperienceTileButton_C'
GAME_INSTANCE='/Game/B_LyraGameInstance.B_LyraGameInstance_C'
KEYS=('art','reset','progress','pre','construct','hover','unhover','click','clicksound','finished','select','deselect','disable','enable')
GATES={k:'UEPExperience'+k.title() for k in KEYS}
NATIVE_CLICK='UEPExperienceStartNativeClick'
SOUNDS={k:'/Game/Audio/Sounds/UI/sfx_UI_Lobby_'+n+'_nl_meta_Preset.sfx_UI_Lobby_'+n+'_nl_meta_Preset' for k,n in (('hover','Highlight'),('select','Select'))}

def evidence(w):
    if not hasattr(w,'_uep_experience_tile'):w._uep_experience_tile={p+'_'+k:0 for p in ('python','fallback') for k in KEYS}
    return w._uep_experience_tile
def mark(w,k):evidence(w)['python_'+k]+=1
def call(w,f,*a):return w.call_function(f,*a)
def prop(w,n):return w.get_property(n)
def materials(w):return (call(prop(w,'ButtonBorder'),'GetDynamicMaterial'),)+tuple(call(prop(w,n),'GetDynamicFontMaterial') for n in ('ExperienceTitle','MapTitle','ExperienceDescription'))
def scalar(values,n,v):
    for material in values:
        if valid(material):call(material,'SetScalarParameterValue',n,v)
def play(w,n,forward):call(w,'PlayAnimationForward' if forward else 'PlayAnimationReverse',prop(w,n),1.,False)
def sound(w,k):lib('GameplayStatics').call_function('PlaySound2D',w,ue.load_object(ue.find_class('SoundBase'),SOUNDS[k]),1.,1.,0.,None,None,True)
def art(w,texture):
    mark(w,'art');material=call(prop(w,'KeyArt'),'GetDynamicMaterial')
    if valid(material):call(material,'SetTextureParameterValue','TileArt',texture)
    return False
def reset(w):mark(w,'reset');call(w,'StopAnimation',prop(w,'OnPressed'));values=materials(w);scalar(values,'Hover_Animate',0.);scalar(values,'Pressed_Animate',0.);return False
def progress(w):mark(w,'progress');return dict(UseOriginal=False,Progress=float(prop(w,'PressProgress')))
def pre(w,design):mark(w,'pre');call(w,'ResetMaterials');return False
def construct(w):mark(w,'construct');call(w,'ResetMaterials');return False
def hover(w):
    mark(w,'hover')
    if not prop(w,'IsDisabled'):play(w,'OnHovered',True);sound(w,'hover')
    return False
def unhover(w):
    mark(w,'unhover')
    if not prop(w,'IsDisabled'):play(w,'OnHovered',False)
    return False
def select(w):
    mark(w,'select')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',True);sound(w,'select')
    return False
def deselect(w):
    mark(w,'deselect')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',False)
    return False
def disable(w):mark(w,'disable');w.set_property('IsDisabled',True);scalar((call(prop(w,'ButtonBorder'),'GetDynamicMaterial'),),'bIsDisabled',1.);call(w,'ResetMaterials');return False
def enable(w):mark(w,'enable');w.set_property('IsDisabled',False);scalar((call(prop(w,'ButtonBorder'),'GetDynamicMaterial'),),'bIsDisabled',0.);return False
def click(w):
    mark(w,'click')
    if not prop(w,'IsDisabled'):call(w,NATIVE_CLICK)
    return False
def clicksound(w):
    mark(w,'clicksound');statics=lib('GameplayStatics');statics.call_function('SpawnSound2D',w,ue.load_object(ue.find_class('SoundBase'),SOUNDS['select']),1.,1.,0.,None,True,True);instance=statics.call_function('GetGameInstance',w)
    # Original SpawnSound2D.ReturnValue is unwired. The following setter clears
    # Audio_LobbySelect instead of assigning the newly spawned component.
    if valid(instance) and instance.is_a(ue.load_class(GAME_INSTANCE)):instance.set_property('Audio_LobbySelect',None)
    return False
def finished(w):
    mark(w,'finished')
    if not prop(w,'IsDisabled'):play(w,'OnPressed',False)
    return False
def method(k,fn):
    def invoke(self,*args):return fn(self,*args)
    invoke.override=GATES[k];return invoke
class LyraExperienceTilePythonProfile:
    Art=method('art',art);Reset=method('reset',reset);Pre=method('pre',pre);Construct=method('construct',construct);Hover=method('hover',hover);Unhover=method('unhover',unhover);Select=method('select',select);Deselect=method('deselect',deselect);Disable=method('disable',disable);Enable=method('enable',enable);Click=method('click',click);ClickSound=method('clicksound',clicksound);Finished=method('finished',finished)
    def Progress(self):return progress(self)
    Progress.override=GATES['progress'];Progress.uep_named_outputs=True
def fallback(k):
    def invoke(self,*args):evidence(self)['fallback_'+k]+=1;return dict(UseOriginal=True,Progress=0.) if k=='progress' else True
    invoke.override=GATES[k]
    if k=='progress':invoke.uep_named_outputs=True
    return invoke
class LyraExperienceTileBlueprintFallbackProfile:
    Art=fallback('art');Reset=fallback('reset');Pre=fallback('pre');Construct=fallback('construct');Hover=fallback('hover');Unhover=fallback('unhover');Select=fallback('select');Deselect=fallback('deselect');Disable=fallback('disable');Enable=fallback('enable');Click=fallback('click');ClickSound=fallback('clicksound');Finished=fallback('finished');Progress=fallback('progress')
