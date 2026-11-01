"""Retain quickbar data and replace only the native inventory component reference."""
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback
import unreal_engine as ue


def argument(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))


def generate(stage,output):
    from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
    from unreal_engine.structs import UEPPythonMixinProfile
    from mixin_graph_gates import semantics
    definitions=[('/ShooterCore/Game/B_QuickBarComponent','Quick','LyraQuickBarComponent',3),('/Game/UEPNative/BP_InventoryManager','Inventory','LyraInventoryManagerComponent',1)]
    def export(obj,name):
        path=output/(name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(path)):raise RuntimeError('Inventory asset export failed')
        b=path.read_bytes();return b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    def retained(t):return '\n'.join(r for r in t.splitlines() if not r.strip().startswith(('PythonMixinSet=','PythonMixinProfile=')))
    assets=[];save_later=[];details=[];inventory_bp=None
    for package,prefix,parent,methods in definitions:
        bp=ue.create_blueprint(ue.find_class(parent),package) if prefix=='Inventory' else ue.load_object(Blueprint,package+'.'+package.rsplit('/',1)[-1])
        if prefix=='Inventory':ue.compile_blueprint(bp);inventory_bp=bp
        ue.unregister_all_mixins()
        if bp.ParentClass!=ue.find_class(parent):raise RuntimeError('Retained quickbar/inventory native parent differs')
        before=export(bp.GeneratedClass.get_cdo(),prefix+'-before');graphs=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,n,set()) for g,n in graphs}
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Native'+prefix+'Mixin'
        mixins=ue.create_asset(name,'/Game/UEPNative',UEPPythonMixinSet,factory);mixins.DefaultProfile='Python'
        mixins.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_native.inventory',PythonClass=prefix+p+'Profile') for p in ('Python','NativeFallback')]
        ue.blueprint_configure_mixin(bp,mixins,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or retained(export(bp.GeneratedClass.get_cdo(),prefix+'-after'))!=retained(before) or any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in graphs):raise RuntimeError('Original quickbar/inventory defaults/graphs changed')
        ue.register_declared_mixin(bp.GeneratedClass)
        try:
            row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!={'Python':methods,'NativeFallback':methods}:raise RuntimeError('Inventory policy profile method counts differ')
        finally:ue.unregister_all_mixins()
        save_later.extend((bp,mixins));assets.extend([('Plugins/GameFeatures/ShooterCore/Content/'+package[len('/ShooterCore/'):] if package.startswith('/ShooterCore/') else 'Content/'+package[len('/Game/'):])+'.uasset','Content/UEPNative/'+name+'.uasset'])
        details.append(dict(class_path=bp.GeneratedClass.get_path_name(),method_counts=counts,original_defaults_graphs_and_inheritance_preserved=True))
    gfd=ue.load_object(ue.find_class('GameFeatureData'),'/ShooterCore/ShooterCore.ShooterCore');changes=[]
    for index,action in enumerate(gfd.get_property('Actions')):
        if 'ComponentList' not in action.properties():continue
        before=export(action,'action-'+str(index)+'-before')
        matches=re.findall(r'ComponentList\((\d+)\)=.*?ComponentClass="/Script/LyraGame.LyraInventoryManagerComponent"',before)
        if not matches:continue
        if len(matches)!=1:raise RuntimeError('One native inventory class reference required')
        entries=[entry.clone() for entry in action.get_property('ComponentList')];slot=int(matches[0]);old=entries[slot]
        flags=(bool(old.bClientComponent),bool(old.bServerComponent));entries[slot].ComponentClass=inventory_bp.GeneratedClass;action.set_property('ComponentList',entries)
        after=export(action,'action-'+str(index)+'-after')
        if after!=before.replace('/Script/LyraGame.LyraInventoryManagerComponent',inventory_bp.GeneratedClass.get_path_name()):raise RuntimeError('Unrelated game feature component data changed')
        current=action.get_property('ComponentList')[slot]
        if (bool(current.bClientComponent),bool(current.bServerComponent))!=flags:raise RuntimeError('Inventory authority/client flags changed')
        changes.append(dict(action=index,slot=slot,client=flags[0],server=flags[1]))
    if len(changes)!=1:raise RuntimeError('One production inventory replacement required')
    for obj in [*save_later,gfd]:obj.save_package()
    assets.append('Plugins/GameFeatures/ShooterCore/Content/ShooterCore.uasset')
    return dict(status='passed',asset_family_count=5,assets=assets,assets_saved=True,classes=details,production_inventory_replacements=changes,
        native_selection_rpc_and_inventory_replication_preserved=True,new_policy_events=4,runtime_acceptance=False,
        asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(argument('UEPNativeInventoryAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_inventory_assets.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(argument('UEPNativeInventoryStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage,result.parent)
except Exception:report=dict(status='failed',error=traceback.format_exc(),runtime_acceptance=False)
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_INVENTORY_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
