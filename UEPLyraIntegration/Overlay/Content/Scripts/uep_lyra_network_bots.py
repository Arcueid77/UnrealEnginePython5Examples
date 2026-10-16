"""Test-only AI combat isolation; no Health, immunity or player-state writes."""


def isolate_bots(gameplay_statics, world, bot_class):
    # UEP represents out parameters as a tuple, even for a single out array.
    bots, = gameplay_statics.call_function('GetAllActorsOfClass', world, bot_class)
    result = []
    for controller in bots:
        brain = getattr(controller, 'BrainComponent', None)
        if brain is None or not brain.is_valid():
            continue
        if brain.call_function('IsRunning'):
            brain.call_function('StopLogic', 'UEP network Health isolation')
            controller.call_function('StopMovement')
        result.append({'controller': controller.get_path_name(), 'brain': brain.get_path_name(),
                       'running': bool(brain.call_function('IsRunning'))})
    return result
