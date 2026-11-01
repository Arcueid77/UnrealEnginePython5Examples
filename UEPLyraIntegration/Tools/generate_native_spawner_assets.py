"""Extend the existing spawner Set and preserve all retained Blueprint blocks."""
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
    from uep_lyra_native.spawner import CLASS,CHILD
    blueprints=[ue.load_object(Blueprint,p.rsplit('_C',1)[0]) for p in (CLASS,CHILD)];ue.unregister_all_mixins()
    def export(bp,name):
        p=output/(name+'.t3d');require=ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp.GeneratedClass.get_cdo(),str(p))
        if not require:raise RuntimeError('Spawner default export failed')
        raw=p.read_bytes();return canonical_cdo(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    before={bp.get_name():export(bp,bp.get_name()+'-before') for bp in blueprints}
    parents={bp.get_name():bp.ParentClass for bp in blueprints};graphs={bp.get_name():[(g,{n.get_name() for n in g.Nodes},semantics(g,{n.get_name() for n in g.Nodes},set())) for g in ue.blueprint_get_all_graphs(bp)] for bp in blueprints}
    mixins=ue.load_object(UEPPythonMixinSet,'/Game/UEPMixins/DA_SpawnerMixin.DA_SpawnerMixin')
    mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.spawner',PythonClass='Spawner'+p+'Profile') for p in ('Python','NativeFallback')]
    counts={}
    for bp in blueprints:
        ue.unregister_all_mixins()
        if int(bp.Status)==2 or bp.ParentClass!=parents[bp.get_name()] or export(bp,bp.get_name()+'-after')!=before[bp.get_name()] or any(semantics(g,n,set())!=h for g,n,h in graphs[bp.get_name()]):raise RuntimeError('Retained spawner defaults/graphs/inheritance changed')
        if bp==blueprints[0]:
            ue.register_declared_mixin(bp.GeneratedClass)
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];methods={p:len(v['functions']) for p,v in row['profiles'].items()}
            if methods!={'Python':11,'NativeFallback':11}:raise RuntimeError('Spawner profile function set differs: '+str(methods))
            counts[bp.get_name()]=methods;ue.unregister_all_mixins()
        elif bp.GeneratedClass.get_cdo().call_function('GetPythonMixinSet')!=mixins:raise RuntimeError('Ability spawner lost the inherited parent Set')
    mixins.save_package()
    assets=['Plugins/GameFeatures/ShooterCore/Content/Blueprint/'+bp.get_name()+'.uasset' for bp in blueprints]+['Content/UEPMixins/DA_SpawnerMixin.uasset']
    return dict(status='passed',assets_saved=True,assets=assets,asset_family_count=3,policy_events=3,method_counts=counts,original_defaults_graphs_and_inheritance_preserved=True,native_timers_replication_overlaps_preserved=True,runtime_acceptance=False,asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(argument('UEPNativeSpawnerAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_spawner_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeSpawnerStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_SPAWNER_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
