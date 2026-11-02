"""Device, replay, audio, damage, attribute and Pawn choices on native snapshots."""
from . import world_policies

OPERATIONS={
    'Device':frozenset(('Device.Connection','Device.Pairing','Device.Platform','Device.Schedule','Device.Process')),
    'Replay':frozenset(('Replay.Start','Replay.Select','Replay.Deleted')),
    'Audio':frozenset(('Audio.DynamicRange','Audio.Loading')),
    'Damage':frozenset(('Damage.CanCause',)),
    'Attribute':frozenset(('Attribute.Clamp',)),
    'Pawn':frozenset(('Pawn.Data','Pawn.Class','Pawn.Restart')),
}


def metrics(owner):
    if not hasattr(owner,'_uep_rule_policies'):owner._uep_rule_policies=dict(routes={},applied={},object_choices=0,trace=[])
    return owner._uep_rule_policies


def apply_rule(context):
    operation=str(context.Operation)
    if operation=='Device.Connection':context.set_property('bAct',int(context.OwnerUser)==int(context.ChangedUser))
    elif operation=='Device.Pairing':context.set_property('bAct',int(context.OwnerUser) in (int(context.NewUser),int(context.OldUser)))
    elif operation=='Device.Platform':context.set_property('bAct',bool(context.bPlatformTraits or context.bEditorTraits))
    elif operation=='Device.Schedule':context.set_property('bAct',not context.bPendingProcess)
    elif operation=='Device.Process':
        connected=any(row.bConnected and row.bGamepad for row in context.Devices)
        context.set_property('Action','Show' if not connected else 'Hide' if context.bScreenPresent else 'None')
    elif operation=='Replay.Start':context.set_property('bAct',bool(context.bHasLocalPlayer and not context.bBusy and int(context.NumberToKeep)>0))
    elif operation=='Replay.Deleted':context.set_property('bAct',bool(context.bDeleteSucceeded))
    elif operation=='Replay.Select':
        keep=int(context.NumberToKeep);rows=[row for row in context.Streams if not row.bShouldKeep]
        rows.sort(key=lambda row:(-int(row.TimestampTicks),int(row.Index)))
        if context.bRecording and rows and not rows[0].bIsLive:rows.insert(0,None)
        selected=rows[keep] if keep>0 and len(rows)>keep else None
        context.set_property('DeleteIndex',int(selected.Index) if selected is not None and not selected.bIsLive else -1)
    elif operation=='Audio.DynamicRange':
        apply,clear=(list(context.HDRSubmixes),list(context.LDRSubmixes)) if context.bHDR else (list(context.LDRSubmixes),list(context.HDRSubmixes))
        context.set_property('ApplyIndices',list(range(len(apply))))
        context.set_property('ClearIndices',[index for index,submix in enumerate(clear) if submix not in apply])
    elif operation=='Audio.Loading':context.set_property('bAct',bool(context.bAppliedLoading!=context.bWantsLoading and context.bHasMix and context.bHasWorld))
    elif operation=='Damage.CanCause':context.set_property('bAllowed',bool((context.bAllowSelf and (context.bSameObject or context.bSamePlayerState)) or context.bDifferentTeams or (context.bInvalidRelationship and context.bInstigatorHasTeam and context.bTargetHasASC)))
    elif operation=='Attribute.Clamp':
        name,value=str(context.Attribute),float(context.Input)
        if name=='BombsRemaining':low,high=0.,float(context.BombCapacity);value=low if value<low else value if value<high else high
        elif name in ('BombCapacity','BombRange'):value=value if value>=1. else 1.
        elif name=='MovementSpeed':value=200. if value<200. else value if value<800. else 800.
        context.set_property('Result',value)
    elif operation=='Pawn.Data':context.set_property('SelectedData',context.PlayerStateData if context.PlayerStateData is not None else (context.ExperienceData if context.ExperienceData is not None else context.AssetManagerData) if context.bExperienceLoaded else None)
    elif operation=='Pawn.Restart':context.set_property('bAllowed',bool(context.bBaseRestartAllowed and (not context.bHasSpawningManager or context.bManagerRestartAllowed)))
    else:raise AssertionError('Unknown native rule: '+operation)


def profile(name,enabled):
    enabled=frozenset(enabled);base=world_policies.CameraPython
    def uses(self,operation):
        operation=str(operation);family=operation.split('.',1)[0]
        if family not in OPERATIONS:return base.UEPUsesPythonPolicy(self,operation)
        if operation not in OPERATIONS[family]:return False
        m=metrics(self);m['routes'][operation]=m['routes'].get(operation,0)+1
        return family in enabled
    def apply(self,context):
        operation=str(context.Operation);family=operation.split('.',1)[0]
        if family not in OPERATIONS:return base.UEPApplyPolicy(self,context)
        assert family in enabled and operation in OPERATIONS[family],'disabled native rule dispatched'
        apply_rule(context);m=metrics(self);m['applied'][operation]=m['applied'].get(operation,0)+1
        detail=dict(operation=operation)
        if operation=='Audio.Loading':detail.update(before=bool(context.bAppliedLoading),wanted=bool(context.bWantsLoading),changed=bool(context.bAct),has_mix=bool(context.bHasMix),has_world=bool(context.bHasWorld))
        elif operation=='Replay.Select':detail.update(number_to_keep=int(context.NumberToKeep),streams=len(context.Streams),delete_index=int(context.DeleteIndex),recording=bool(context.bRecording))
        elif operation=='Damage.CanCause':detail.update(allowed=bool(context.bAllowed),different_teams=bool(context.bDifferentTeams),same_player_state=bool(context.bSamePlayerState))
        elif operation=='Attribute.Clamp':detail.update(attribute=str(context.Attribute),input=float(context.Input),result=float(context.Result))
        m['trace'].append(detail);del m['trace'][:-128];context.set_property('bCompleted',True)
    def choose(self,operation,primary,secondary):
        if str(operation)=='Pawn.Class':
            assert 'Pawn' in enabled,'disabled Pawn class choice dispatched'
            metrics(self)['object_choices']+=1;return primary if primary is not None else secondary
        return base.UEPChooseObject(self,operation,primary,secondary)
    uses.__name__='UEPUsesPythonPolicy';apply.__name__='UEPApplyPolicy';choose.__name__='UEPChooseObject'
    return type(name,(),dict(__module__=__name__,UEPUsesPythonPolicy=uses,UEPApplyPolicy=apply,UEPChooseObject=choose))


DeviceNative=profile('DeviceNative',())
DevicePython=profile('DevicePython',('Device',))
ReplayNative=profile('ReplayNative',('Device',))
ReplayPython=profile('ReplayPython',('Device','Replay'))
AudioNative=profile('AudioNative',('Device','Replay'))
AudioPython=profile('AudioPython',('Device','Replay','Audio'))
DamageNative=profile('DamageNative',('Device','Replay','Audio'))
DamagePython=profile('DamagePython',('Device','Replay','Audio','Damage'))
AttributeNative=profile('AttributeNative',('Device','Replay','Audio','Damage'))
AttributePython=profile('AttributePython',('Device','Replay','Audio','Damage','Attribute'))
PawnNative=profile('PawnNative',('Device','Replay','Audio','Damage','Attribute'))
PawnPython=profile('PawnPython',('Device','Replay','Audio','Damage','Attribute','Pawn'))
