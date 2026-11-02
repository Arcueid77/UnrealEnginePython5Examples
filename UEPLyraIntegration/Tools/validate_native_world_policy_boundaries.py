"""Verify typed native inputs and policy result marshalling for CPP16-18."""
import itertools
import json
from pathlib import Path
import sys
import traceback


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def require(value,message):
    if not value:raise AssertionError(message)


def gate(report):
    require(report['status']=='passed' and report['error'] is None and report['roots_restored'],'world policy boundaries failed')
    require(report['frontend_cases']==70 and report['part_cases']==28 and report['camera_cases']==8,'typed world-policy matrix incomplete')
    require(not report['native_handles_exposed'] and not report['online_service_tested'],'world policy boundary overclaim')
    return {key:report[key] for key in ('status','frontend_cases','part_cases','camera_cases','online_service_tested')}


def run():
    import unreal_engine as ue
    from unreal_engine.structs import UEPNativeCharacterPartPolicyRow
    from uep_lyra_native import global_policy
    world=ue.get_editor_world();cls=ue.load_class(global_policy.CLASS);ue.register_declared_mixin(cls)
    host=ue.new_object(cls,world);roots=[]
    for obj in (cls,host):
        if not obj.is_rooted():obj.add_to_root();roots.append(obj)
    result=dict(status='passed',error=None,frontend_cases=0,part_cases=0,camera_cases=0,native_handles_exposed=False,online_service_tested=False)
    try:
        inputs=[('Plan',{},['Initialize','PressStart','JoinRequested','Main'])]
        for hard,user,session in itertools.product((False,True),repeat=3):inputs.append(('Initialize',dict(bHardDisconnect=hard,bHasUser=user,bHasSession=session),(['ResetUsers'] if hard and user else [])+(['CleanSessions'] if session else [])+['Continue']))
        for logged,wait,layout in itertools.product((False,True),repeat=3):inputs.append(('PressStart',dict(bLoggedIn=logged,bWaitForStart=wait,bHasRootLayout=layout),['Continue'] if logged else ['AutoLogin'] if not wait else ['PushStart'] if layout else []))
        for success in (False,True):
            inputs += [('UserInitialized',dict(bSuccess=success),['Continue']),('JoinResult',dict(bSuccess=success),['Cancel'] if success else ['Continue'])]
        for requested,can in itertools.product((False,True),repeat=2):inputs.append(('JoinRequested',dict(bRequestedSession=requested,bCanJoin=can),['Join'] if requested and can else ['Continue']))
        for layout in (False,True):inputs.append(('Main',dict(bHasRootLayout=layout),['PushMain'] if layout else []))
        for ready,canceled in itertools.product((False,True),repeat=2):
            values=dict(bWidgetReady=ready,bWidgetCanceled=canceled)
            inputs += [('StartWidget',values,['ClearLoading','WaitForDeactivate'] if ready else ['ClearLoading','Continue'] if canceled else []),('MainWidget',values,['ClearLoading','Continue'] if ready or canceled else [])]
        for selected,profile in ((False,'FrontendNative'),(True,'FrontendPython')):
            ue.set_mixin_profile(host,profile)
            for name,values,expected in inputs:
                context=ue.new_object(ue.find_class('UEPNativeFrontendPolicyContext'),host);context.set_property('Operation','Frontend.'+name)
                for key,value in values.items():context.set_property(key,value)
                require(bool(host.call_function('UEPUsesPythonPolicy','Frontend.'+name))==selected,'frontend route differs')
                if selected:host.call_function('UEPApplyPolicy',context)
                require(bool(context.bCompleted)==selected and [str(v) for v in context.Actions]==(expected if selected else []),'typed frontend actions differ: '+name)
                result['frontend_cases']+=1
        rows=[UEPNativeCharacterPartPolicyRow(Index=i,Source=i//2,bHandleValid=bool(i%2),bEquivalent=i in (2,4)) for i in range(8)]
        for selected,profile in ((False,'PartsNative'),(True,'PartsPython')):
            ue.set_mixin_profile(host,profile)
            for customizer in (False,True):
                for name,expected in (('Add',[7]),('Remove',[2]),('RemoveAll',list(range(8))),('Detach',list(range(8))),('Attach',[0,4,6])):
                    context=ue.new_object(ue.find_class('UEPNativeCharacterPartPolicyContext'),host);context.set_property('Operation','Parts.'+name);context.set_property('Entries',rows);context.set_property('bHasCustomizer',customizer)
                    if selected:host.call_function('UEPApplyPolicy',context)
                    wanted=expected if selected and (customizer or name=='Remove') else []
                    require(bool(context.bCompleted)==selected and list(context.Indices)==wanted,'typed part selection differs: '+name);result['part_cases']+=1
            for suppressed in (False,True):
                context=ue.new_object(ue.find_class('UEPNativeCharacterPartPolicyContext'),host);context.set_property('Operation','Parts.Suppress');context.set_property('Entries',rows);context.set_property('bSuppressed',suppressed)
                if selected:host.call_function('UEPApplyPolicy',context)
                require(list(context.Indices)==([0,1] if suppressed else [2,3]) if selected else not list(context.Indices),'part suppression source selection differs');result['part_cases']+=1
            # Empty lists and missing customizers must stay empty.
            for name in ('Add','Attach'):
                context=ue.new_object(ue.find_class('UEPNativeCharacterPartPolicyContext'),host);context.set_property('Operation','Parts.'+name);context.set_property('bHasCustomizer',True)
                if selected:host.call_function('UEPApplyPolicy',context)
                require(not list(context.Indices),'empty part list produced an index');result['part_cases']+=1
        a,b=ue.find_class('LyraCameraMode'),ue.find_class('LyraCameraMode_ThirdPerson')
        for selected,profile in ((False,'CameraNative'),(True,'CameraPython')):
            ue.set_mixin_profile(host,profile)
            for primary,secondary in ((None,None),(a,None),(None,b),(a,b)):
                require(bool(host.call_function('UEPUsesPythonPolicy','Camera.Determine'))==selected,'camera route differs')
                if selected:require(host.call_function('UEPChooseObject','Camera.Determine',primary,secondary)==(primary if primary is not None else secondary),'camera class/null marshalling differs')
                result['camera_cases']+=1
    finally:
        for obj in reversed(roots):obj.remove_from_root()
        result['roots_restored']=all(not obj.is_rooted() for obj in roots)
    gate(result);return result


if '--check-report' in sys.argv:
    print(json.dumps(gate(json.loads(Path(sys.argv[-1]).read_text(encoding='utf-8-sig')))))
else:
    try:
        import unreal_engine as ue
        script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_world_policy_boundaries.py'))).resolve();sys.path.insert(0,str(script.parent))
        from stage_safety import require_authoring_stage
        require_authoring_stage(arg('UEPNativeCarrierStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=run()
    except Exception:report=dict(status='failed',error=traceback.format_exc())
    Path(arg('UEPNativeCarrierResult')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    (ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_WORLD_BOUNDARIES_'+report['status'].upper())
    if report['status']!='passed':raise RuntimeError(report['error'])
