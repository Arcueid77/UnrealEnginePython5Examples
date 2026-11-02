"""Configure constant profile selectors without replacing instanced fragments."""
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
    from uep_lyra_native.item_stats import CLASSES
    from explorer_character_cdo import canonical_cdo
    from mixin_graph_gates import semantics
    def export(obj,name):
        path=output/(name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(path)):raise RuntimeError('Item definition CDO export failed')
        raw=path.read_bytes();return canonical_cdo(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;mixins=ue.create_asset('DA_InitialStatsMixin','/Game/UEPNative',UEPPythonMixinSet,factory)
    mixins.DefaultProfile='Python';mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.item_stats',PythonClass='InitialStats'+p+'Profile') for p in ('Python','NativeFallback')]
    assets=[];details=[]
    for index,name in enumerate(CLASSES):
        bp=ue.load_object(Blueprint,name.rsplit('_C',1)[0]);ue.unregister_all_mixins();parent=bp.ParentClass;cdo=bp.GeneratedClass.get_cdo();before=export(cdo,str(index)+'-before')
        fragments=list(cdo.get_property('Fragments'));graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
        ue.blueprint_configure_mixin(bp,mixins,'Python');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or bp.ParentClass!=parent or export(bp.GeneratedClass.get_cdo(),str(index)+'-after')!=before:raise RuntimeError('Const item definition defaults/parent changed')
        if any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original item definition graph changed')
        current=list(bp.GeneratedClass.get_cdo().get_property('Fragments'))
        if [f.get_class().get_path_name() for f in current]!=[f.get_class().get_path_name() for f in fragments]:raise RuntimeError('Native fragment classes/order changed')
        ue.register_declared_mixin(bp.GeneratedClass)
        try:
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!={'Python':2,'NativeFallback':2}:raise RuntimeError('Initial-stat profile functions differ')
            snapshots=[dict(tag=str(r.Tag.TagName),count=int(r.Count)) for f in current if f.is_a(ue.find_class('InventoryFragment_SetStats')) for r in f.call_function('UEPGetInitialStats')]
            if len(snapshots)!=3:raise RuntimeError('Typed snapshot lost initial stat rows')
        finally:ue.unregister_all_mixins()
        bp.save_package();relative='Plugins/GameFeatures/ShooterCore/Content/'+name[len('/ShooterCore/'):].split('.')[0]+'.uasset';assets.append(relative)
        details.append(dict(target=name,profiles=counts,constant_selector=True,original_defaults_graphs_inheritance_and_native_fragments_preserved=True,initial_stats=snapshots))
    mixins.save_package();assets.append('Content/UEPNative/DA_InitialStatsMixin.uasset')
    return dict(status='passed',assets_saved=True,asset_family_count=6,policy_events=2,assets=assets,classes=details,runtime_acceptance=False,asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(arg('UEPNativeStatsAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_stats_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(arg('UEPNativeStatsStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',runtime_acceptance=False,error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_STATS_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
