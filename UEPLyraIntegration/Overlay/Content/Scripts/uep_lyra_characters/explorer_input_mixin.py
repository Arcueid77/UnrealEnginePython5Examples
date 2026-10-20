"""Per-Explorer native EnhancedInput symbols; Original retains fallback input frames."""
import unreal_engine as ue
from .explorer_helpers_mixin import CLASSES
from . import explorer_beginplay_mixin as beginning
from .enhanced_input_contract import ACTIONS
from .enhanced_input_mixin import dispatch

def bindings(cls):
    result={}
    for binding in ue.tobject_iterator(ue.find_class('EnhancedInputActionDelegateBinding')):
        if binding.get_outer()!=cls:continue
        for entry in binding.get_property('InputActionDelegateBindings'):
            asset=entry.InputAction.get_path_name()
            for key,(name,_,_,_) in ACTIONS.items():
                if asset=='/ShooterCore/Input/Actions/'+name+'.'+name:
                    if key in result or int(entry.TriggerEvent)!=1:raise RuntimeError('ambiguous/non-Triggered Explorer input binding: '+key)
                    result[key]=str(entry.FunctionNameToBind)
    if set(result)!=set(ACTIONS):raise RuntimeError('all five original Explorer EnhancedInput bindings required')
    return result

class InputReceiver:
    def __init__(self,kind,action,function):self.kind,self.action,self.function,self.__wrapped__=kind,action,function,function
    @property
    def override(self):
        cls=ue.find_class(CLASSES[self.kind])
        if cls is None:raise RuntimeError('original Explorer class must be loaded before input registration')
        return bindings(cls)[self.action]
    def __call__(self,*args,**kwargs):return self.function(*args,**kwargs)
    def __get__(self,instance,owner):return self.function.__get__(instance,owner)

def receiver(kind,action):
    def invoke(actor,ActionValue,ElapsedTime:float,TriggeredTime:float,SourceAction):dispatch(actor,action)
    return InputReceiver(kind,action,invoke)

for kind in CLASSES:
    for profile in ('Python','BlueprintFallback'):
        parent=vars(beginning)['LyraExplorerBeginPlay'+kind.title()+profile+'Profile'];methods={name:fn for name,fn in vars(parent).items() if not name.startswith('__')}
        if profile=='Python':
            for action in ACTIONS:methods['PythonExplorerInput'+action.replace('-','_').title()]=receiver(kind,action)
        globals()['LyraExplorerInput'+kind.title()+profile+'Profile']=type('LyraExplorerInput'+kind.title()+profile+'Profile',(),methods)
