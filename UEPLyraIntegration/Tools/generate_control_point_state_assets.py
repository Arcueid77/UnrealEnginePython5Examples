"""Extend accepted helper asset with native-ready, authority-overlap and state gates."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_small_burst_cue_assets import construction
from generate_hero_burst_cue_assets import timeline_exports
from generate_control_point_helpers_assets import RELATIVE
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.control_point_state_mixin import CLASS,GATES

SET='Content/UEPMixins/DA_ControlPointHelpersMixin.uasset'


def generate(stage):
    baseline=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPControlPointHelpersBaseline=')));accepted=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if accepted['status']!='passed' or accepted['kind']!='controlpointhelpers':raise RuntimeError('accepted helper parent revision required')
    for row in accepted['assets']:
        for key in ('stage','overlay'):
            if hashlib.sha256(Path(row[key]).read_bytes()).hexdigest().lower()!=row['sha256'].lower():raise RuntimeError('helper parent asset changed')
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent
    dependency='Plugins/GameFeatures/ShooterCore/Content/ControlPoint/B_ControlPointScoring.uasset';dependency_sha=hashlib.sha256((stage/dependency).read_bytes()).hexdigest()
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'point-state-before');components=construction(bp,output,'point-state-before');timelines=timeline_exports(bp,output,'point-state-before')
    methods=('ReceiveBeginPlay','RecomputeContest','UserConstructionScript','CheckTimerNS','MarkThisPointContested','MarkThisPointRecaptured','Capture Audio','Activate VFX','Clean Up VFX');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(keys) for _,keys in originals)
    if total!=292:raise RuntimeError('accepted helper footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
    points=((nodes['K2Node_AsyncAction_0'],'OnReady','Ready',None),(nodes['K2Node_MacroInstance_19'],'Authority','EnterAuthority',nodes['K2Node_DynamicCast_2'].node_find_pin('AsPawn')),(nodes['K2Node_MacroInstance_12'],'Authority','ExitAuthority',nodes['K2Node_DynamicCast_0'].node_find_pin('AsPawn')),(nodes['K2Node_CustomEvent_0'],'then','Recompute',None))
    ignored=set()
    for node,output_pin,key,pawn in points:
        target,=node.node_find_pin(output_pin).get_linked_to();ignored.update(((node.get_name(),output_pin),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,keys,ignored if g==event else set()) for g,keys in originals}
    for node,output_pin,key,pawn in points:make_gate(bp,GATES[key],'Pawn' if pawn is not None else None,pawn)
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for node,output_pin,key,pawn in points:
        old={n.get_name() for n in event.Nodes};insert_gate(event,node,output_pin,getattr(bp.GeneratedClass,GATES[key]))
        if pawn is not None:
            call,=[n for n in event.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction'];connect(pawn.owning_node,pawn.name,call,'Pawn')
    asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_ControlPointHelpersMixin.DA_ControlPointHelpersMixin');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.control_point_state_mixin',PythonClass='LyraControlPointState'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'point-state-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('accepted volume CDO/signature/RPC changed')
    if construction(bp,output,'point-state-after')!=components or timeline_exports(bp,output,'point-state-after')!=timelines:raise RuntimeError('accepted volume components/Timeline changed')
    if any(semantics(g,keys,ignored if g==event else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('accepted volume graph changed beyond new state gates')
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=16:raise RuntimeError('four state gates must add16 transport nodes')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=8,BlueprintFallback=8):raise RuntimeError('full helper/state Profile family required')
    finally:ue.unregister_all_mixins()
    if hashlib.sha256((stage/dependency).read_bytes()).hexdigest()!=dependency_sha:raise RuntimeError('CP scoring dependency changed')
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='controlpointstate',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,accepted_helper_cdo_components_timeline_rpc_and_all_remaining_graphs_preserved=True,
        source_original_graph_nodes=271,parent_revision_graph_nodes=292,new_transport_nodes_this_revision=16,cumulative_transport_nodes=32,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,actual_registered_profile_method_counts=counts,
        native_experience_factory_component_overlap_binding_authority_switches_and_rpc_preserved=True,timeline_update_finish_rpc_vfx_audio_business_migrated=False,dependency_hashes={dependency:dependency_sha},assets=[RELATIVE,SET])
