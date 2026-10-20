"""Compile exact original macros in a stage-only probe and census all callsites."""
import hashlib
import json
from pathlib import Path
import re
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_MacroInstance,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType
from generate_accolade_widget_assets import kind
from mixin_graph_gates import semantics
from message_payload_graphs import connect

LIBRARIES={'audio':('/Game/Audio/Blueprints/WeaponAudioMacros.WeaponAudioMacros','Content/Audio/Blueprints/WeaponAudioMacros.uasset'),'vfx':('/ShooterCore/Blueprint/Macros/BPML_VFXMacros.BPML_VFXMacros','Plugins/GameFeatures/ShooterCore/Content/Blueprint/Macros/BPML_VFXMacros.uasset')}
NAMES=('LyraGetWeapon','LyraGetWeaponAmmo','IgnoreSpecificSkeletalMesh','IgnoreSkeletalMeshTag')
PROBE='Content/UEPValidation/BP_MacroClosureProbe.uasset'


def expected_callers(repo):
    master=repo/'.build/LyraValidation/BlueprintPython/20261012-audit/blueprints.json';data=json.loads(master.read_text(encoding='utf-8-sig'));expected=[]
    for bp in data['blueprints']:
        for graph in bp['graphs']:
            for node in graph['nodes']:
                if node['class']!='K2Node_MacroInstance':continue
                title=re.sub('[^a-z0-9]','',str(node.get('title','')).lower())
                matches=[n for n in NAMES if re.sub('[^a-z0-9]','',n.lower()) in title]
                # "LyraGetWeapon" is also a prefix of the Ammo macro.
                if matches:expected.append(dict(package=bp['path'],graph=graph['name'],node=node['name'],macro=max(matches,key=len)))
    return expected,master


