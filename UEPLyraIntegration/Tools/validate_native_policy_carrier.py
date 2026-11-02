"""Blueprint-owned typed policy contexts; no native UClass mixin mutation."""
import json
from pathlib import Path
import sys
import traceback


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def require(value,message):
    if not value:raise AssertionError(message)
def gate(r):
    require(r['status']=='passed' and r['error'] is None and len(r['cases'])==4 and r['roots_restored'],'native policy carrier fixture failed')
    for row in r['cases']:
        require(row['selected']==(row['profile']=='Python'),'native policy carrier selector differs')
        require(row['completed']==row['selected'] and row['actions']==(['CancelOthers','MakeUncancelable','ResetCharacter','BroadcastReset','ActivateBlueprint','EndAbility'] if row['selected'] else []),'native carrier typed context writeback differs')
    require(r['unknown_operation_uses_native'] and not r['native_class_router_used'] and not r['actual_gas_reset_acceptance'],'policy carrier scope differs')
    return dict(status='passed',typed_context_cases=4,native_class_router_used=False,actual_gas_reset_acceptance=False)


def run(stage):
    import unreal_engine as ue
    from uep_lyra_native import global_policy as policy
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()));cls=ue.load_class(policy.CLASS);ue.register_declared_mixin(cls);rooted=cls.is_rooted()
    if not rooted:cls.add_to_root()
    owner=ue.new_object(cls,ue.get_editor_world());owner.add_to_root();r=dict(status='running',error=None,cases=[],native_class_router_used=False,actual_gas_reset_acceptance=False)
    try:
        for profile in ('NativeGameplayFallback','Python'):
            ue.set_mixin_profile(owner,profile)
            for character in (False,True):
                ctx=ue.new_object(ue.find_class('UEPNativeResetPolicyContext'),owner);ctx.add_to_root()
                try:
                    ctx.set_property('Operation','Reset.Activate');ctx.set_property('bHasCharacter',character);selected=bool(owner.call_function('UEPUsesPythonPolicy','Reset.Activate'))
                    if selected:owner.call_function('UEPApplyPolicy',ctx)
                    r['cases'].append(dict(profile=profile,has_character=character,selected=selected,completed=bool(ctx.bCompleted),actions=[str(x) for x in ctx.Actions]))
                finally:ctx.remove_from_root()
        r['unknown_operation_uses_native']=not bool(owner.call_function('UEPUsesPythonPolicy','Unimplemented.Operation'))
    finally:
        ue.clear_mixin_profile(owner);owner.remove_from_root()
        if not rooted:cls.remove_from_root()
        r['roots_restored']=cls.is_rooted()==rooted and not owner.is_rooted()
    r['status']='passed';gate(r);return r


if '--check-report' in sys.argv:print(json.dumps(gate(json.loads(Path(sys.argv[sys.argv.index('--check-report')+1]).read_text(encoding='utf-8-sig'))),indent=2))
else:
    import unreal_engine as ue
    result=Path(arg('UEPNativeCarrierResult'))
    try:
        script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('validate_native_policy_carrier.py'))).resolve();sys.path.insert(0,str(script.parent));report=run(Path(arg('UEPNativeCarrierStageRoot')).resolve())
    except Exception:report=dict(status='failed',error=traceback.format_exc())
    result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_CARRIER_BOUNDARIES_'+report['status'].upper())
    if report['status']!='passed':raise RuntimeError(report['error'])
