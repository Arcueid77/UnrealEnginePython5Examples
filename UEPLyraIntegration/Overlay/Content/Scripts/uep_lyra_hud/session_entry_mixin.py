"""Session row policy with native FText formatting and original async join IO."""
import unreal_engine as ue
from uep_lyra_weapons.hero_burst_cue_mixin import lib
from uep_lyra_world.effect_pad_mixin import valid
CLASS='/Game/UI/Menu/Experiences/W_SessionBrowserEntry.W_SessionBrowserEntry_C'
METHODS=('item','display_ready','image','click','join','spinner','prepared','completed')
GATES={m:'UEPSessionEntry'+''.join(v.title() for v in m.split('_')) for m in METHODS}
NATIVE={m:'UEPSessionEntryNative'+''.join(v.title() for v in m.split('_')) for m in ('display_load','texts','spinner','prepare_load','submit','failure')}
def evidence(w):
    if not hasattr(w,'_uep_session_entry'):w._uep_session_entry={p+'_'+m:0 for p in ('python','fallback') for m in METHODS}
    return w._uep_session_entry
def invoke(w,m,*args):
    evidence(w)['python_'+m]+=1
    if m=='item':
        item=args[0]
        if valid(item) and item.is_a(ue.find_class('CommonSession_SearchResult')):w.set_property('SessionEntry',item);w.call_function(NATIVE['display_load'])
    elif m=='display_ready':w.call_function(NATIVE['texts'])
    elif m=='image':w.get_property('SessionButton').call_function('SetMapImage',args[0].get_property('TileIcon'))
    elif m=='click':w.call_function('JoinSession')
    elif m=='join':w.call_function(NATIVE['spinner'])
    elif m=='spinner':w.set_property('JoiningProgressWidget',args[0]);w.call_function(NATIVE['prepare_load'])
    elif m=='prepared':w.call_function(NATIVE['submit'])
    elif m=='completed':
        if not bool(args[0]):w.call_function(NATIVE['failure'])
    return False
def method(m,fallback):
    def apply(self,*args):
        if fallback:evidence(self)['fallback_'+m]+=1;return True
        return invoke(self,m,*args)
    apply.override=GATES[m];return apply
for profile,fallback in (('Python',False),('BlueprintFallback',True)):
    globals()['LyraSessionEntry'+profile+'Profile']=type('LyraSessionEntry'+profile+'Profile',(),{m:method(m,fallback) for m in METHODS})
