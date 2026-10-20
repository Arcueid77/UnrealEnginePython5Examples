"""Original Explorer inventory/map deactivation removes this widget from its layer."""
from uep_lyra_weapons.hero_burst_cue_mixin import lib

CLASSES={key:'/ShooterExplorer/UserInterface/'+name+'.'+name+'_C' for key,name in (('inventory','W_InventoryScreen'),('map','W_MapScreen'))}

def evidence(widget):
    if not hasattr(widget,'_uep_explorer_screen'):widget._uep_explorer_screen=dict(python=0,fallback=0)
    return widget._uep_explorer_screen

class LyraExplorerScreenPythonProfile:
    def BP_OnDeactivated(self):
        evidence(self)['python']+=1;lib('CommonUIExtensions').call_function('PopContentFromLayer',self)

class LyraExplorerScreenBlueprintFallbackProfile:
    def BP_OnDeactivated(self):
        evidence(self)['fallback']+=1;self.call_mixin_original('BP_OnDeactivated')
