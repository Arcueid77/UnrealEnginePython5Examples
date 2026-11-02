"""Frontend decisions, cosmetic selection and camera priority on a BP carrier."""
from . import global_policy


def metrics(owner):
    if not hasattr(owner,'_uep_world_policies'):
        owner._uep_world_policies=dict(routes={},applied={},camera_choices=0,trace=[])
    return owner._uep_world_policies


def frontend_actions(context):
    operation=str(context.Operation)
    if operation=='Frontend.Plan':return ['Initialize','PressStart','JoinRequested','Main']
    if operation=='Frontend.Initialize':return (['ResetUsers'] if context.bHardDisconnect and context.bHasUser else [])+(['CleanSessions'] if context.bHasSession else [])+['Continue']
    if operation=='Frontend.PressStart':return ['Continue'] if context.bLoggedIn else ['AutoLogin'] if not context.bWaitForStart else ['PushStart'] if context.bHasRootLayout else []
    if operation=='Frontend.UserInitialized':return ['Continue']
    if operation=='Frontend.JoinRequested':return ['Join'] if context.bRequestedSession and context.bCanJoin else ['Continue']
    if operation=='Frontend.JoinResult':return ['Cancel'] if context.bSuccess else ['Continue']
    if operation=='Frontend.Main':return ['PushMain'] if context.bHasRootLayout else []
    if operation=='Frontend.StartWidget':return ['ClearLoading','WaitForDeactivate'] if context.bWidgetReady else ['ClearLoading','Continue'] if context.bWidgetCanceled else []
    if operation=='Frontend.MainWidget':return ['ClearLoading','Continue'] if context.bWidgetReady or context.bWidgetCanceled else []
    raise AssertionError('Unknown frontend operation: '+operation)


def part_indices(context):
    operation=str(context.Operation);rows=list(context.Entries)
    if operation=='Parts.Remove':return [int(row.Index) for row in rows if row.bEquivalent][:1]
    if operation=='Parts.Suppress':return [int(row.Index) for row in rows if int(row.Source)==(0 if context.bSuppressed else 1)]
    if not context.bHasCustomizer:return []
    if operation=='Parts.Add':return [int(rows[-1].Index)] if rows and int(rows[-1].Source)!=1 else []
    if operation in ('Parts.Detach','Parts.RemoveAll'):return [int(row.Index) for row in rows]
    if operation=='Parts.Attach':return [int(row.Index) for row in rows if not row.bHandleValid and int(row.Source)!=1]
    raise AssertionError('Unknown character-part operation: '+operation)


def profile(name,enabled):
    enabled=frozenset(enabled)
    def uses(self,operation):
        operation=str(operation)
        if operation.startswith('Reset.'):return global_policy.GameplayPolicyPython.UEPUsesPythonPolicy(self,operation)
        m=metrics(self);m['routes'][operation]=m['routes'].get(operation,0)+1
        return operation.split('.',1)[0] in enabled
    def apply(self,context):
        operation=str(context.Operation)
        if operation.startswith('Reset.'):return global_policy.GameplayPolicyPython.UEPApplyPolicy(self,context)
        assert operation.split('.',1)[0] in enabled,'disabled world policy dispatched'
        if operation.startswith('Frontend.'):context.set_property('Actions',frontend_actions(context))
        elif operation.startswith('Parts.'):context.set_property('Indices',part_indices(context))
        else:raise AssertionError('Unknown typed world operation: '+operation)
        m=metrics(self);m['applied'][operation]=m['applied'].get(operation,0)+1
        m['trace'].append(dict(operation=operation));del m['trace'][:-128]
        context.set_property('bCompleted',True)
    def choose(self,operation,primary,secondary):
        assert str(operation)=='Camera.Determine' and 'Camera' in enabled,'disabled camera selection dispatched'
        metrics(self)['camera_choices']+=1
        return primary if primary is not None else secondary
    uses.__name__='UEPUsesPythonPolicy'
    apply.__name__='UEPApplyPolicy'
    choose.__name__='UEPChooseObject'
    return type(name,(),dict(__module__=__name__,UEPUsesPythonPolicy=uses,UEPApplyPolicy=apply,UEPChooseObject=choose))


FrontendNative=profile('FrontendNative',())
FrontendPython=profile('FrontendPython',('Frontend',))
PartsNative=profile('PartsNative',('Frontend',))
PartsPython=profile('PartsPython',('Frontend','Parts'))
CameraNative=profile('CameraNative',('Frontend','Parts'))
CameraPython=profile('CameraPython',('Frontend','Parts','Camera'))
