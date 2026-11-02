"""Validate value-only death/reset plans and native-class mixin ownership."""
import json
from pathlib import Path
import sys
import traceback


def require(value,message):
    if not value:raise AssertionError(message)
def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))
def gate(r):
    require(r['status']=='passed' and r['error'] is None and r['native_reset_class_routed'] and r['inherited_death_event_routed'] and r['native_functions_restored'],'native lifecycle interface ownership failed')
    require(r['reset_plan']==['CancelOthers','MakeUncancelable','ResetCharacter','BroadcastReset','ActivateBlueprint','EndAbility'],'native reset action sequence differs')
    require(r['death_plans']==[['CancelOthers','MakeUncancelable','BlockAbilities','ActivateBlueprint'],['CancelOthers','MakeUncancelable','BlockAbilities','StartDeath','ActivateBlueprint']],'native death auto-start action sequence differs')
    return dict(status='passed',native_class_mixin_supported=True,inherited_event_supported=True,raw_gas_pointers_exposed=False)


def run(stage):
    import unreal_engine as ue
    from uep_lyra_native import ability_lifecycle as policy
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    reset=ue.find_class('LyraGameplayAbility_Reset');death=ue.find_class('LyraGameplayAbility_Death');hero=ue.load_class('/Game/Characters/Heroes/Abilities/GA_Hero_Death.GA_Hero_Death_C');ue.register_declared_mixin(hero)
    old_reset=reset.get_cdo().find_function('UEPResetActivationPlan');old_death=hero.get_cdo().find_function('UEPDeathActivationPlan');installed=[]
    r=dict(status='running',error=None,native_reset_class_routed=False,inherited_death_event_routed=False,native_functions_restored=False)
    try:
        policy.install_native_reset();installed.append(reset);r['native_reset_class_routed']=bool(reset.get_cdo().call_function('UEPUsesPythonResetPolicy'));r['reset_plan']=[str(x) for x in reset.get_cdo().call_function('UEPResetActivationPlan')]
        ue.register_mixin_profile(death,'Python',policy.DeathPolicyPython,make_default=True);installed.append(death);ue.register_mixin_profile(death,'BlueprintFallback',policy.DeathPolicyNative)
        cdo=hero.get_cdo();r['inherited_death_event_routed']=bool(cdo.call_function('UEPUsesPythonDeathPolicy'));r['death_plans']=[[str(x) for x in cdo.call_function('UEPDeathActivationPlan',value)] for value in (False,True)]
        require([str(x) for x in cdo.call_function('UEPDeathEndPlan')]==['FinishDeath','EndBlueprint'],'native death end sequence differs')
        for has_health,state in ((False,-1),(True,0),(True,1),(True,2)):
            require(bool(cdo.call_function('UEPShouldStartDeath',has_health,state))==(has_health and state==0),'death start snapshot decision differs');require(bool(cdo.call_function('UEPShouldFinishDeath',has_health,state))==(has_health and state==1),'death finish snapshot decision differs')
    finally:
        for cls in reversed(installed):ue.unregister_mixin(cls)
        r['native_functions_restored']=reset.get_cdo().find_function('UEPResetActivationPlan')==old_reset and hero.get_cdo().find_function('UEPDeathActivationPlan')==old_death
    r['status']='passed';gate(r);return r


if '--check-report' in sys.argv:print(json.dumps(gate(json.loads(Path(sys.argv[sys.argv.index('--check-report')+1]).read_text(encoding='utf-8-sig'))),indent=2))
else:
    import unreal_engine as ue
    result=Path(arg('UEPNativeLifecycleProbeResult'))
    try:
        script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('probe_native_lifecycle_interfaces.py'))).resolve();sys.path.insert(0,str(script.parent));report=run(Path(arg('UEPNativeLifecycleProbeStageRoot')).resolve())
    except Exception:report=dict(status='failed',error=traceback.format_exc())
    result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_LIFECYCLE_PROBE_'+report['status'].upper())
    if report['status']!='passed':raise RuntimeError(report['error'])
