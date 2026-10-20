"""Add exact named-delegate transports and one native int-linkage resume stub."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from generate_explorer_character_assets import public_shapes,relative
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_characters.explorer_helpers_mixin import CLASSES
from uep_lyra_characters.explorer_callbacks_mixin import METHODS as PREVIOUS_METHODS,PARTS_EVENT,HEALTH_EVENT
from uep_lyra_characters.explorer_init_mixin import resolve,TEAM_BIND,EXPERIENCE_BIND
from uep_lyra_characters.inventory_wait_mixin import RESUME

def bind(bp,name,cls,event,callback):
    graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Observer');call=graph.graph_add_node(K2Node_AddDelegate);call.DelegateReference=MemberReference(MemberName=event,MemberParent=cls,bSelfContext=False);graph.graph_reconstruct_node(call);delegate=graph.graph_add_node(K2Node_CreateDelegate);owner=graph.graph_add_node(K2Node_Self);connect(entry,'Observer',call,'self');connect(entry,'then',call,'execute');connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',call,'Delegate');delegate.SelectedFunctionName=callback
    if len(graph.Nodes)!=4:raise RuntimeError('named-delegate transport footprint differs')
    return dict(function=name,nodes=4,delegate=event,callback=callback,python_callback_retained=False)

def shapes(bp,names):
    result=public_shapes(bp)
    for name in (PARTS_EVENT,HEALTH_EVENT,*names.values()):result[name]=ue.describe_function(bp.GeneratedClass,name)
    return result

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCharacterBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='explorercallbacks':raise RuntimeError('accepted twelve-method Explorer callback baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('Explorer callback parent changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];reports={};pending=[]
    for key in CLASSES:
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();callbacks={k:resolve(bp.GeneratedClass,k) for k in ('team','experience')};before=canonical_cdo(snapshot(bp,key+'-init-before'));signatures=shapes(bp,callbacks);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        transports=[bind(bp,TEAM_BIND,ue.find_class('AsyncAction_ObserveTeamColors'),'OnTeamChanged',callbacks['team']),bind(bp,EXPERIENCE_BIND,ue.find_class('AsyncAction_ExperienceReady'),'OnReady',callbacks['experience'])];graph=ue.blueprint_add_function(bp,RESUME);entry=graph.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='int'),'Linkage');result=graph.graph_add_node(K2Node_FunctionResult);connect(entry,'then',result,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        new_callbacks={k:resolve(bp.GeneratedClass,k) for k in callbacks}
        if callbacks!=new_callbacks:raise RuntimeError('original async symbols changed while declaring native transports')
        name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/'+name+'.'+name);asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_init_mixin',PythonClass='LyraExplorerInit'+key.title()+p+'Profile') for p in ('Python','BlueprintFallback')]
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()};expected=set(PREVIOUS_METHODS)|{'ListenForTeam','ReceivePossessed',callbacks['team'],callbacks['experience'],RESUME}
            if counts!=dict(Python=17,BlueprintFallback=17) or set(row['functions'])!=expected:raise RuntimeError('complete seventeen-method Explorer init family required')
        finally:ue.unregister_all_mixins()
        after=canonical_cdo(snapshot(bp,key+'-init-after'));after_shapes=shapes(bp,callbacks)
        if int(bp.Status)==2 or before!=after or signatures!=after_shapes or any(semantics(g,ns,set())!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('Explorer init changed original CDO/ABI/graphs/GUIDs')
        added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-sum(len(ns) for _,ns in originals)
        if added!=10:raise RuntimeError('Explorer init transport footprint differs')
        (out/(key+'-init-preservation.json')).write_text(json.dumps(dict(cdo_before=before,cdo_after=after,signatures_before=signatures,signatures_after=after_shapes,original_graph_hashes=hashes,callbacks=callbacks),indent=2));reports[key]=dict(method_counts=counts,transport_nodes_added=added,callbacks=callbacks,named_transports=transports,original_cdo_public_signatures_graphs_guids_and_async_symbols_preserved=True);assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset']);pending.extend([bp,asset])
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='explorerinit',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,original_all_graphs_guids_async_factories_and_callbacks_preserved=True,native_named_delegate_binding_and_latent_resume_only=True,whole_characters_migrated=False,characters=reports,assets=assets)
