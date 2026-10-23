"""Observe current Cue profiles while preserving each exact selected handler."""

def around(original,record):
    def OnBurst(actor,Target,Parameters,SpawnResults):
        record(Target,Parameters)
        return original(actor,Target,Parameters,SpawnResults)
    if hasattr(original,'override'):OnBurst.override=original.override
    return OnBurst

class ExistingCueObservation:
    def __init__(self,api,cls,binding,record):
        self.api,self.cls=api,cls
        self.originals={name:row['python_class'] for name,row in binding['profiles'].items()}
        for name,base in self.originals.items():
            values={key:value for key,value in vars(base).items() if callable(value)}
            if 'OnBurst' not in values:raise ValueError('current Cue profile must expose its OnBurst handler')
            values['OnBurst']=around(values['OnBurst'],record)
            api.register_mixin_profile(cls,name,type('ObservedCurrentMeleeCue'+name,(),values))
    def restore(self):
        for name,base in self.originals.items():self.api.register_mixin_profile(self.cls,name,base)
        binding,=[b for b in self.api.get_registered_mixins() if b['target_class']==self.cls]
        return set(binding['profiles'])==set(self.originals) and all(binding['profiles'][name]['python_class'] is base for name,base in self.originals.items())
