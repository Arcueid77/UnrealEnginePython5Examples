"""Extend existing ability Sets; retain the original ability Blueprint bytes."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def generate(stage,output):
    from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    from uep_lyra_native.tag_stack_costs import OWNERS
    assets=[];proof=[];retained=[]
    for owner,set_path,prefix in OWNERS:
        package=owner.rsplit('.',1)[0];mount=package.split('/')[1];relative=('Content/'+package[len('/Game/'):] if mount=='Game' else 'Plugins/GameFeatures/'+mount+'/Content/'+package[len('/'+mount+'/'):])+'.uasset'
        path=stage/relative;before=hashlib.sha256(path.read_bytes()).hexdigest().upper();cls=ue.load_class(owner);mixins=ue.load_object(UEPPythonMixinSet,set_path)
        profiles=[p.clone() for p in mixins.Profiles];names={str(p.ProfileName) for p in profiles}
        if names!={'Python','BlueprintFallback'}:raise RuntimeError('Original ability profile family differs')
        legacy=next(p.clone() for p in profiles if str(p.ProfileName)=='BlueprintFallback');legacy_values=(str(legacy.PythonModule),str(legacy.PythonClass));default=str(mixins.DefaultProfile)
        for p in profiles:
            if str(p.ProfileName)=='Python':p.PythonModule='uep_lyra_native.tag_stack_costs';p.PythonClass=prefix+'CostPythonProfile'
        profiles.append(UEPPythonMixinProfile(ProfileName='NativeCostFallback',PythonModule='uep_lyra_native.tag_stack_costs',PythonClass=prefix+'CostNativeFallbackProfile'));mixins.Profiles=profiles
        ue.unregister_all_mixins();ue.register_declared_mixin(cls);registered=next(r for r in ue.get_registered_mixins() if r['target_class']==cls);counts={p:len(v['functions']) for p,v in registered['profiles'].items()}
        expected={'Weapon':10,'Heal':2,'Net':5}[prefix]
        if counts!={'Python':expected+3,'BlueprintFallback':expected,'NativeCostFallback':expected+3}:raise RuntimeError('Retained Blueprint/cost profile methods differ')
        current=next(p for p in mixins.Profiles if str(p.ProfileName)=='BlueprintFallback')
        if (str(current.PythonModule),str(current.PythonClass))!=legacy_values or str(mixins.DefaultProfile)!=default:raise RuntimeError('Legacy fallback/default profile changed')
        mixins.save_package();set_relative='Content/'+set_path[len('/Game/'):].split('.')[0]+'.uasset';assets.append(set_relative)
        if hashlib.sha256(path.read_bytes()).hexdigest().upper()!=before:raise RuntimeError('Original ability Blueprint bytes changed')
        retained.append(dict(relative=relative,sha256=before));proof.append(dict(owner=owner,profiles=counts,previous_blueprint_python_methods_retained=True))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;fixture_set=ue.create_asset('DA_CostFixtureMixin','/Game/UEPValidation',UEPPythonMixinSet,factory);fixture_set.DefaultProfile='Python'
    fixture_set.Profiles=[UEPPythonMixinProfile(ProfileName=name,PythonModule='uep_lyra_native.tag_stack_costs',PythonClass=cls) for name,cls in (('Python','CostPythonProfile'),('NativeCostFallback','CostNativeFallbackProfile'))]
    bp=ue.create_blueprint(ue.find_class('UEPNativeCostWitness'),'/Game/UEPValidation/GA_TagStackCostWitness');ue.blueprint_configure_mixin(bp,fixture_set,'Python','PythonMixinProfile');ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('Cost witness compilation failed')
    fixture_set.save_package();bp.save_package();fixtures=['Content/UEPValidation/DA_CostFixtureMixin.uasset','Content/UEPValidation/GA_TagStackCostWitness.uasset']
    return dict(status='passed',assets_saved=True,asset_family_count=3,policy_events=3,assets=assets,fixtures=fixtures,classes=proof,retained_abilities=retained,runtime_acceptance=False,
        asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets+fixtures})


result=Path(arg('UEPNativeCostAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_cost_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(arg('UEPNativeCostStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',runtime_acceptance=False,error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_COST_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
