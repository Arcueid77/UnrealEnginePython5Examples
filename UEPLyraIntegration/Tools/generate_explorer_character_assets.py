"""Keep whole original characters; route only the five audited helper methods."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from generate_message_widget_assets import move_node
from generate_character_inventory_assets import input_bindings
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_characters.explorer_helpers_mixin import CLASSES,METHODS,UNARMED

def relative(key):return 'Plugins/GameFeatures/ShooterExplorer/Content/Blueprint/'+CLASSES[key].split('/')[-1].split('.')[0]+'.uasset'
def public_shapes(bp):
    names={'UserConstructionScript','ChangeQuickbarSlot','AddInitialInventory','ClearInventory','CreateOrUpdateOutlineIfNeeded','OnRep_PlayerInfo','OnTeamOrCosmeticsChanged','GetEmoteAudioComponent','ReceivePossessed','ReceiveBeginPlay','SetEmoteAudioComponent','K2_OnReset','K2_OnDeathFinished'}
    if bp.get_name()=='B_Hero_Explorer':names.add('AnimMotionEffect')
    else:names.add('UseBehaviorTree')
    return {n:ue.describe_function(bp.GeneratedClass,n) for n in names}

def caller(stage,bp,key):
    name='BP_Explorer'+key.title()+'HelpersCallProbe';probe=ue.create_blueprint(ue.find_class('Actor'),'/Game/UEPValidation/'+name)
    actor=EdGraphPinType(PinCategory='object',PinSubCategoryObject=bp.GeneratedClass)
    for label,method in (('Grant','AddInitialInventory'),('Clear','ClearInventory'),('Slot','ChangeQuickbarSlot'),('SetAudio','SetEmoteAudioComponent'),('GetAudio','GetEmoteAudioComponent')):
        graph=ue.blueprint_add_function(probe,label);entry=graph.Nodes[0];entry.node_create_pin(1,actor,'Target');call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,method));result=graph.graph_add_node(K2Node_FunctionResult);connect(entry,'Target',call,'self')
        if label=='GetAudio':
            result.node_create_pin(0,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('AudioComponent')),'ReturnValue');connect(call,'AudioComponent',result,'ReturnValue');connect(entry,'then',call,'execute');connect(call,'then',result,'execute')
        else:
            connect(entry,'then',call,'execute');connect(call,'then',result,'execute')
            for parameter,kind,obj in ((('NewSlotIndex','int',None),('SlotActionTag','struct',ue.find_struct('GameplayTag'))) if label=='Slot' else (('AudioComponent','object',ue.find_class('AudioComponent')), ) if label=='SetAudio' else ()):
                entry.node_create_pin(1,EdGraphPinType(PinCategory=kind,PinSubCategoryObject=obj),parameter);connect(entry,parameter,call,parameter)
    ue.compile_blueprint(probe);ue.unregister_all_mixins()
    if int(probe.Status)==2:raise RuntimeError('native Explorer helper caller compile failed')
    probe.save_package();file=stage/'Content/UEPValidation'/(name+'.uasset');return dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),package='/Game/UEPValidation/'+name+'.'+name+'_C')

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];reports={};pending=[]
    for key,total in (('hero',193),('pawn',212)):
        if hashlib.sha256((stage/relative(key)).read_bytes()).digest()!=hashlib.sha256((official/relative(key)).read_bytes()).digest():raise RuntimeError('fresh original Explorer character required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();before=canonical_cdo(snapshot(bp,key+'-explorer-character-before'));signatures=public_shapes(bp);bindings=input_bindings(bp.GeneratedClass);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)]
        if sum(len(ns) for _,ns in originals)!=total:raise RuntimeError('original Explorer footprint differs')
        graph=next(g for g,_ in originals if g.get_name()=='AddInitialInventory');nodes={n.get_name():n for n in graph.Nodes};moved={'K2Node_CallFunction_2','K2Node_VariableGet_5'};branch=nodes['K2Node_IfThenElse_0'];link,=branch.node_find_pin('else').get_linked_to()
        if link.owning_node!=nodes['K2Node_CallFunction_2'] or str(nodes['K2Node_CallFunction_2'].FunctionReference.MemberName)!='LinkAnimClassLayers':raise RuntimeError('original Explorer empty-loadout layer branch required')
        ignored={(branch.get_name(),'else')};hashes={g.get_name():semantics(g,ns-(moved if g==graph else set()),ignored if g==graph else set()) for g,ns in originals};native=semantics(graph,moved,set());guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        helper=ue.blueprint_add_function(bp,UNARMED);entry=helper.Nodes[0];result=helper.graph_add_node(K2Node_FunctionResult)
        for name in moved:move_node(graph,helper,nodes[name])
        connect(entry,'then',nodes['K2Node_CallFunction_2'],'execute');connect(nodes['K2Node_VariableGet_5'],'Mesh',nodes['K2Node_CallFunction_2'],'self');connect(nodes['K2Node_CallFunction_2'],'then',result,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,UNARMED));connect(branch,'else',call,'execute')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_helpers_mixin',PythonClass='LyraExplorerHelpers'+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after=public_shapes(bp);new_bindings=input_bindings(bp.GeneratedClass)
        cdo_after=canonical_cdo(snapshot(bp,key+'-explorer-character-after'))
        (out/(key+'-character-signatures.json')).write_text(json.dumps(dict(before=signatures,after=after,inputs_before=bindings,inputs_after=new_bindings,cdo_before=before,cdo_after=cdo_after),indent=2))
        if int(bp.Status)==2 or cdo_after!=before or signatures!=after or sorted((x['action'],x['trigger']) for x in bindings)!=sorted((x['action'],x['trigger']) for x in new_bindings):raise RuntimeError('original Explorer CDO/signature/input binding semantics changed')
        if any(semantics(g,ns-(moved if g==graph else set()),ignored if g==graph else set())!=hashes[g.get_name()] for g,ns in originals) or semantics(helper,moved,set())!=native or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('original Explorer graph partitions/GUIDs changed')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict(Python=5,BlueprintFallback=5) or set(row['functions'])!=set(METHODS):raise RuntimeError('exact five Explorer helpers required')
        finally:ue.unregister_all_mixins()
        interfaces=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interfaces
        if interfaces!=5 or transport!=3:raise RuntimeError('Explorer helper transport footprint changed')
        reports[key]=dict(original_nodes=total,transport_nodes=transport,interface_nodes=interfaces,method_counts=counts,original_cdo_signatures_graph_partitions_guids_and_input_semantics_preserved=True,original_native_unarmed_class_and_mesh_payload_preserved=True,whole_character_migrated=False)
        pending.extend([bp,asset]);assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset'])
    for obj in pending:obj.save_package()
    fixtures=[caller(stage,pending[i*2],key) for i,key in enumerate(('hero','pawn'))]
    return dict(status='passed',kind='explorercharacters',runtime_acceptance=False,full_acceptance=False,new_business_nodes=0,native_end_adapter_nodes=0,whole_characters_migrated=False,original_class_defaults_signature_graphs_preserved=True,original_five_helper_signatures_and_all_graphs_cdos_guids_preserved=True,original_native_empty_loadout_unarmed_layer_payload_preserved=True,characters=reports,assets=assets,fixtures=fixtures)
