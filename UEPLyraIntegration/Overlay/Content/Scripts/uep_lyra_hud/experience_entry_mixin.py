"""Experience assignment and activation; original FText/focus/delegate IO stays native."""
import unreal_engine as ue

CLASS='/Game/UI/Menu/Experiences/W_ExperienceTile.W_ExperienceTile_C'
METHODS=('set','click','focus')
GATES={m:'UEPExperienceEntry'+m.title() for m in METHODS}
NATIVE={m:'UEPExperienceEntryNative'+m.title() for m in ('appearance','notify','focus')}

def evidence(w):
    if not hasattr(w,'_uep_experience_entry'):w._uep_experience_entry={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_experience_entry

def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='set':w.set_property('MyUserFacingExperience',args[0]);w.call_function(NATIVE['appearance'])
    elif m=='click':w.call_function(NATIVE['notify'])
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
    globals()['LyraExperienceEntry'+profile+'Profile']=type('LyraExperienceEntry'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
