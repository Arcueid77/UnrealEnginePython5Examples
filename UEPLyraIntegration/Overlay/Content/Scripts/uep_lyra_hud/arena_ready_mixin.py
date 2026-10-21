"""Original GetReady construction intent; animation clock and curves stay native."""
CLASS='/TopDownArena/GameplayCues/W_GetReady.W_GetReady_C'
CUE='/TopDownArena/GameplayCues/GCN_GetReady.GCN_GetReady_C'

def evidence(widget):
    value=getattr(widget,'_uep_arena_ready',None)
    if value is None:value=dict(python_constructs=0,fallback_constructs=0,plays=0);widget._uep_arena_ready=value
    return value

class LyraArenaReadyPythonProfile:
    def Construct(self):
        value=evidence(self);value['python_constructs']+=1;self.call_function('PlayAnimationForward',self.get_property('GetReady_Intro'),1.,False);value['plays']+=1

class LyraArenaReadyBlueprintFallbackProfile:
    def Construct(self):
        evidence(self)['fallback_constructs']+=1;self.call_mixin_original('Construct')
