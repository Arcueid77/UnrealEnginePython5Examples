"""Preserve original StateTree event ABI,native AI move tasks and delay UUIDs."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.explorer_state_mixin import CLASSES,METHODS,GATES,NATIVE
def relative(kind):return 'Plugins/GameFeatures/ShooterExplorer/Content/'+('AI/StateTrees/Evaluators/EV_PlayerPosition.uasset' if kind=='eval' else 'AI/StateTrees/Tasks/'+CLASSES[kind].split('/')[-1].split('.')[0]+'.uasset')
def gate(bp,name):
    graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};pending=[];assets=[]
    for kind,total,transport in (('eval',4,7),('location',4,7),('follow',8,13),('goto',9,13),('delay',20,18)):
        asset_path=relative(kind)
        if hashlib.sha256((stage/asset_path).read_bytes()).digest()!=hashlib.sha256((official/asset_path).read_bytes()).digest():raise RuntimeError('fresh original Explorer StateTree nodes required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[kind].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,kind+'-explorer-state-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
        if sum(len(ns) for _,ns in originals)!=total:raise RuntimeError('original StateTree node footprint differs: '+kind)
        if kind in ('eval','location'):
            entry=nodes['K2Node_Event_'+('0' if kind=='eval' else '1')];points=[(entry,'then','tick')];moved={'K2Node_CallFunction_0','K2Node_CallFunction_'+('2' if kind=='eval' else '1')};getter=nodes['K2Node_CallFunction_'+('2' if kind=='eval' else '1')];variable=nodes['K2Node_VariableSet_0'];valuepin='PlayerPosition' if kind=='eval' else 'PlayerLocation'
        elif kind in ('follow','goto'):points=[(nodes['K2Node_Event_'+('1' if kind=='follow' else '0')],'then','enter'),(nodes['K2Node_LatentGameplayTaskCall_0'],'OnMoveFinished','success'),(nodes['K2Node_LatentGameplayTaskCall_0'],'OnRequestFailed','failed')];moved=set()
        else:points=[(nodes['K2Node_Event_0'],'then','enter'),(nodes['K2Node_Event_1'],'then','tick'),(nodes['K2Node_CallFunction_4'],'then','enter_done'),(nodes['K2Node_CallFunction_0'],'then','tick_done')];moved=set()
        names={str(n.EventReference.MemberName) for n in event.Nodes if n.get_class().get_name()=='K2Node_Event'};signatures={n:ue.describe_function(bp.GeneratedClass,n) for n in names};ignored={g.get_name():set() for g,_ in originals}
        for n,p,_ in points:
            target,=n.node_find_pin(p).get_linked_to();ignored[event.get_name()].update(((n.get_name(),p),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,ns-(moved if g==event else set()),ignored[g.get_name()]) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};group_hash=semantics(event,moved,set()) if moved else None;helper=None
        if moved:
            links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in moved for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in moved];helper=ue.blueprint_add_function(bp,NATIVE[kind]['location']);start=helper.Nodes[0];result=helper.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('Vector')),'ReturnValue')
            for name in moved:move_node(event,helper,nodes[name])
            for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
            connect(start,'then',result,'execute');connect(getter,'ReturnValue',result,'ReturnValue')
        for _,_,key in points:gate(bp,GATES[kind][key])
        if kind in ('follow','goto'):
            alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[kind]['move'];event.graph_reconstruct_node(alias);connect(alias,'then',nodes['K2Node_LatentGameplayTaskCall_0'],'execute')
        elif kind=='delay':
            for key,target in (('enter_delay','K2Node_CallFunction_4'),('tick_delay','K2Node_CallFunction_0')):
                alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=NATIVE[kind][key];event.graph_reconstruct_node(alias);connect(alias,'then',nodes[target],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if moved:
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,NATIVE[kind]['location']));connect(entry,'then',call,'execute');connect(call,'then',variable,'execute');connect(call,'ReturnValue',variable,valuepin)
        for node,pin,key in points:insert_gate(event,node,pin,getattr(bp.GeneratedClass,GATES[kind][key]))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_ExplorerState'+kind.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.explorer_state_mixin',PythonClass='LyraExplorerState'+kind.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();after={n:ue.describe_function(bp.GeneratedClass,n) for n in names};(out/(kind+'-state-signatures.json')).write_text(json.dumps(dict(before=signatures,after=after),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or signatures!=after or snapshot(bp,kind+'-explorer-state-after')!=before:raise RuntimeError('original StateTree node CDO/public ABI changed: '+kind)
        if any(semantics(g,ns-(moved if g==event else set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or (helper is not None and semantics(helper,moved,set())!=group_hash) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original StateTree node graph/GUID changed: '+kind)
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));actual=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total-interface
        if interface!=5 or actual!=transport:raise RuntimeError('StateTree transport differs: '+repr((kind,actual)))
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),len(METHODS[kind])):raise RuntimeError('complete StateTree Profile family required')
        finally:ue.unregister_all_mixins()
        rows[kind]=dict(original_nodes=total,transport_nodes=actual,interface_nodes=interface,method_counts=counts,original_cdo_public_signatures_nodes_guids_and_native_payload_preserved=True);pending.extend([bp,asset]);assets.extend([asset_path,'Content/UEPMixins/'+name+'.uasset'])
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='explorerstate',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_native_statetree_event_transition_abi_preserved=True,original_native_ai_move_options_and_result_callback_order_preserved=True,original_native_two_delay_nodes_and_completion_flags_preserved=True,original_get_player_index_zero_and_null_location_diagnostic_preserved=True,nodes=rows,new_business_nodes=0,native_end_adapter_nodes=0,assets=assets)
