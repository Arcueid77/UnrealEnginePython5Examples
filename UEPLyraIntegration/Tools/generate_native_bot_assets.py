"""Inspect retained bot classes before configuring their native policy routes."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def argument(name):return next((v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'=')),None)


def inspect(stage,output):
    from unreal_engine.classes import Blueprint
    from uep_lyra_native.bot_creation import CLASSES
    rows=[]
    for index,path in enumerate(CLASSES):
        bp=ue.load_object(Blueprint,path.rsplit('_C',1)[0])
        if not bp.GeneratedClass.get_cdo().is_a(ue.find_class('LyraBotCreationComponent')):raise RuntimeError('Wrong native bot family')
        graphs=[]
        for graph in ue.blueprint_get_all_graphs(bp):
            nodes=[]
            for node in graph.Nodes:
                row=dict(name=node.get_name(),cls=node.get_class().get_name())
                if 'FunctionReference' in node.properties():row['function']=str(node.get_property('FunctionReference').MemberName)
                if 'EventReference' in node.properties():row['event']=str(node.get_property('EventReference').MemberName)
                if 'CustomFunctionName' in node.properties():row['custom']=str(node.get_property('CustomFunctionName'))
                nodes.append(row)
            graphs.append(dict(name=graph.get_name(),nodes=nodes))
        p=output/(str(index)+'-original.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp,str(p)):raise RuntimeError('Bot Blueprint export failed')
        default=bp.GeneratedClass.get_cdo()
        rows.append(dict(class_path=path,parent=bp.ParentClass.get_path_name(),graphs=graphs,default_count=int(default.get_property('NumBotsToCreate')),
            bot_controller=default.get_property('BotControllerClass').get_path_name() if default.get_property('BotControllerClass') is not None else None,
            names=list(default.get_property('RandomBotNames'))))
    return dict(status='passed',inspect_only=True,classes=rows,runtime_acceptance=False)


def generate(stage,output):
    from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    from mixin_graph_gates import semantics
    baseline=inspect(stage,output)
    # Existing Blueprint overrides need explicit review before replacing their
    # native parent event's body. Inspection is deliberately separate.
    for row in baseline['classes']:
        if any(g['name']=='ServerCreateBots' or any(n.get('event')=='ServerCreateBots' for n in g['nodes']) for g in row['graphs']):raise RuntimeError('Review existing ServerCreateBots Blueprint override before authoring: '+row['class_path'])
    excluded=stage/'Plugins/GameFeatures/ShooterCore/Content/Bot/B_ShooterBotSpawner_Perf.uasset'
    excluded_hash=hashlib.sha256(excluded.read_bytes()).hexdigest().upper()
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet
    mixins=ue.create_asset('DA_NativeBotCreationMixin','/Game/UEPNative',UEPPythonMixinSet,factory)
    mixins.DefaultProfile='Python';mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.bot_creation',PythonClass='Bot'+p+'Profile') for p in ('Python','NativeFallback')]
    assets=['Content/UEPNative/DA_NativeBotCreationMixin.uasset'];save_later=[mixins];details=[]
    for index,row in enumerate(baseline['classes']):
        bp=ue.load_object(Blueprint,row['class_path'].rsplit('_C',1)[0]);ue.unregister_all_mixins();parent=bp.ParentClass
        def export(name):
            p=output/(str(index)+'-'+name+'.t3d')
            if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(bp.GeneratedClass.get_cdo(),str(p)):raise RuntimeError('Bot CDO export failed')
            b=p.read_bytes();t=b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
            return '\n'.join(r for r in t.splitlines() if not r.strip().startswith(('PythonMixinProfile=','PythonMixinSet=')))
        before=export('before');graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
        ue.blueprint_configure_mixin(bp,mixins,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or bp.ParentClass!=parent or export('after')!=before or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Retained bot class configuration, graph or inheritance changed')
        ue.register_declared_mixin(bp.GeneratedClass)
        try:
            registered,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in registered['profiles'].items()}
            if counts!={'Python':4,'NativeFallback':4}:raise RuntimeError('Bot policy profile method counts differ')
        finally:ue.unregister_all_mixins()
        assets.append('Plugins/GameFeatures/ShooterCore/Content/'+row['class_path'].split('.')[0][len('/ShooterCore/'):]+'.uasset');save_later.append(bp)
        details.append(dict(class_path=row['class_path'],method_counts=counts,original_defaults_graphs_and_inheritance_preserved=True))
    for obj in save_later:obj.save_package()
    if hashlib.sha256(excluded.read_bytes()).hexdigest().upper()!=excluded_hash:raise RuntimeError('Retained performance test class changed')
    return dict(status='passed',asset_family_count=3,assets=assets,assets_saved=True,classes=details,new_policy_events=2,existing_native_event='ServerCreateBots',runtime_acceptance=False,
        retained_performance_test=dict(path=str(excluded),sha256=excluded_hash,reason='Original Blueprint scope excludes this performance test; retain its custom ServerCreateBots graph and native fallback.'),
        asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(argument('UEPNativeBotAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_bot_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeBotStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()))
    report=inspect(stage,result.parent) if '-UEPNativeBotInspectOnly' in sys.argv else generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_BOT_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
