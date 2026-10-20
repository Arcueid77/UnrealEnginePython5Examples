"""Extend accepted Explorer helper assets without editing any original graphs."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_explorer_character_assets import public_shapes,relative
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_characters.explorer_helpers_mixin import CLASSES
from uep_lyra_characters.explorer_style_mixin import METHODS

def caller(stage,bp,key):
    name='BP_Explorer'+key.title()+'StyleCallProbe';package='/Game/UEPValidation/'+name+'.'+name
    if ue.find_asset(package) is not None:
        probe=ue.load_object(Blueprint,package);ue.unregister_all_mixins();graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(probe)}
        for label,method in (('Outline','CreateOrUpdateOutlineIfNeeded'),('Team','OnTeamOrCosmeticsChanged'),('Legacy','OnRep_PlayerInfo')):
            graph=graphs[label];calls=[n for n in graph.Nodes if n.get_class().get_name()=='K2Node_CallFunction']
            if len(graph.Nodes)!=3 or len(calls)!=1 or str(calls[0].FunctionReference.MemberName)!=method:raise RuntimeError('existing owned style caller differs')
        file=stage/'Content/UEPValidation'/(name+'.uasset');return dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),reused_exact_owned_caller=True)
    probe=ue.create_blueprint(ue.find_class('Actor'),'/Game/UEPValidation/'+name)
    for name,method,parameters in (('Outline','CreateOrUpdateOutlineIfNeeded',(('TeamID','int',None),('OutlineColor','struct',ue.find_struct('LinearColor')))),('Team','OnTeamOrCosmeticsChanged',(('TeamID','int',None),('TeamDisplayAsset','object',ue.find_class('LyraTeamDisplayAsset')))),('Legacy','OnRep_PlayerInfo',())):
        graph=ue.blueprint_add_function(probe,name);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=bp.GeneratedClass),'Target');call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,method));result=graph.graph_add_node(K2Node_FunctionResult);connect(entry,'then',call,'execute');connect(entry,'Target',call,'self');connect(call,'then',result,'execute')
        for parameter,kind,obj in parameters:entry.node_create_pin(1,EdGraphPinType(PinCategory=kind,PinSubCategoryObject=obj),parameter);connect(entry,parameter,call,parameter)
    ue.compile_blueprint(probe);ue.unregister_all_mixins()
    if int(probe.Status)==2:raise RuntimeError('native Explorer style caller compile failed')
    probe.save_package();file=stage/'Content/UEPValidation'/('BP_Explorer'+key.title()+'StyleCallProbe.uasset');return dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest())

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCharacterBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'));proof=json.loads((baseline/'assets.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='explorercharacters' or not proof['original_five_helper_signatures_and_all_graphs_cdos_guids_preserved']:raise RuntimeError('accepted original Explorer helper revision required')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];characters={};fixtures=[]
    for record in parent['assets']:
        if hashlib.sha256(Path(record['stage']).read_bytes()).hexdigest().upper()!=record['sha256'].upper():raise RuntimeError('Explorer helper parent asset changed')
    for key in ('hero','pawn'):
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();before=canonical_cdo(snapshot(bp,key+'-style-before'));signatures=public_shapes(bp);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/'+name+'.'+name)
        asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_style_mixin',PythonClass='LyraExplorerStyle'+p+'Profile') for p in ('Python','BlueprintFallback')]
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(value['functions']) for p,value in row['profiles'].items()}
            if counts!=dict(Python=8,BlueprintFallback=8) or set(row['functions'])!=set(METHODS):raise RuntimeError('exact eight Explorer helper/style methods required')
        finally:ue.unregister_all_mixins()
        after=canonical_cdo(snapshot(bp,key+'-style-after'));shapes_after=public_shapes(bp)
        if before!=after or signatures!=shapes_after or any(semantics(g,ns,set())!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('Explorer style altered original CDO/ABI/graphs/GUIDs')
        (out/(key+'-style-preservation.json')).write_text(json.dumps(dict(cdo_before=before,cdo_after=after,signatures_before=signatures,signatures_after=shapes_after,graph_hashes=hashes),indent=2))
        asset.save_package();assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset']);fixtures.append(caller(stage,bp,key));characters[key]=dict(method_counts=counts,original_graphs_cdo_signatures_and_guids_unchanged=True,whole_character_migrated=False)
    return dict(status='passed',kind='explorerstyle',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,original_all_graphs_and_native_unarmed_payload_unchanged=True,only_mixin_profile_data_assets_changed=True,whole_characters_migrated=False,characters=characters,assets=assets,fixtures=fixtures)
