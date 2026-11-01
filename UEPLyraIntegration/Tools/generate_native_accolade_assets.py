"""Extend the retained host Set; its three presentation routes remain Python."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def argument(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def generate(stage,output):
    from unreal_engine.classes import Blueprint,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile,PendingAccoladeEntry
    from mixin_graph_gates import semantics
    from explorer_character_cdo import canonical_cdo
    from uep_lyra_native.accolades import CLASS
    bp=ue.load_object(Blueprint,CLASS.rsplit('_C',1)[0]);ue.unregister_all_mixins();parent=bp.ParentClass
    def export(name):
        p=output/(name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp.GeneratedClass.get_cdo(),str(p)):raise RuntimeError('Accolade CDO export failed')
        raw=p.read_bytes();return canonical_cdo(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    before=export('before');graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
    mixins=ue.load_object(UEPPythonMixinSet,'/Game/UEPMixins/DA_AccoladeHostMixin.DA_AccoladeHostMixin')
    mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.accolades',PythonClass='Accolade'+p+'Profile') for p in ('Python','NativeFallback')]
    ue.register_declared_mixin(bp.GeneratedClass)
    try:
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!={'Python':10,'NativeFallback':10}:raise RuntimeError('Accolade policy/presentation method set differs: '+str(counts))
    finally:ue.unregister_all_mixins()
    sample=PendingAccoladeEntry(SequenceID=7,bFinishedLoading=True)
    if int(sample.SequenceID)!=7 or not sample.bFinishedLoading:raise RuntimeError('Typed native sequence/completion fields unavailable')
    if bp.ParentClass!=parent or export('after')!=before or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original accolade host defaults/graphs/inheritance changed')
    mixins.save_package();assets=['Plugins/GameFeatures/ShooterCore/Content/UserInterface/Notifications/Accolades/W_AccoladeHostWidget.uasset','Content/UEPMixins/DA_AccoladeHostMixin.uasset']
    name='DT_NativeAccoladeCold';package=ue.get_or_create_package('/Game/UEPValidation/'+name)
    fixture=ue.new_object(ue.find_class('DataTable'),package,name,3);fixture.add_to_root();fixture.set_property('RowStruct',ue.find_struct('LyraAccoladeDefinitionRow'));fixture.set_property('bIgnoreMissingFields',True)
    rows=[dict(Name='Cold'+str(i),Icon='/Game/'+f.relative_to(stage/'Content').with_suffix('').as_posix()+'.'+f.stem) for i,f in enumerate(sorted((stage/'Content').rglob('T_*.uasset')))]
    if not ue.find_class('DataTableFunctionLibrary').get_cdo().call_function('FillDataTableFromJSONString',fixture,json.dumps(rows),ue.find_struct('LyraAccoladeDefinitionRow')):raise RuntimeError('Cold accolade fixture import failed')
    fixture.save_package();fixture.remove_from_root();relative='Content/UEPValidation/'+name+'.uasset'
    return dict(status='passed',assets_saved=True,assets=assets,asset_family_count=2,policy_events=7,method_counts=counts,original_defaults_graphs_and_inheritance_preserved=True,typed_sequence_and_completion_fields=True,native_registry_async_timer_ownership_preserved=True,runtime_acceptance=False,asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets},fixtures=[dict(relative=relative,sha256=hashlib.sha256((stage/relative).read_bytes()).hexdigest().upper(),stage_only=True,rows=len(rows))])


result=Path(argument('UEPNativeAccoladeAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_accolade_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeAccoladeStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_ACCOLADE_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
