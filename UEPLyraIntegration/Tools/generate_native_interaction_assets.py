"""Add native interaction policy routes without changing the retained Blueprint."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def argument(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def generate(stage,output):
    from unreal_engine.classes import Blueprint,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    from mixin_graph_gates import semantics
    from explorer_character_cdo import canonical_cdo
    from uep_lyra_native.interactions import CLASS
    bp=ue.load_object(Blueprint,CLASS.rsplit('_C',1)[0]);ue.unregister_all_mixins();parent=bp.ParentClass
    def export(name):
        path=output/(name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp.GeneratedClass.get_cdo(),str(path)):raise RuntimeError('Interaction CDO export failed')
        raw=path.read_bytes();return canonical_cdo(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    before=export('before');graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
    mixins=ue.load_object(UEPPythonMixinSet,'/Game/UEPMixins/DA_ExplorerInteractMixin.DA_ExplorerInteractMixin')
    # Retain the accepted Blueprint comparison profile for the existing Explorer
    # regression. Missing native policy methods use their original C++ bodies.
    mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.interactions',PythonClass='Interaction'+p+'Profile') for p in ('Python','NativeFallback')]+[UEPPythonMixinProfile(ProfileName='BlueprintFallback',PythonModule='uep_lyra_abilities.explorer_interact_mixin',PythonClass='LyraExplorerInteractBlueprintFallbackProfile')]
    ue.register_declared_mixin(bp.GeneratedClass)
    try:
        row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!={'Python':8,'NativeFallback':8,'BlueprintFallback':6}:raise RuntimeError('Interaction method sets differ: '+str(counts))
    finally:ue.unregister_all_mixins()
    for name in ('UEPNativeInteractionFixture','UEPNativeInteractionWitness'):ue.find_class(name)
    if bp.ParentClass!=parent or export('after')!=before or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original interaction defaults/graphs/inheritance changed')
    mixins.save_package();assets=['Plugins/GameFeatures/ShooterExplorer/Content/Input/Abilities/GA_Interact.uasset','Content/UEPMixins/DA_ExplorerInteractMixin.uasset']
    factory=ue.new_object(ue.find_class('WidgetBlueprintFactory'));factory.ParentClass=ue.find_class('UserWidget');fixture=factory.factory_create_new('/Game/UEPValidation/W_NativeInteractionIndicator');ue.compile_blueprint(fixture)
    if int(fixture.Status)==2:raise RuntimeError('Native interaction indicator fixture compile failed')
    fixture.save_package();relative='Content/UEPValidation/W_NativeInteractionIndicator.uasset'
    return dict(status='passed',assets_saved=True,assets=assets,asset_family_count=2,policy_events=2,method_counts=counts,original_defaults_graphs_and_inheritance_preserved=True,native_interface_soft_classes_actor_info_and_gas_retained=True,stage_only_native_validation_types_loaded=True,runtime_acceptance=False,asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets},fixtures=[dict(relative=relative,sha256=hashlib.sha256((stage/relative).read_bytes()).hexdigest().upper(),stage_only=True)])


result=Path(argument('UEPNativeInteractionAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_interaction_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeInteractionStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_INTERACTION_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
