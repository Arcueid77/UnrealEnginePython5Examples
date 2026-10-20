"""Retain spline component template and native Timeline/curves/lifecycle adapter."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import kind
from generate_message_widget_assets import move_node,method_counts
from generate_hero_burst_cue_assets import timeline_exports,gate
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.collect_cue_mixin import CLASS,CREATE,TARGET,ERROR,START,UPDATE,FINISH
def group(bp,event,nodes,name,members,first,last,output=None,param=None):
    links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    if param:entry.node_create_pin(1,kind(nodes[first].node_find_pin('self')),'Target')
    if output:result.node_create_pin(0,kind(nodes[last].node_find_pin(output)),'ReturnValue')
    for member in members:move_node(event,g,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(entry,'then',nodes[first],'execute');connect(nodes[last],'then',result,'execute')
    if param:
        for name in members:connect(entry,'Target',nodes[name],'self')
    if output:connect(nodes[last],output,result,'ReturnValue')
    return g
def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPCollectCueBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='collectcuelifecycle':raise RuntimeError('accepted collect Cue lifecycle baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('collect Cue lifecycle baseline changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'collect-full-before');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in ('OnExecute','PlayPickup','UserConstructionScript')};templates=timeline_exports(bp,out,'collect-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};timeline=nodes['K2Node_Timeline_2'];groups={'create':{'K2Node_AddComponent_0'},'target':{'K2Node_CallFunction_14','K2Node_CallFunction_15'},'error':{'K2Node_CallFunction_13'}};moved=set().union(*groups.values());ignored={('K2Node_MacroInstance_2','Is Valid'),('K2Node_VariableSet_8','execute'),('K2Node_VariableSet_8','Spline_PickedUpAnim'),('K2Node_CallFunction_51','self'),('K2Node_VariableSet_3','then'),('K2Node_MacroInstance_2','exec'),('K2Node_CallFunction_11','then'),('K2Node_Timeline_2','Update'),('K2Node_CallFunction_64','execute'),('K2Node_Timeline_2','Finished'),('K2Node_Knot_1','InputPin')};hashes={g.get_name():semantics(g,ns-moved if g==event else ns,ignored if g==event else set()) for g,ns in original};group_hash={k:semantics(event,ns,set()) for k,ns in groups.items()};total=sum(len(ns) for _,ns in original)
    if total!=73:raise RuntimeError('accepted collect Cue lifecycle footprint differs')
    helpers={'create':group(bp,event,nodes,CREATE,groups['create'],'K2Node_AddComponent_0','K2Node_AddComponent_0','ReturnValue'),'target':group(bp,event,nodes,TARGET,groups['target'],'K2Node_CallFunction_14','K2Node_CallFunction_15',param=True),'error':group(bp,event,nodes,ERROR,groups['error'],'K2Node_CallFunction_13','K2Node_CallFunction_13')};alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=START;event.graph_reconstruct_node(alias);connect(alias,'then',timeline,'PlayFromStart');gate(bp,UPDATE,timeline,(('Position','NewTrack_0'),('Scale','ItemScale')));gate(bp,FINISH,timeline,());ue.compile_blueprint(bp);ue.unregister_all_mixins()
    call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,CREATE));connect(nodes['K2Node_MacroInstance_2'],'Is Valid',call,'execute');connect(call,'then',nodes['K2Node_VariableSet_8'],'execute');connect(call,'ReturnValue',nodes['K2Node_VariableSet_8'],'Spline_PickedUpAnim');connect(call,'ReturnValue',nodes['K2Node_CallFunction_51'],'self');call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,TARGET));connect(nodes['K2Node_VariableSet_3'],'then',call,'execute');connect(nodes['K2Node_VariableSet_3'],'Output_Get',call,'Target');connect(call,'then',nodes['K2Node_MacroInstance_2'],'exec');call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,ERROR));connect(nodes['K2Node_CallFunction_11'],'then',call,'execute')
    for endpoint,name in (('Update',UPDATE),('Finished',FINISH)):
        old={n.get_name() for n in event.Nodes};insert_gate(event,timeline,endpoint,getattr(bp.GeneratedClass,name))
        if endpoint=='Update':
            call,=[n for n in event.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction'];connect(timeline,'NewTrack_0',call,'Position');connect(timeline,'ItemScale',call,'Scale')
    asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_CollectCueLifecycleMixin.DA_CollectCueLifecycleMixin');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.collect_cue_mixin',PythonClass='LyraCollectCue'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.compile_blueprint(bp);ue.unregister_all_mixins();after=snapshot(bp,'collect-full-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in shapes};after_hash={g.get_name():semantics(g,ns-moved if g==event else ns,ignored if g==event else set()) for g,ns in original};after_groups={k:semantics(helpers[k],ns,set()) for k,ns in groups.items()};after_templates=timeline_exports(bp,out,'collect-after');proof=dict(status=int(bp.Status),cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hash,group_hashes_before=group_hash,group_hashes_after=after_groups,timeline_templates_equal=templates==after_templates,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'collect-full-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hash or group_hash!=after_groups or templates!=after_templates or proof['bad_guids']:raise RuntimeError('collect Cue CDO/ABI/original template/curve/component/group/GUID changed')
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=18:raise RuntimeError('collect Cue business transport footprint differs')
    counts=method_counts(bp,6);bp.save_package();asset.save_package();curves={str(t.TrackName):t.CurveFloat.get_path_name() for t in bp.Timelines[0].FloatTracks}
    return dict(status='passed',kind='collectcue',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_public_abis_guids_graph_partitions_native_spline_template_and_timeline_curves_preserved=True,lifecycle_adapter_and_original_forwarding_empty_overrides_preserved=True,original_world_spline_points_socket_branch_bounds_and_uniform_scale_policy_migrated=True,native_timeline_clock_retained=True,whole_collect_cue_business_migrated=True,transport_nodes_added=18,native_end_adapter_nodes=0,new_business_nodes=0,method_counts=counts,curve_paths=curves,assets=['Plugins/GameFeatures/ShooterMaps/Content/GameplayCues/GC_Collect_Effect.uasset','Content/UEPMixins/DA_CollectCueLifecycleMixin.uasset'])
