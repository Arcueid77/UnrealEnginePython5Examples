"""Append native lifecycle profiles while retaining prior Blueprint methods and bytes."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def generate(stage):
    from unreal_engine.classes import UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    kind=arg('UEPNativeLifecycleKind');prefix={'jump':'Jump','death':'Death'}[kind];name={'jump':'JumpAbility','death':'DeathAbility'}[kind];owner='/Game/Characters/Heroes/Abilities/GA_Hero_'+prefix+'.GA_Hero_'+prefix+'_C';relative='Content/Characters/Heroes/Abilities/GA_Hero_'+prefix+'.uasset';asset=stage/relative;before=hashlib.sha256(asset.read_bytes()).hexdigest().upper();cls=ue.load_class(owner)
    data=ue.load_object(UEPPythonMixinSet,'/Game/UEPMixins/DA_'+name+'Mixin.DA_'+name+'Mixin');ue.register_declared_mixin(cls);old=next(r for r in ue.get_registered_mixins() if r['target_class']==cls);old_count=len(old['profiles']['Python']['functions']);profiles=[p.clone() for p in data.Profiles]
    if {str(p.ProfileName) for p in profiles}!={'Python','BlueprintFallback'}:raise RuntimeError('Fresh lifecycle declaration baseline required')
    legacy=next(p for p in profiles if str(p.ProfileName)=='BlueprintFallback');legacy_values=str(legacy.PythonModule),str(legacy.PythonClass);default=str(data.DefaultProfile)
    for p in profiles:
        if str(p.ProfileName)=='Python':p.PythonModule='uep_lyra_native.ability_lifecycle';p.PythonClass=prefix+'PythonProfile'
    profiles.append(UEPPythonMixinProfile(ProfileName='NativeLifecycleFallback',PythonModule='uep_lyra_native.ability_lifecycle',PythonClass=prefix+'NativeProfile'));data.Profiles=profiles;ue.unregister_mixin(cls);ue.register_declared_mixin(cls);row=next(r for r in ue.get_registered_mixins() if r['target_class']==cls);counts={k:len(v['functions']) for k,v in row['profiles'].items()};events=4 if kind=='jump' else 5
    if counts!={'Python':old_count+events,'BlueprintFallback':len(old['profiles']['BlueprintFallback']['functions']),'NativeLifecycleFallback':old_count+events}:raise RuntimeError('Lifecycle methods changed unexpectedly')
    if str(data.DefaultProfile)!=default or (str(legacy.PythonModule),str(legacy.PythonClass))!=legacy_values:raise RuntimeError('Original default/fallback modified')
    data.save_package();output='Content/UEPMixins/DA_'+name+'Mixin.uasset'
    if hashlib.sha256(asset.read_bytes()).hexdigest().upper()!=before:raise RuntimeError('Original ability Blueprint bytes changed')
    return dict(status='passed',assets_saved=True,asset_family_count=1,policy_events=events,kind=kind,assets=[output],fixtures=[],retained_abilities=[dict(relative=relative,sha256=before)],profiles=counts,previous_blueprint_python_fixed=True,runtime_acceptance=False)


result=Path(arg('UEPNativeLifecycleAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_lifecycle_assets.py'))).resolve();sys.path.insert(0,str(script.parent));from stage_safety import require_authoring_stage
    stage=require_authoring_stage(arg('UEPNativeLifecycleStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage)
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_LIFECYCLE_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
