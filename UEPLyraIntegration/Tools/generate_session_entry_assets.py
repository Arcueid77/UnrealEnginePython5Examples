"""Preserve exact native localized row payloads, loading macro and join teardown."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.session_entry_mixin import CLASS,METHODS,GATES,NATIVE
ASSET='Content/UI/Menu/Experiences/W_SessionBrowserEntry.uasset'
MACRO='Content/UI/Menu/Experiences/UIExperienceMacros.uasset'
def gate(bp,key,params):
    graph=ue.blueprint_add_function(bp,GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/ASSET).read_bytes()).digest()!=hashlib.sha256((official/ASSET).read_bytes()).digest():raise RuntimeError('fresh original session entry required')
    macro_hash=hashlib.sha256((stage/MACRO).read_bytes()).hexdigest();ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'session-entry-before');tree=visuals(bp,out,'session-entry-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(ns) for _,ns in originals)
    if total!=62:raise RuntimeError('original session entry footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};definition=nodes['K2Node_DynamicCast_2'].node_find_pin('AsLyra User Facing Experience Definition')
    points=[(nodes[name],pin,key,params) for name,pin,key,params in (('K2Node_Event_0','then','item',(('ListItemObject',nodes['K2Node_Event_0'].node_find_pin('ListItemObject')),)),('K2Node_DynamicCast_2','then','display_ready',(('Experience',definition),)),('K2Node_CallFunction_5','then','image',(('Experience',definition),)),('K2Node_ComponentBoundEvent_0','then','click',()),('K2Node_CustomEvent_2','then','join',()),('K2Node_AsyncAction_0','AfterPush','spinner',(('Widget',nodes['K2Node_AsyncAction_0'].node_find_pin('UserWidget')),)),('K2Node_MacroInstance_1','then','prepared',()),('K2Node_CallFunction_8','then','completed',(('Succeeded',nodes['K2Node_BreakStruct_0'].node_find_pin('bWasSuccessful')),)))]
    methods={'OnListItemObjectSet','OnJoinCompleted','JoinSession',str(nodes['K2Node_ComponentBoundEvent_0'].CustomFunctionName)};signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
    for node,pin,_,_ in points:
        target,=node.node_find_pin(pin).get_linked_to();ignored[event.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
    for _,_,key,params in points:gate(bp,key,params)
    for key,target in (('display_load','K2Node_CallFunction_21'),('texts','K2Node_CallFunction_5'),('spinner','K2Node_AsyncAction_0'),('prepare_load','K2Node_CallFunction_18'),('submit','K2Node_AddDelegate_0'),('failure','K2Node_CallFunction_7')):
        alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for node,pin,key,params in points:
        previous={n.get_name() for n in event.Nodes};insert_gate(event,node,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in event.Nodes if n.get_name() not in previous and n.get_class().get_name()=='K2Node_CallFunction']
        for name,p in params:p.make_link_to(call.node_find_pin(name))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_SessionEntryMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.session_entry_mixin',PythonClass='LyraSessionEntry'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};(out/'session-entry-public-signatures.json').write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
    if int(bp.Status)==2 or signatures!=after or snapshot(bp,'session-entry-after')!=before or visuals(bp,out,'session-entry-after')!=tree:raise RuntimeError('session entry CDO/tree/animation/public ABI changed')
    if any(semantics(g,ns,ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('session entry original graph/GUID changed')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
    if interface!=5 or transport!=38:raise RuntimeError('session entry transport differs: '+str(transport))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS)):raise RuntimeError('complete entry Profile family required')
    finally:ue.unregister_all_mixins()
    if hashlib.sha256((stage/MACRO).read_bytes()).hexdigest()!=macro_hash:raise RuntimeError('shared loading macro changed')
    bp.save_package();asset.save_package();return dict(status='passed',kind='sessionentry',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_tree_animations_public_signatures_guids_and_graphs_preserved=True,original_native_five_text_payload_and_unwired_mapname_string_preserved=True,original_primary_load_and_spinner_loading_macro_order_preserved=True,original_join_binding_and_unbind_then_pop_before_bool_gate_preserved=True,original_failure_ftext_system_message_preserved=True,shared_macro_definition_unchanged=True,shared_macro_sha256=macro_hash,original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,assets=[ASSET,'Content/UEPMixins/'+name+'.uasset'])