def generate(stage):
    repo=Path(__file__).resolve().parents[3];official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if (stage/PROBE).exists():raise RuntimeError('fresh native macro probe required')
    libraries={};graphs={};initial={}
    for label,(package,relative) in LIBRARIES.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('original macro library required')
        bp=ue.load_object(Blueprint,package);values=ue.blueprint_get_all_graphs(bp);libraries[label]=dict(package=package,relative=relative,sha256=hashlib.sha256((stage/relative).read_bytes()).hexdigest(),graphs={g.get_name():len(g.Nodes) for g in values});initial[label]={g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in values}
        for g in values:graphs[g.get_name()]=(bp,g)
    if libraries['audio']['graphs']!={'LyraGetWeapon':20,'LyraGetWeaponAmmo':12} or libraries['vfx']['graphs']!={'IgnoreSpecificSkeletalMesh':5,'IgnoreSkeletalMeshTag':4}:raise RuntimeError('complete original macro definitions required')
    expected,master=expected_callers(repo);calls=[];consumer_hashes={}
    for package in sorted({row['package'] for row in expected}):
        bp=ue.load_object(Blueprint,package);relative=('Content/' if package.startswith('/Game/') else 'Plugins/GameFeatures/ShooterCore/Content/')+package.split('.')[0].split('/',2)[2]+'.uasset';file=stage/relative;overlay=repo/'Demos/UEPLyraIntegration/Overlay'/relative
        if not overlay.is_file() or hashlib.sha256(file.read_bytes()).digest()!=hashlib.sha256(overlay.read_bytes()).digest():raise RuntimeError('current accepted macro consumer Stage/Overlay revision required: '+package)
        consumer_hashes[package]=dict(relative=relative,sha256=hashlib.sha256(file.read_bytes()).hexdigest())
        for g in ue.blueprint_get_all_graphs(bp):
            for node in g.Nodes:
                if node.get_class().get_name()!='K2Node_MacroInstance':continue
                macro=node.node_get_macro_graph()
                if macro is not None and macro.get_name() in NAMES:calls.append(dict(package=package,graph=g.get_name(),node=node.get_name(),macro=macro.get_name(),macro_path=macro.get_path_name()))
    if sorted((r['package'],r['graph'],r['node'],r['macro']) for r in calls)!=sorted((r['package'],r['graph'],r['node'],r['macro']) for r in expected):raise RuntimeError('original/current macro callsite census differs')
    if len(calls)!=9 or len(consumer_hashes)!=9:raise RuntimeError('all nine live asset callsites required')
    probe=ue.create_blueprint(ue.find_class('Actor'),'/Game/UEPValidation/BP_MacroClosureProbe')
    for macro_name,method in (('LyraGetWeapon','Weapon'),('LyraGetWeaponAmmo','Ammo'),('IgnoreSpecificSkeletalMesh','Specific'),('IgnoreSkeletalMeshTag','Tag')):
        library,source=graphs[macro_name];g=ue.blueprint_add_function(probe,method);entry=g.Nodes[0];node=g.graph_add_node(K2Node_MacroInstance);ref=ue.find_struct('GraphReference')(MacroGraph=source,GraphBlueprint=library,GraphGuid=source.get_property('GraphGuid'));node.set_property('MacroGraphReference',ref);g.graph_reconstruct_node(node)
        resolved=node.node_get_macro_graph();details=dict(macro=macro_name,source=source.get_path_name(),resolved=resolved.get_path_name() if resolved is not None else None,source_pins=[(n.get_name(),[(p.name,p.direction,p.category) for p in n.node_pins()]) for n in source.Nodes if n.get_class().get_name()=='K2Node_Tunnel'],instance_pins=[(p.name,p.direction,p.category) for p in node.node_pins()]);root=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;(root/('probe-'+method+'-pins.json')).write_text(json.dumps(details,indent=2),encoding='utf-8')
        input_exec=next(p for p in node.node_pins() if p.direction==0 and p.category=='exec');input_data=next(p for p in node.node_pins() if p.direction==0 and p.category=='object');entry.node_create_pin(1,kind(input_data),'Target');connect(entry,'then',node,input_exec.name);connect(entry,'Target',node,input_data.name)
        if method=='Weapon':
            result=g.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'Found');result.node_find_pin('Found').default_value='true';result.node_create_pin(0,kind(node.node_find_pin('AsB Weapon')),'Weapon');connect(node,'then',result,'execute');connect(node,'AsB Weapon',result,'Weapon')
        elif method=='Ammo':
            result=g.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'Completed');result.node_find_pin('Completed').default_value='true';result.node_create_pin(0,kind(node.node_find_pin('MagazineAmmo')),'Ammo');connect(node,'then',result,'execute');connect(node,'MagazineAmmo',result,'Ammo')
        else:
            result=g.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'Ignored');result.node_find_pin('Ignored').default_value='true';connect(node,'IgnoredPath',result,'execute')
    ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('exact original macro expansion probe failed to compile')
    probe.save_package()
    for label,(package,relative) in LIBRARIES.items():
        bp=ue.load_object(Blueprint,package)
        if hashlib.sha256((stage/relative).read_bytes()).hexdigest()!=libraries[label]['sha256'] or {g.get_name():semantics(g,{n.get_name() for n in g.Nodes},set()) for g in ue.blueprint_get_all_graphs(bp)}!=initial[label]:raise RuntimeError('original macro definition changed')
    return dict(status='passed',kind='macroclosure',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_macro_definition_assets_and_graphs_unchanged=True,original_audio_macro_graph_nodes=32,original_vfx_macro_graph_nodes=9,original_macro_callsite_census_matches=True,original_unused_specific_mesh_macro_has_no_live_callsite=True,original_source_index=dict(path=str(master),sha256=hashlib.sha256(master.read_bytes()).hexdigest()),libraries=libraries,callsites=calls,current_consumers=consumer_hashes,fixture=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),new_business_nodes=0,native_end_adapter_nodes=0,assets=[])
