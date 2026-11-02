"""Configure the four audited HUD layout shells; preserve their native defaults."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def argument(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def generate(stage,output):
    from unreal_engine.classes import Blueprint,UEPPythonMixinSet,DataAssetFactory
    from unreal_engine.structs import UEPPythonMixinProfile
    from explorer_character_cdo import canonical_cdo
    from mixin_graph_gates import semantics
    from uep_lyra_native.escape_menu import CLASSES
    factory=ue.new_object(DataAssetFactory);factory.DataAssetClass=UEPPythonMixinSet
    mixins=ue.create_asset('DA_EscapeMenuMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);mixins.DefaultProfile='Python'
    mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.escape_menu',PythonClass='EscapeMenu'+p+'Profile') for p in ('Python','NativeFallback')]
    assets=[];proof=[]
    def export(bp,label):
        path=output/(label+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp.GeneratedClass.get_cdo(),str(path)):raise RuntimeError('Escape HUD CDO export failed')
        raw=path.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
        return canonical_cdo('\n'.join(line for line in text.splitlines() if not line.strip().startswith(('PythonMixinProfile=','PythonMixinSet='))))
    for index,name in enumerate(CLASSES):
        bp=ue.load_object(Blueprint,name.rsplit('_C',1)[0]);ue.unregister_all_mixins();parent=bp.ParentClass
        before=export(bp,str(index)+'-before');graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
        ue.blueprint_configure_mixin(bp,mixins,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or bp.ParentClass!=parent or export(bp,str(index)+'-after')!=before or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original HUD defaults/visual tree/graphs/inheritance changed: '+name)
        ue.register_declared_mixin(bp.GeneratedClass)
        try:
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!={'Python':1,'NativeFallback':1}:raise RuntimeError('Escape policy method set differs')
        finally:ue.unregister_all_mixins()
        bp.save_package();prefix='/Game/' if name.startswith('/Game/') else '/'+name.split('/')[1]+'/'
        relative=('Content/' if prefix=='/Game/' else 'Plugins/GameFeatures/'+prefix.strip('/')+'/Content/')+name[len(prefix):].split('.')[0]+'.uasset'
        assets.append(relative);proof.append(dict(target=name,profiles=counts,original_defaults_graphs_and_visual_tree_preserved=True,original_parent=parent.get_path_name()))
    mixins.save_package();assets.append('Content/UEPMixins/DA_EscapeMenuMixin.uasset')
    return dict(status='passed',assets_saved=True,assets=assets,asset_family_count=5,policy_events=1,classes=proof,native_common_ui_binding_streamed_loading_and_input_ownership_preserved=True,runtime_acceptance=False,asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(argument('UEPNativeEscapeAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_escape_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeEscapeStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_ESCAPE_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
