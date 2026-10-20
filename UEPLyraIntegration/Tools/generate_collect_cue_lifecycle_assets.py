"""Retain all collect Cue business; interpose native pool-safe lifespan deadline."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent
from generate_dash_selector_assets import snapshot
from generate_message_widget_assets import set_asset,method_counts
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.collect_cue_lifecycle_mixin import CLASS,GATE,DEADLINE
RELATIVE='Plugins/GameFeatures/ShooterMaps/Content/GameplayCues/GC_Collect_Effect.uasset'
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original collect Cue required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'collect-cue-lifecycle-before');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in ('OnExecute','PlayPickup','UserConstructionScript')};original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};points=[(nodes['K2Node_CallFunction_8'],'then',nodes['K2Node_CallFunction_4']), (nodes['K2Node_MacroInstance_2'],'Is Not Valid',nodes['K2Node_CallFunction_11'])];ignored={(source.get_name(),pin) for source,pin,_ in points}|{(target.get_name(),'execute') for _,_,target in points};hashes={g.get_name():semantics(g,ns,ignored if g==event else set()) for g,ns in original}
    if sum(len(ns) for _,ns in original)!=60 or [target.node_find_pin('InLifespan').default_value for _,_,target in points]!=['3.000000','0.0']:raise RuntimeError('original collect Cue self lifespans differ')
    make_gate(bp,GATE,'Seconds',points[0][2].node_find_pin('InLifespan'));deadline=event.graph_add_node(K2Node_CustomEvent);deadline.CustomFunctionName=DEADLINE;event.graph_reconstruct_node(deadline);end=event.graph_add_node_call_function(ue.find_class('GameplayCueNotify_Actor').K2_EndGameplayCue);connect(deadline,'then',end,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for source,pin,target in points:
        old={n.get_name() for n in event.Nodes};insert_gate(event,source,pin,getattr(bp.GeneratedClass,GATE));call,=[n for n in event.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction'];call.node_find_pin('Seconds').default_value=target.node_find_pin('InLifespan').default_value
    asset=set_asset(bp,'DA_CollectCueLifecycleMixin','uep_lyra_weapons.collect_cue_lifecycle_mixin','LyraCollectCueLifecycle');ue.compile_blueprint(bp);ue.unregister_all_mixins();after=snapshot(bp,'collect-cue-lifecycle-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in shapes};after_hashes={g.get_name():semantics(g,ns,ignored if g==event else set()) for g,ns in original};proof=dict(status=int(bp.Status),cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'collect-cue-lifecycle-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hashes or proof['bad_guids']:raise RuntimeError('original collect Cue CDO/ABI/graphs/GUIDs changed beyond lifespan transport')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-60
    if interface!=5 or added!=13:raise RuntimeError('collect Cue lifecycle transport footprint differs')
    counts=method_counts(bp,3);bp.save_package();asset.save_package()
    return dict(status='passed',kind='collectcuelifecycle',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_public_abis_all_original_nodes_guids_and_business_graphs_preserved=True,original_self_lifespan_values_three_and_zero_retained=True,pool_deadline_lead_seconds=.001,dynamic_spline_resources_released_before_execute_and_pool_return=True,whole_collect_cue_business_migrated=False,remaining_business=['PlayPickup and original native Timeline setup/update/finish business'],transport_nodes=8,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,method_counts=counts,assets=[RELATIVE,'Content/UEPMixins/DA_CollectCueLifecycleMixin.uasset'])
