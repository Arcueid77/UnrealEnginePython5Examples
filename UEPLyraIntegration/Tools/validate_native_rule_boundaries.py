"""Exercise rule-context ABI, readonly snapshots, identity and numeric writeback."""
import itertools
import json
from pathlib import Path
import sys
import traceback

COUNTS=dict(Device=56,Replay=132,Audio=52,Damage=256,Attribute=48,Pawn=56)


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def require(value,message):
    if not value:raise AssertionError(message)
def gate(report):
    require(report['status']=='passed' and report['error'] is None and report['counts']==COUNTS and report['roots_restored'],'native rule context matrix incomplete')
    require(report['trace_bounded'] and report['int64_exact'] and report['unknown_operation_uses_native'],'native rule diagnostics/64-bit/fallback proof missing')
    return dict(status='passed',typed_context_cases=sum(COUNTS.values()),families=COUNTS,physical_input_tested=False,online_service_tested=False)


def run():
    import unreal_engine as ue
    from unreal_engine.structs import UEPNativeInputDeviceRow,UEPNativeReplayPolicyRow
    from uep_lyra_native import global_policy,rule_policies
    world=ue.get_editor_world();cls=ue.load_class(global_policy.CLASS);ue.register_declared_mixin(cls);host=ue.new_object(cls,world);roots=[]
    for value in (cls,host):
        if not value.is_rooted():value.add_to_root();roots.append(value)
    result=dict(status='passed',error=None,counts={key:0 for key in COUNTS},int64_exact=True)
    objects=[ue.new_object(ue.find_class('UEPNativePolicyContext'),host) for _ in range(3)];a,b,c=objects
    cases={key:[] for key in COUNTS}
    def add(family,operation,fields,outputs):cases[family].append((operation,fields,outputs))
    for owner,changed in ((0,0),(0,1),(1,0),(-1,-1)):add('Device','Connection',dict(OwnerUser=owner,ChangedUser=changed),dict(bAct=owner==changed))
    for owner,new,old in itertools.product((0,1),repeat=3):add('Device','Pairing',dict(OwnerUser=owner,NewUser=new,OldUser=old),dict(bAct=owner in (new,old)))
    for platform,editor in itertools.product((False,True),repeat=2):add('Device','Platform',dict(bPlatformTraits=platform,bEditorTraits=editor),dict(bAct=platform or editor))
    for pending in (False,True):add('Device','Schedule',dict(bPendingProcess=pending),dict(bAct=not pending))
    device_sets=([],[(True,False)],[(False,True)],[(True,True)],[(False,True),(True,False),(True,True)])
    for devices in device_sets:
        rows=[UEPNativeInputDeviceRow(DeviceId=i,bConnected=connected,bGamepad=gamepad) for i,(connected,gamepad) in enumerate(devices)]
        for screen in (False,True):add('Device','Process',dict(Devices=rows,bScreenPresent=screen),dict(Action='Show' if not any(x and y for x,y in devices) else 'Hide' if screen else 'None'))
    for player,busy in itertools.product((False,True),repeat=2):
        for keep in (-1,0,1,3):add('Replay','Start',dict(bHasLocalPlayer=player,bBusy=busy,NumberToKeep=keep),dict(bAct=player and not busy and keep>0))
    replay_sets=([],[(30,False,False),(20,False,False),(10,False,False)],[(30,True,False),(20,False,False),(10,False,False)],[(30,False,True),(20,False,False),(10,False,False)],[(30,True,False),(20,True,False)],[(638000000000000001,False,False),(638000000000000000,False,False),(638000000000000000,False,False)])
    for values in replay_sets:
        rows=[UEPNativeReplayPolicyRow(Index=i,Name='UEP_'+str(i),TimestampTicks=t,bShouldKeep=keep,bIsLive=live) for i,(t,keep,live) in enumerate(values)]
        for keep,recording in itertools.product((0,1,2,5),(False,True)):
            remaining=[i for i,(_,protected,_) in enumerate(values) if not protected]
            remaining.sort(key=lambda i:(-values[i][0],i))
            if recording and remaining and not values[remaining[0]][2]:remaining.insert(0,None)
            selected=remaining[keep] if keep>0 and len(remaining)>keep else None
            chosen=selected if selected is not None and not values[selected][2] else -1
            add('Replay','Select',dict(Streams=rows,NumberToKeep=keep,bRecording=recording,bHasLocalPlayer=True,bHasStreamer=True),dict(DeleteIndex=chosen))
    for succeeded in (False,True):add('Replay','Deleted',dict(bDeleteSucceeded=succeeded),dict(bAct=succeeded))
    for hdr,ldr in (([],[]),([a,b],[b,c]),([a,a,None],[a,c,None]),([None],[a]),([a],[a])):
        for selected in (False,True):
            apply,clear=(hdr,ldr) if selected else (ldr,hdr)
            add('Audio','DynamicRange',dict(bHDR=selected,HDRSubmixes=hdr,LDRSubmixes=ldr),dict(ApplyIndices=list(range(len(apply))),ClearIndices=[i for i,x in enumerate(clear) if x not in apply]))
    for applied,wanted,mix,has_world in itertools.product((False,True),repeat=4):add('Audio','Loading',dict(bAppliedLoading=applied,bWantsLoading=wanted,bHasMix=mix,bHasWorld=has_world),dict(bAct=applied!=wanted and mix and has_world))
    for allow,same,same_state,different,invalid,team,asc in itertools.product((False,True),repeat=7):
        add('Damage','CanCause',dict(bAllowSelf=allow,bSameObject=same,bSamePlayerState=same_state,bDifferentTeams=different,bInvalidRelationship=invalid,bInstigatorHasTeam=team,bTargetHasASC=asc),dict(bAllowed=(allow and(same or same_state))or different or(invalid and team and asc)))
    for capacity in (1.,3.):
        for value in (-1.,0.,.5,1.,3.,5.):add('Attribute','Clamp',dict(Attribute='BombsRemaining',Input=value,BombCapacity=capacity),dict(Result=max(0.,min(value,capacity))))
    for name in ('BombCapacity','BombRange'):
        for value in (-1.,1.,5.):add('Attribute','Clamp',dict(Attribute=name,Input=value),dict(Result=max(1.,value)))
    for value in (100.,200.,450.,800.,900.):add('Attribute','Clamp',dict(Attribute='MovementSpeed',Input=value),dict(Result=max(200.,min(value,800.))))
    add('Attribute','Clamp',dict(Attribute='Unknown',Input=.5),dict(Result=.5))
    for player,experience,asset,loaded in itertools.product((False,True),repeat=4):
        add('Pawn','Data',dict(PlayerStateData=a if player else None,ExperienceData=b if experience else None,AssetManagerData=c if asset else None,bExperienceLoaded=loaded),dict(SelectedData=a if player else b if loaded and experience else c if loaded and asset else None))
    for base,manager,allowed in itertools.product((False,True),repeat=3):add('Pawn','Restart',dict(bBaseRestartAllowed=base,bHasSpawningManager=manager,bManagerRestartAllowed=allowed),dict(bAllowed=base and(not manager or allowed)))
    classes=dict(Device='UEPNativeDevicePolicyContext',Replay='UEPNativeReplayPolicyContext',Audio='UEPNativeAudioPolicyContext',Damage='UEPNativeDamagePolicyContext',Attribute='UEPNativeAttributePolicyContext',Pawn='UEPNativePawnPolicyContext')
    try:
        for family in COUNTS:
            for selected,suffix in ((False,'Native'),(True,'Python')):
                ue.set_mixin_profile(host,family+suffix)
                for operation,fields,outputs in cases[family]:
                    context=ue.new_object(ue.find_class(classes[family]),host);operation=family+'.'+operation;context.set_property('Operation',operation)
                    for name,value in fields.items():context.set_property(name,value)
                    if family=='Replay' and 'Streams' in fields:
                        require([int(r.TimestampTicks) for r in context.Streams]==[int(r.TimestampTicks) for r in fields['Streams']],'64-bit replay timestamps changed')
                    initial={name:context.get_property(name) for name in outputs}
                    require(bool(host.call_function('UEPUsesPythonPolicy',operation))==selected,'rule selector differs: '+operation)
                    if selected:host.call_function('UEPApplyPolicy',context)
                    require(bool(context.bCompleted)==selected,'typed rule did not complete: '+operation)
                    for name,expected in outputs.items():
                        expected=expected if selected else initial[name];actual=context.get_property(name)
                        if name=='Action':actual=str(actual);expected=str(expected)
                        if isinstance(expected,list):actual=list(actual)
                        require(abs(float(actual)-expected)<.00001 if isinstance(expected,float) else actual==expected,'rule output differs: '+operation+'/'+name)
                    result['counts'][family]+=1
                if family=='Pawn':
                    for primary,secondary in ((None,None),(ue.find_class('Pawn'),None),(None,ue.find_class('LyraCharacter')),(ue.find_class('Pawn'),ue.find_class('LyraCharacter'))):
                        require(bool(host.call_function('UEPUsesPythonPolicy','Pawn.Class'))==selected,'Pawn class selector differs')
                        if selected:require(host.call_function('UEPChooseObject','Pawn.Class',primary,secondary)==(primary if primary is not None else secondary),'Pawn class/null identity differs')
                        result['counts'][family]+=1
        result['trace_bounded']=len(rule_policies.metrics(host)['trace'])<=128
        result['unknown_operation_uses_native']=not host.call_function('UEPUsesPythonPolicy','Pawn.Unknown')
    finally:
        for value in reversed(roots):value.remove_from_root()
        result['roots_restored']=all(not value.is_rooted() for value in roots)
    gate(result);return result


if '--check-report' in sys.argv:print(json.dumps(gate(json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8-sig')))))
else:
    try:
        import unreal_engine as ue
        script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_rule_boundaries.py'))).resolve();sys.path.insert(0,str(script.parent))
        from stage_safety import require_authoring_stage
        require_authoring_stage(arg('UEPNativeCarrierStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=run()
    except Exception:report=dict(status='failed',error=traceback.format_exc())
    Path(arg('UEPNativeCarrierResult')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    (ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_RULE_BOUNDARIES_'+report['status'].upper())
    if report['status']!='passed':raise RuntimeError(report['error'])
