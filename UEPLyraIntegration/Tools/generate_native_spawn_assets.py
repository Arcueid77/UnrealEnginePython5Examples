"""Bind the retained production spawning rules without editing its restart graph."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def argument(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def generate(stage,output):
    from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    from mixin_graph_gates import semantics
    from uep_lyra_native.spawning import CLASS
    bp=ue.load_object(Blueprint,CLASS.rsplit('_C',1)[0]);ue.unregister_all_mixins();parent=bp.ParentClass
    if parent!=ue.find_class('TDM_PlayerSpawningManagmentComponent'):raise RuntimeError('Original TDM spawning parent differs')
    def export(name):
        p=output/(name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp.GeneratedClass.get_cdo(),str(p)):raise RuntimeError('Spawning CDO export failed')
        b=p.read_bytes();t=b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        return '\n'.join(r for r in t.splitlines() if not r.strip().startswith(('PythonMixinSet=','PythonMixinProfile=')))
    before=export('before');graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixins=ue.create_asset('DA_NativeSpawningMixin','/Game/UEPNative',UEPPythonMixinSet,factory)
    mixins.DefaultProfile='Python';mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.spawning',PythonClass='Spawning'+p+'Profile') for p in ('Python','NativeFallback')]
    ue.blueprint_configure_mixin(bp,mixins,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or bp.ParentClass!=parent or export('after')!=before or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original spawning configuration/graphs changed')
    ue.register_declared_mixin(bp.GeneratedClass)
    try:
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!={'Python':2,'NativeFallback':2}:raise RuntimeError('Spawning policy method counts differ')
    finally:ue.unregister_all_mixins()
    signatures={name:ue.describe_function(bp.GeneratedClass,name) for name in ('UEPChooseFromStarts','UEPChooseTDMStart','UEPChooseSpecificStart','UEPGetStartOccupancy','UEPIsStartClaimed','UEPTryClaimStart')}
    for obj in (bp,mixins):obj.save_package()
    assets=['Content/UEPNative/DA_NativeSpawningMixin.uasset','Plugins/GameFeatures/ShooterCore/Content/Game/B_TeamSpawningRules.uasset']
    return dict(status='passed',asset_family_count=2,assets=assets,assets_saved=True,class_path=CLASS,method_counts=counts,signatures=signatures,
        original_defaults_graphs_and_inheritance_preserved=True,policy_events=2,runtime_acceptance=False,
        asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(argument('UEPNativeSpawnAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_spawn_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeSpawnStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()))
    report=generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_SPAWN_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
