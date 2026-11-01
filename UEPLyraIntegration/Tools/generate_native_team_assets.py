"""Retain the two/four-team Blueprint configurations and bind native policy events."""
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
    from uep_lyra_native.team_creation import CLASSES
    def export(obj,name):
        path=output/(name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(path)):raise RuntimeError('Team default export failed')
        data=path.read_bytes();return data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    def retained(text):return '\n'.join(row for row in text.splitlines() if not row.strip().startswith(('PythonMixinProfile=','PythonMixinSet=')))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    if (stage/'Content/UEPNative/DA_NativeTeamCreationMixin.uasset').is_file():
        mixins=ue.load_object(UEPPythonMixinSet,'/Game/UEPNative/DA_NativeTeamCreationMixin.DA_NativeTeamCreationMixin')
    else:mixins=ue.create_asset('DA_NativeTeamCreationMixin','/Game/UEPNative',UEPPythonMixinSet,factory)
    mixins.DefaultProfile='Python';mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.team_creation',PythonClass='Team'+p+'Profile') for p in ('Python','NativeFallback')]
    assets=['Content/UEPNative/DA_NativeTeamCreationMixin.uasset'];details=[];save_later=[mixins]
    for index,path in enumerate(CLASSES):
        bp=ue.load_object(Blueprint,path.rsplit('_C',1)[0]);ue.unregister_all_mixins()
        if bp.ParentClass!=ue.find_class('LyraTeamCreationComponent'):raise RuntimeError('Original team native parent differs')
        before=export(bp.GeneratedClass.get_cdo(),str(index)+'-before')
        graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
        hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
        original_teams={int(k):v.get_path_name() if v is not None else None for k,v in bp.GeneratedClass.get_cdo().get_property('TeamsToCreate').items()}
        ue.blueprint_configure_mixin(bp,mixins,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('Native team Blueprint compilation failed')
        after=export(bp.GeneratedClass.get_cdo(),str(index)+'-after')
        if retained(before)!=retained(after) or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original team configuration/graphs changed')
        ue.register_declared_mixin(bp.GeneratedClass)
        try:
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass]
            counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!={'Python':2,'NativeFallback':2}:raise RuntimeError('Native team profile registration differs')
        finally:ue.unregister_all_mixins()
        mount=path.split('/')[1];package=path.split('.')[0]
        relative='Plugins/GameFeatures/'+mount+'/Content/'+package[len(mount)+2:]+'.uasset'
        assets.append(relative);save_later.append(bp)
        details.append(dict(class_path=path,original_defaults_preserved=True,original_graphs_preserved=True,teams=original_teams,method_counts=counts))
    for asset in save_later:asset.save_package()
    signatures={name:ue.describe_function(ue.find_class('LyraTeamCreationComponent'),name) for name in ('UEPChooseTeamForPlayer','UEPGetLeastPopulatedTeamID','UEPSetPlayerTeam')}
    return dict(status='passed',event_entrypoints=2,native_setter_adapters=1,signatures=signatures,asset_family_count=3,assets=assets,
        asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets},classes=details,assets_saved=True,runtime_acceptance=False)


result=Path(argument('UEPNativeTeamAssetsResult'));stage=Path(argument('UEPNativeTeamStageRoot')).resolve()
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_team_assets.py'))).resolve()
    sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    require_authoring_stage(str(stage),ue.convert_relative_path_to_full(ue.get_content_dir()))
    report=generate(stage,result.parent)
except Exception:
    report=dict(status='failed',error=traceback.format_exc());ue.log_error(report['error'])
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_TEAM_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
