"""Session-button visual policy; five-FText setter and native latent clock retained."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/Game/UI/Menu/Experiences/W_LyraSessionButton.W_LyraSessionButton_C'
METHODS=('image','reset','font_reset','pre','construct','hover','unhover','select','deselect','click','finished','disable','enable')
GATES={m:'UEPSessionButton'+''.join(v.title() for v in m.split('_')) for m in METHODS}
NATIVE_CLICK='UEPSessionButtonNativeClick'
SOUNDS={key:'/Game/Audio/Sounds/UI/sfx_UI_Lobby_'+value+'_nl_meta_Preset.sfx_UI_Lobby_'+value+'_nl_meta_Preset' for key,value in (('hover','Highlight'),('select','Select'))}

def evidence(w):
    if not hasattr(w,'_uep_session_button'):w._uep_session_button={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_session_button

def play(w,name,forward):w.call_function('PlayAnimationForward' if forward else 'PlayAnimationReverse',w.get_property(name),1.,False)
def sound(w,key):lib('GameplayStatics').call_function('PlaySound2D',w,ue.load_object(ue.find_class('SoundBase'),SOUNDS[key]),1.,1.,0.,None,None,True)
def zero(material):
    if valid(material):material.call_function('SetScalarParameterValue','Hover_Animate',0.);material.call_function('SetScalarParameterValue','Pressed_Animate',0.)

def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='image':
        material=w.get_property('ButtonBorder').call_function('GetDynamicMaterial')
        if valid(material):material.call_function('SetTextureParameterValue','MapTileArt',args[0])
    elif m=='reset':
        w.call_function('StopAnimation',w.get_property('OnPressed'));materials=[w.get_property('ButtonBorder').call_function('GetDynamicMaterial')]
        for name in ('GameModeText','PingText','PingLabel','MapLabel','PlayersText','MapNameText','MaxPlayersText'):
            material=w.get_property(name).call_function('GetDynamicFontMaterial')
            if name not in ('PingLabel','MapLabel'):materials.append(material)
        # Original Blueprint multi-self expansion applies all Hover writes,
        # followed by all Pressed writes. Two label getter results are unused.
        for parameter in ('Hover_Animate','Pressed_Animate'):
            for material in materials:
                if valid(material):material.call_function('SetScalarParameterValue',parameter,0.)
    elif m=='font_reset':zero(args[0].call_function('GetDynamicFontMaterial'))
    elif m in ('pre','construct'):w.call_function('ResetMaterials')
    elif m=='hover':
        if not w.get_property('IsDisabled'):play(w,'OnHovered',True);sound(w,'hover')
    elif m=='unhover':
        if not w.get_property('IsDisabled'):play(w,'OnHovered',False)
    elif m=='select':
        if not w.get_property('IsDisabled'):play(w,'OnPressed',True)
    elif m in ('deselect','finished'):
        if not w.get_property('IsDisabled'):play(w,'OnPressed',False)
    elif m=='click':
        if not w.get_property('IsDisabled'):w.call_function(NATIVE_CLICK)
    elif m in ('disable','enable'):
        disabled=m=='disable';w.set_property('IsDisabled',disabled);material=w.get_property('ButtonBorder').call_function('GetDynamicMaterial')
        if valid(material):material.call_function('SetScalarParameterValue','bIsDisabled',1. if disabled else 0.)
        if disabled:w.call_function('ResetMaterials')
    return False

def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return True
        return invoke(self,m,*args)
    apply.override=GATES[m];return apply

for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraSessionButton'+profile+'Profile']=type('LyraSessionButton'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
