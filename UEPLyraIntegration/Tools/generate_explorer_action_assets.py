"""Retain exact event/cue/pickup-interface/duration-message/montage native nodes."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent,K2Node_FunctionResult,K2Node_BreakStruct
from unreal_engine.structs import EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import kind as pin_kind
from generate_message_widget_assets import set_asset,method_counts,move_node
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,read_graph
from uep_lyra_abilities.explorer_actions_mixin import CLASSES,PREP,PICKUP,DURATION,MONTAGE,ENDED
def move_group(bp,event,nodes,name,members,params,first,first_pin,last,last_pin):
    links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for label,pin in params:entry.node_create_pin(1,pin_kind(pin),label)
    for member in members:move_node(event,g,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(entry,'then',nodes[first],first_pin);connect(nodes[last],last_pin,result,'execute');return g,entry
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];reports={}
    for key,path in CLASSES.items():
        relative='Plugins/GameFeatures/ShooterExplorer/Content/Interact/'+path.rsplit('/',1)[-1].split('.')[0]+'.uasset'
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original interaction action required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,path.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,key+'-action-before');shape=ue.describe_function(bp.GeneratedClass,'K2_ActivateAbilityFromEvent');event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};original=set(nodes);guids={n:n.NodeGuid.as_dict() for n in event.Nodes};total=24 if key=='collect' else 20
        if len(original)!=total:raise RuntimeError('original interaction action footprint differs')
        prep={'K2Node_CallFunction_8','K2Node_BreakStruct_0','K2Node_CallFunction_4','K2Node_CallFunction_7','K2Node_Knot_2'}|({'K2Node_CallFunction_14','K2Node_CallFunction_15'} if key=='collect' else set());duration={'K2Node_Knot_0','K2Node_Knot_1','K2Node_GetSubsystem_1','K2Node_CallFunction_10','K2Node_MakeStruct_1'};pickup={'K2Node_CallFunction_16','K2Node_CallFunction_27','K2Node_CallFunction_1','K2Node_CallFunction_9'} if key=='collect' else set();moved=prep|duration|pickup;ignored={('K2Node_DynamicCast_1','Object'),('K2Node_CallFunction_5','False'),('K2Node_CallFunction_5','execute'),('K2Node_LatentAbilityCall_0','execute'),('K2Node_CallFunction_2','execute')}|{('K2Node_LatentAbilityCall_0',n) for n in ('OnCompleted','OnInterrupted','OnCancelled')}
        if key=='collect':ignored.add(('K2Node_DynamicCast_1','then'))
        groups={'prep':prep,'duration':duration,**({'pickup':pickup} if pickup else {})};hashes={name:semantics(event,members,set()) for name,members in groups.items()};remaining=semantics(event,original-moved,ignored);task=nodes['K2Node_LatentAbilityCall_0'];montage_pins={p.name:p.default_value for p in task.node_pins() if p.direction==0 and p.category!='exec'}
        g,e=move_group(bp,event,nodes,PREP,prep,(('EventData',nodes['K2Node_Event_1'].node_find_pin('EventData')),),'K2Node_CallFunction_8','execute','K2Node_CallFunction_4','then');connect(e,'EventData',nodes['K2Node_BreakStruct_0'],'GameplayEventData');helpers={'prep':g}
        g,e=move_group(bp,event,nodes,DURATION,duration,(('Instigator',nodes['K2Node_MakeStruct_1'].node_find_pin('Instigator')),),'K2Node_Knot_0','InputPin','K2Node_Knot_1','OutputPin');connect(e,'Instigator',nodes['K2Node_MakeStruct_1'],'Instigator');helpers['duration']=g
        if pickup:
            g,e=move_group(bp,event,nodes,PICKUP,pickup,(('Pawn',nodes['K2Node_CallFunction_16'].node_find_pin('self')),('Target',nodes['K2Node_CallFunction_9'].node_find_pin('Actor'))),'K2Node_CallFunction_1','execute','K2Node_CallFunction_1','then');connect(e,'Pawn',nodes['K2Node_CallFunction_16'],'self');connect(e,'Target',nodes['K2Node_CallFunction_9'],'Actor');helpers['pickup']=g
        split=event.graph_add_node(K2Node_BreakStruct);split.StructType=ue.find_struct('GameplayEventData');event.graph_reconstruct_node(split);connect(nodes['K2Node_Event_1'],'EventData',split,'GameplayEventData');nodes['K2Node_DynamicCast_1'].node_find_pin('Object').break_all_pin_links(True);connect(split,'Instigator',nodes['K2Node_DynamicCast_1'],'Object');alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=MONTAGE;event.graph_reconstruct_node(alias);connect(alias,'then',task,'execute');make_gate(bp,ENDED,None);ue.compile_blueprint(bp);ue.unregister_all_mixins()
        call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,PREP));connect(nodes['K2Node_Event_1'],'then',call,'execute');connect(nodes['K2Node_Event_1'],'EventData',call,'EventData');connect(call,'then',nodes['K2Node_CallFunction_5'],'execute');call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,DURATION));connect(nodes['K2Node_CallFunction_5'],'False',call,'execute');connect(split,'Instigator',call,'Instigator');connect(call,'then',task,'execute')
        if pickup:
            call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,PICKUP));connect(nodes['K2Node_DynamicCast_1'],'then',call,'execute');connect(nodes['K2Node_DynamicCast_1'],'AsPawn',call,'Pawn');connect(split,'Target',call,'Target');connect(call,'then',task,'execute')
        for output in ('OnCompleted','OnInterrupted','OnCancelled'):insert_gate(event,task,output,getattr(bp.GeneratedClass,ENDED))
        asset=set_asset(bp,'DA_Explorer'+key.title()+'ActionMixin','uep_lyra_abilities.explorer_actions_mixin','LyraExplorer'+key.title());ue.compile_blueprint(bp);ue.unregister_all_mixins();after=snapshot(bp,key+'-action-after');after_shape=ue.describe_function(bp.GeneratedClass,'K2_ActivateAbilityFromEvent');after_hashes={name:semantics(helpers[name],members,set()) for name,members in groups.items()};after_remaining=semantics(event,original-moved,ignored);proof=dict(status=int(bp.Status),cdo_equal=before==after,signature_before=shape,signature_after=after_shape,group_hashes_before=hashes,group_hashes_after=after_hashes,remaining_before=remaining,remaining_after=after_remaining,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v],montage_pins=montage_pins);(out/(key+'-preservation.json')).write_text(json.dumps(proof,indent=2))
        if int(bp.Status)==2 or before!=after or shape!=after_shape or hashes!=after_hashes or remaining!=after_remaining or proof['bad_guids']:raise RuntimeError('original action CDO/ABI/native groups/montage or GUID changed: '+key)
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total;transport=19 if key=='collect' else 16
        if interface!=5 or added!=transport+5:raise RuntimeError('interaction action typed transport footprint differs')
        counts=method_counts(bp,2);bp.save_package();asset.save_package();assets.extend([relative,'Content/UEPMixins/DA_Explorer'+key.title()+'ActionMixin.uasset']);reports[key]=dict(original_nodes=total,transport_nodes=transport,interface_nodes=5,method_counts=counts)
    probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_ExplorerActionDurationProbe');read_graph(probe,'Duration',ue.find_struct('LyraInteractionDurationMessage'),ue.find_class('AsyncAction_ListenForGameplayMessage'));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('typed native duration reader failed compile')
    probe.save_package();file=stage/'Content/UEPValidation/BP_ExplorerActionDurationProbe.uasset'
    return dict(status='passed',kind='exploreractions',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_public_abis_node_guids_graph_partitions_and_native_payload_groups_preserved=True,original_cue_event_fields_collision_lifespan_pickup_interface_and_duration_defaults_preserved=True,original_native_montage_task_completion_interruption_cancellation_routes_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,actions=reports,fixture=dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),stage_only=True),assets=assets)
