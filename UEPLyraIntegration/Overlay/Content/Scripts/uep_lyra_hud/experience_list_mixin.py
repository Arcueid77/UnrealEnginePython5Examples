"""Experience-list selection/filter policy, opaque native focus/delegate IO."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid

CLASS='/Game/UI/Menu/Experiences/W_ExperienceList.W_ExperienceList_C'
TILE='/Game/UI/Menu/Experiences/W_ExperienceTile.W_ExperienceTile_C'
METHODS=('construct','loaded','click','first','random','focus')
GATES={m:'UEPExperienceList'+m.title() for m in METHODS}
NATIVE={m:'UEPExperienceListNative'+m.title() for m in ('load','bind','notify','complete','select','focus')}

def evidence(w):
    if not hasattr(w,'_uep_experience_list'):w._uep_experience_list={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_experience_list

def filter_experiences(loaded,show_all,cls):
    result=[]
    for exp in loaded:
        if valid(exp) and exp.is_a(cls) and exp.get_property('bShowInFrontEnd'):
            if exp.get_property('bIsDefaultExperience'):result.insert(0,exp)
            elif show_all:result.append(exp)
    return result

def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='construct':w.get_property('ExperienceRowBox').call_function('ClearChildren');w.set_property('UserFacingExperienceList',[]);w.call_function(NATIVE['load'])
    elif m=='loaded':
        experiences=filter_experiences(args[0],bool(w.get_property('ShowAllExperiences')),ue.find_class('LyraUserFacingExperienceDefinition'));w.set_property('UserFacingExperienceList',experiences)
        for exp in experiences:
            tile=lib('WidgetBlueprintLibrary').call_function('Create',w,ue.load_class(TILE),w.call_function('GetOwningPlayer'));tile.call_function('Set User Facing Experience',exp);widgets=list(w.get_property('ExperienceWidgets'));widgets.append(tile);w.set_property('ExperienceWidgets',widgets);w.call_function(NATIVE['bind'],tile);row=w.get_property('ExperienceRowBox');row.call_function('AddChildToHorizontalBox',tile)
            if int(row.call_function('GetChildrenCount'))==1:tile.call_function('SetUserFocus',w.call_function('GetOwningPlayer'))
        w.call_function(NATIVE['complete'])
    elif m=='click':w.call_function(NATIVE['notify'],args[0])
    elif m in ('first','random'):
        index=0 if m=='first' else int(lib('KismetMathLibrary').call_function('RandomInteger',len(w.get_property('ExperienceWidgets'))));w.call_function(NATIVE['select'],index)
    elif m=='focus':return dict(UseOriginal=False,ReturnValue=w.call_function(NATIVE['focus']))
    return False

def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return dict(UseOriginal=True,ReturnValue=ue.find_struct('EventReply')()) if m=='focus' else True
        return invoke(self,m,*args)
    apply.override=GATES[m]
    if m=='focus':apply.uep_named_outputs=True
    return apply

for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraExperienceList'+profile+'Profile']=type('LyraExperienceList'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
