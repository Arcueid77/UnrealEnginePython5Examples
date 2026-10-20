"""Pawn construction/behavior decisions; retain original FText/native operation payloads."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_FunctionResult,K2Node_CallParentFunction
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from generate_explorer_character_assets import relative,input_bindings
from generate_explorer_beginplay_assets import signatures
from generate_explorer_input_assets import bindings
from generate_dash_selector_assets import snapshot
from generate_message_widget_assets import move_node,raw_text
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_characters.explorer_helpers_mixin import CLASSES
from uep_lyra_characters.explorer_init_mixin import resolve
from uep_lyra_characters.explorer_behavior_mixin import CONTROLLER,BEHAVIOR,BT_TEXT,ST_TEXT,PARENT

def cdo(bp,label):return canonical_cdo('\n'.join(line for line in snapshot(bp,label).splitlines() if not line.strip().startswith(CONTROLLER+'=')))
def move_group(bp,graph,nodes,names,function,controller=False):
    links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in graph.Nodes if n.get_name() in names for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in names];helper=ue.blueprint_add_function(bp,function);entry=helper.Nodes[0]
    if controller:entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('Controller')),'Controller')
    result=helper.graph_add_node(K2Node_FunctionResult)
    if not controller:result.node_create_pin(0,EdGraphPinType(PinCategory='text'),'ReturnValue')
    for name in names:move_node(graph,helper,nodes[name])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    first='K2Node_CallFunction_4' if controller else 'K2Node_CallFunction_0' if function==BT_TEXT else 'K2Node_CallFunction_2';last='K2Node_CallFunction_0' if controller else first;connect(entry,'then',nodes[first],'execute');connect(nodes[last],'then',result,'execute')
    if controller:connect(entry,'Controller',nodes['K2Node_CallFunction_1'],'ControlledActor')
    else:connect(nodes['K2Node_CallFunction_1' if function==BT_TEXT else 'K2Node_CallFunction_3'],'ReturnValue',result,'ReturnValue')
    return helper

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCharacterBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='explorerinput':raise RuntimeError('accepted Explorer Python25/Original20 input baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('Explorer input parent changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];reports={};pending=[]
    for key in CLASSES:
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();callbacks={k:resolve(bp.GeneratedClass,k) for k in ('team','experience')};before=cdo(bp,key+'-behavior-before');sigs=signatures(bp,callbacks);before_input=bindings(bp.GeneratedClass);input_shapes={k:ue.describe_function(bp.GeneratedClass,v) for k,v in before_input.items()};originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};ignored={g.get_name():set() for g,_ in originals};moved={};text_before={};helpers={}
        if key=='pawn':
            ctor=next(g for g,_ in originals if g.get_name()=='UserConstructionScript');behavior=next(g for g,_ in originals if g.get_name()=='UseBehaviorTree');event=bp.UbergraphPages[0]
            moved[ctor.get_name()]={'K2Node_CallFunction_0','K2Node_CallFunction_1','K2Node_VariableGet_1','K2Node_CallFunction_2','K2Node_CallFunction_3','K2Node_VariableGet_2'};moved[behavior.get_name()]={'K2Node_CallFunction_4','K2Node_VariableGet_1','K2Node_CallFunction_1','K2Node_CallFunction_0','K2Node_VariableGet_2','K2Node_Knot_0'}
            ignored[ctor.get_name()]={('K2Node_IfThenElse_0','then'),('K2Node_IfThenElse_0','else'),('K2Node_CallParentFunction_0','execute')};ignored[behavior.get_name()]={('K2Node_IfThenElse_0','then')};ignored[event.get_name()]={('K2Node_Event_2','then'),('K2Node_MacroInstance_0','Execute'),('K2Node_Event_2','NewController'),('K2Node_Knot_0','InputPin')}
        hashes={g.get_name():semantics(g,ns-moved.get(g.get_name(),set()),ignored[g.get_name()]) for g,ns in originals}
        if key=='pawn':
            cn={n.get_name():n for n in ctor.Nodes};bn={n.get_name():n for n in behavior.Nodes};en={n.get_name():n for n in event.Nodes};group_names={'behavior':moved[behavior.get_name()],'bt':{'K2Node_CallFunction_0','K2Node_CallFunction_1','K2Node_VariableGet_1'},'st':{'K2Node_CallFunction_2','K2Node_CallFunction_3','K2Node_VariableGet_2'}};group_hashes={'behavior':semantics(behavior,group_names['behavior'],set()),'bt':semantics(ctor,group_names['bt'],set()),'st':semantics(ctor,group_names['st'],set())};text_before={k:raw_text(cn[node],out/(k+'-original-text.t3d')) for k,node in (('bt','K2Node_CallFunction_1'),('st','K2Node_CallFunction_3'))}
            ue.blueprint_add_member_variable(bp,CONTROLLER,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('Controller')))
            for variable in bp.NewVariables:
                if str(variable.VarName)==CONTROLLER:variable.PropertyFlags=int(variable.PropertyFlags)|0x2000
            ue.compile_blueprint(bp);ue.unregister_all_mixins()
            helpers['bt']=move_group(bp,ctor,cn,group_names['bt'],BT_TEXT);helpers['st']=move_group(bp,ctor,cn,group_names['st'],ST_TEXT);helpers['behavior']=move_group(bp,behavior,bn,group_names['behavior'],BEHAVIOR,True)
            parent_graph=ue.blueprint_add_function(bp,PARENT);entry=parent_graph.Nodes[0];call=parent_graph.graph_add_node(K2Node_CallParentFunction);source=cn['K2Node_CallParentFunction_0'];call.FunctionReference=MemberReference(MemberName='UserConstructionScript',MemberParent=source.FunctionReference.MemberParent,bSelfContext=False);parent_graph.graph_reconstruct_node(call);connect(entry,'then',call,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
            for pin,function in (('then',BT_TEXT),('else',ST_TEXT)):
                call=ctor.graph_add_node_call_function(getattr(bp.GeneratedClass,function));connect(cn['K2Node_IfThenElse_0'],pin,call,'execute');connect(call,'then',cn['K2Node_CallParentFunction_0'],'execute')
            call=behavior.graph_add_node_call_function(getattr(bp.GeneratedClass,BEHAVIOR));connect(bn['K2Node_IfThenElse_0'],'then',call,'execute');connect(bn['K2Node_FunctionEntry_0'],'Controller',call,'Controller')
            store=event.graph_add_node_variable_set(CONTROLLER);read=event.graph_add_node_variable_get(CONTROLLER);connect(en['K2Node_Event_2'],'then',store,'execute');connect(store,'then',en['K2Node_MacroInstance_0'],'Execute');connect(en['K2Node_Event_2'],'NewController',store,CONTROLLER);en['K2Node_Knot_0'].node_find_pin('InputPin').break_all_pin_links(True);connect(read,CONTROLLER,en['K2Node_Knot_0'],'InputPin');ue.compile_blueprint(bp);ue.unregister_all_mixins()
            text_after={k:raw_text(cn[node],out/(k+'-moved-text.t3d')) for k,node in (('bt','K2Node_CallFunction_1'),('st','K2Node_CallFunction_3'))}
            if text_before!=text_after or any(semantics(helpers[k],group_names[k],set())!=group_hashes[k] for k in group_names):raise RuntimeError('original localized label/native behavior group payload changed')
            (out/'localized-text-identity.json').write_text(json.dumps(dict(before=text_before,after=text_after),indent=2))
        name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/'+name+'.'+name);asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_behavior_mixin',PythonClass='LyraExplorerBehavior'+key.title()+p+'Profile') for p in ('Python','BlueprintFallback')]
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()};expected=dict(Python=27,BlueprintFallback=22) if key=='pawn' else dict(Python=25,BlueprintFallback=20)
            if counts!=expected:raise RuntimeError('complete Explorer behavior/controller continuation family required')
        finally:ue.unregister_all_mixins()
        after=cdo(bp,key+'-behavior-after');after_sigs=signatures(bp,callbacks);after_input=bindings(bp.GeneratedClass)
        graph_changes={g.get_name():dict(before=hashes[g.get_name()],after=semantics(g,ns-moved.get(g.get_name(),set()),ignored[g.get_name()])) for g,ns in originals if semantics(g,ns-moved.get(g.get_name(),set()),ignored[g.get_name()])!=hashes[g.get_name()]}
        (out/(key+'-behavior-diagnostics.json')).write_text(json.dumps(dict(status=int(bp.Status),cdo_equal=before==after,signatures_equal=sigs==after_sigs,input_equal=input_shapes=={k:ue.describe_function(bp.GeneratedClass,v) for k,v in after_input.items()},signatures_before=sigs,signatures_after=after_sigs,graph_changes=graph_changes,guid_changes=[n.get_name() for n,value in guids.items() if n.NodeGuid.as_dict()!=value]),indent=2))
        if int(bp.Status)==2 or before!=after or sigs!=after_sigs or input_shapes!={k:ue.describe_function(bp.GeneratedClass,v) for k,v in after_input.items()} or any(semantics(g,ns-moved.get(g.get_name(),set()),ignored[g.get_name()])!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('original Explorer behavior CDO/ABI/graph partitions/GUIDs changed')
        added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-sum(len(ns) for _,ns in originals)
        if added!=(13 if key=='pawn' else 0):raise RuntimeError('Explorer behavior transport footprint differs')
        (out/(key+'-behavior-preservation.json')).write_text(json.dumps(dict(cdo_before=before,cdo_after=after,signatures_before=sigs,signatures_after=after_sigs,input_bindings_before=before_input,input_bindings_after=after_input,original_graph_hashes=hashes),indent=2));reports[key]=dict(method_counts=counts,transport_nodes_added=added,original_cdo_public_abis_graph_partitions_guids_and_input_frames_preserved=True,latest_controller_transport_transient=True,original_text_namespace_keys_native_payload_preserved=True,whole_character_migrated=False);pending.extend([bp,asset]);assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset'])
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='explorerbehavior',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,original_text_and_static_parent_constructor_payloads_preserved=True,original_native_destroy_then_ai_lookup_then_run_behavior_operations_preserved=True,latest_possession_controller_forwarded_after_inventory_grant=True,original_all_cdos_public_abis_node_guids_and_graph_partitions_preserved=True,whole_characters_migrated=False,characters=reports,assets=assets)
