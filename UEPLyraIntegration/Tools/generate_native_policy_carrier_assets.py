"""Create the thin policy Blueprint; original native gameplay owners stay intact."""
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def run(stage):
    from unreal_engine.classes import DataAssetFactory,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;data=ue.create_asset('DA_GlobalGameplayPolicy','/Game/UEPNative',UEPPythonMixinSet,factory);data.DefaultProfile='Python';data.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule='uep_lyra_native.global_policy',PythonClass=cls) for name,cls in (('Python','GameplayPolicyPython'),('NativeGameplayFallback','GameplayPolicyNative'))]
    bp=ue.create_blueprint(ue.find_class('UEPNativeGameplayPolicy'),'/Game/UEPNative/BP_GlobalGameplayPolicy');ue.blueprint_configure_mixin(bp,data,'Python','PythonMixinProfile');ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('Native policy carrier failed Blueprint compilation')
    data.save_package();bp.save_package();ue.register_declared_mixin(bp.GeneratedClass);row=next(r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass);counts={k:len(v['functions']) for k,v in row['profiles'].items()}
    if counts!={'Python':3,'NativeGameplayFallback':3}:raise RuntimeError('Native policy carrier methods differ')
    return dict(status='passed',assets_saved=True,asset_family_count=2,policy_events=3,assets=['Content/UEPNative/DA_GlobalGameplayPolicy.uasset','Content/UEPNative/BP_GlobalGameplayPolicy.uasset'],fixtures=[],retained_abilities=[],native_gameplay_classes_replaced=False,raw_gas_pointers_exposed=False,runtime_acceptance=False)


result=Path(arg('UEPNativeCarrierAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_policy_carrier_assets.py'))).resolve();sys.path.insert(0,str(script.parent));from stage_safety import require_authoring_stage
    stage=require_authoring_stage(arg('UEPNativeCarrierStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=run(stage)
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_CARRIER_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
