"""Add explicit batch profiles without enabling unaccepted defaults."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def run():
    from unreal_engine.structs import UEPPythonMixinProfile
    data=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPNative/DA_GlobalGameplayPolicy.DA_GlobalGameplayPolicy')
    cls=ue.load_class('/Game/UEPNative/BP_GlobalGameplayPolicy.BP_GlobalGameplayPolicy_C')
    profiles=[('Python','uep_lyra_native.world_policies','CameraPython'),('NativeGameplayFallback','uep_lyra_native.global_policy','GameplayPolicyNative')]
    promote='-UEPNativePromoteRulePolicies' in sys.argv
    if promote:profiles[0]=('Python','uep_lyra_native.rule_policies','PawnPython')
    profiles += [(name,'uep_lyra_native.world_policies',name) for name in ('FrontendNative','FrontendPython','PartsNative','PartsPython','CameraNative','CameraPython')]
    profiles += [(name,'uep_lyra_native.rule_policies',name) for name in ('DeviceNative','DevicePython','ReplayNative','ReplayPython','AudioNative','AudioPython','DamageNative','DamagePython','AttributeNative','AttributePython','PawnNative','PawnPython')]
    data.DefaultProfile='Python';data.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule=module,PythonClass=cls) for name,module,cls in profiles]
    ue.unregister_mixin(cls);ue.register_declared_mixin(cls)
    row=next(r for r in ue.get_registered_mixins() if r['target_class']==cls)
    if len(row['profiles'])!=20 or any(len(p['functions'])!=3 for p in row['profiles'].values()):raise RuntimeError('World policy profile signatures differ: '+str({n:len(p['functions']) for n,p in row['profiles'].items()}))
    data.save_package()
    return dict(status='passed',assets_saved=True,asset_family_count=2,policy_events=3,assets=['Content/UEPNative/DA_GlobalGameplayPolicy.uasset','Content/UEPNative/BP_GlobalGameplayPolicy.uasset'],fixtures=[],retained_abilities=[],native_gameplay_classes_replaced=False,raw_gas_pointers_exposed=False,new_defaults_enabled=promote,runtime_acceptance=False)


result=Path(arg('UEPNativeCarrierAssetsResult'))
try:
    sys.path.insert(0,str(Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('extend_native_rule_policy_assets.py'))).resolve().parent))
    from stage_safety import require_authoring_stage
    require_authoring_stage(arg('UEPNativeCarrierStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=run()
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_CARRIER_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
