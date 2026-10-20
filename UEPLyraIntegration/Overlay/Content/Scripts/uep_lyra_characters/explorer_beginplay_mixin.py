"""Explorer begins at Spawned, preserving its earlier native visibility boundary."""
from unreal_engine.structs import GameplayTag
from . import explorer_init_mixin as initialization,visibility_mixin as visibility,begin_play_mixin as beginning

REQUIRED_STATE='InitState.Spawned'
def begin(actor):
    counts=beginning.evidence(actor);counts['python_calls']+=1
    actor.call_function(beginning.PARENT);counts['parent_calls']+=1;counts['order'].append('parent')
    actor.call_function('ListenForTeam');counts['listen_calls']+=1;counts['order'].append('listen')
    actor.call_function('SetActorHiddenInGame',True);counts['hide_calls']+=1;counts['order'].append('hide')
    actor.call_function(visibility.REGISTER,actor.get_property('PawnExtComponent'),GameplayTag(TagName=REQUIRED_STATE),True);counts['register_calls']+=1;counts['order'].append('register')

for kind in initialization.CLASSES:
    for profile in ('Python','BlueprintFallback'):
        parent=vars(initialization)['LyraExplorerInit'+kind.title()+profile+'Profile'];methods={n:f for n,f in vars(parent).items() if not n.startswith('__')}
        methods.update(ReceiveBeginPlay=begin if profile=='Python' else beginning.LyraCharacterBeginPlayBlueprintFallbackProfile.ReceiveBeginPlay,ShowPawnAgainNextFrame=visibility.LyraCharacterVisibilityPythonProfile.ShowPawnAgainNextFrame if profile=='Python' else visibility.LyraCharacterVisibilityBlueprintFallbackProfile.ShowPawnAgainNextFrame,PythonVisibilityResume=vars(visibility.LyraCharacterVisibilityPythonProfile)['PythonVisibilityResume'])
        globals()['LyraExplorerBeginPlay'+kind.title()+profile+'Profile']=type('LyraExplorerBeginPlay'+kind.title()+profile+'Profile',(),methods)
