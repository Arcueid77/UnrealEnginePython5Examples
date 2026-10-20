"""Pawn-specific construction and post-inventory behavior with latest Controller payload."""
from . import explorer_input_mixin as inputs,explorer_init_mixin as initialization,inventory_wait_mixin as waiting,inventory_ready_mixin as readiness

CONTROLLER='UEPExplorerPossessionController'
BEHAVIOR='UEPExplorerNativeBehaviorOperations'
BT_TEXT='UEPExplorerNativeBehaviorLabel'
ST_TEXT='UEPExplorerNativeStateLabel'
PARENT='UEPExplorerNativeParentConstruction'

def evidence(actor):
    if not hasattr(actor,'_uep_explorer_behavior'):actor._uep_explorer_behavior=dict(python_construction=0,fallback_construction=0,python_behavior=0,fallback_behavior=0,false_noops=0,native_behavior_operations=0,post_grant_behavior_forwards=0,last_controller=None,trace=[])
    return actor._uep_explorer_behavior
def construction(actor):
    counts=evidence(actor);counts['python_construction']+=1;choice=bool(actor.get_property('UseBhvTree'));actor.call_function(BT_TEXT if choice else ST_TEXT);counts['trace'].append('behavior-label' if choice else 'state-label');actor.call_function(PARENT);counts['trace'].append('parent')
def construction_fallback(actor):evidence(actor)['fallback_construction']+=1;actor.call_mixin_original('UserConstructionScript')
def behavior(actor,Controller):
    counts=evidence(actor);counts['python_behavior']+=1;counts['last_controller']=Controller.get_path_name() if Controller is not None else None
    if not actor.get_property('UseBhvTree'):counts['false_noops']+=1;return
    actor.call_function(BEHAVIOR,Controller);counts['native_behavior_operations']+=1
def behavior_fallback(actor,Controller):evidence(actor)['fallback_behavior']+=1;actor.call_mixin_original('UseBehaviorTree',Controller)
def possessed(actor,NewController):
    actor.set_property(CONTROLLER,NewController);initialization.possessed(actor,NewController)
def advance(actor,stage):
    for index in range(stage,3):
        controller=actor.call_function('GetController');value=controller if index==0 or not initialization.valid(controller) else controller.call_function('GetComponentByClass',initialization.ue.find_class(waiting.CLASSES[index]))
        if not initialization.valid(value):waiting.defer(actor,index);return waiting.REASONS[index]
    actor.call_function('AddInitialInventory');waiting.evidence(actor)['grant_forwards']+=1;waiting.trace(actor,'grant',stage);actor.call_function('UseBehaviorTree',actor.get_property(CONTROLLER));evidence(actor)['post_grant_behavior_forwards']+=1;return None
def ready(actor):
    counts=readiness.evidence(actor);counts['python_calls']+=1;reason=advance(actor,0)
    if reason is None:counts['immediate_grants']+=1
    else:counts[reason]+=1
def resume(actor,Linkage:int):
    if Linkage not in (0,1,2):raise ValueError('invalid native Explorer behavior readiness linkage')
    values=waiting.evidence(actor);values['pending'][Linkage]=False;values['resumes']+=1;values['stage_resumes'][Linkage]+=1;waiting.trace(actor,'resume',Linkage);advance(actor,Linkage)
resume.override=waiting.RESUME

for kind in inputs.CLASSES:
    for profile in ('Python','BlueprintFallback'):
        parent=vars(inputs)['LyraExplorerInput'+kind.title()+profile+'Profile'];methods={name:fn for name,fn in vars(parent).items() if not name.startswith('__')}
        if kind=='pawn':
            methods.update(UserConstructionScript=construction if profile=='Python' else construction_fallback,UseBehaviorTree=behavior if profile=='Python' else behavior_fallback)
            if profile=='Python':methods.update(ReceivePossessed=possessed,PythonExperienceReady=initialization.OriginalCallback(kind,'experience',ready),PythonInventoryWaitResume=resume)
        globals()['LyraExplorerBehavior'+kind.title()+profile+'Profile']=type('LyraExplorerBehavior'+kind.title()+profile+'Profile',(),methods)
