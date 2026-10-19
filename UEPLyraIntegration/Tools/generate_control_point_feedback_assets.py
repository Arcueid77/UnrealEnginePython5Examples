"""Extend the accepted volume revision; native Timeline/RPC/message VM stays."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_small_burst_cue_assets import construction
from generate_hero_burst_cue_assets import timeline_exports
from generate_control_point_helpers_assets import RELATIVE
from generate_control_point_state_assets import SET
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.control_point_feedback_mixin import CLASS,GATES,MESSAGE


def generate(stage):
    arg=lambda name:next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-'+name+'='))
    baseline=Path(arg('UEPControlPointHelpersBaseline'));accepted=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if accepted['status']!='passed' or accepted['kind']!='controlpointstate':raise RuntimeError('accepted volume state parent required')
    for row in accepted['assets']:
        for key in ('stage','overlay'):
            if hashlib.sha256(Path(row[key]).read_bytes()).hexdigest().lower()!=row['sha256'].lower():raise RuntimeError('volume state parent changed')
    output=Path(arg('UEPHeroAbilityAssetsResult')).parent
    dependency='Plugins/GameFeatures/ShooterCore/Content/ControlPoint/B_ControlPointScoring.uasset';dependency_sha=hashlib.sha256((stage/dependency).read_bytes()).hexdigest()
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'point-feedback-before');components=construction(bp,output,'point-feedback-before');timelines=timeline_exports(bp,output,'point-feedback-before')
    methods=('ReceiveBeginPlay','RecomputeContest','UserConstructionScript','CheckTimerNS','MarkThisPointContested','MarkThisPointRecaptured','Capture Audio','Activate VFX','Clean Up VFX','Enter Audio ','Exit Audio','Music On CP Finished')
    signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(keys) for _,keys in originals)
    if total!=308:raise RuntimeError('accepted volume state footprint differs')
    event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};timeline=nodes['K2Node_Timeline_0']
    points=[(nodes['K2Node_ExecutionSequence_0'],'then_0','Meshes',None,None),
        (timeline,'Update','TimelineUpdate','Value',timeline.node_find_pin('Capture')),
        (timeline,'Finished','TimelineFinished','Direction',timeline.node_find_pin('Direction')),
        (nodes['K2Node_CustomEvent_12'],'then','EnterAudio','Target',nodes['K2Node_CustomEvent_12'].node_find_pin('Target')),
        (nodes['K2Node_CustomEvent_13'],'then','ExitAudio','Target',nodes['K2Node_CustomEvent_13'].node_find_pin('Target')),
        (nodes['K2Node_CustomEvent_14'],'then','CaptureAudio','OwnerTeamID',nodes['K2Node_CustomEvent_14'].node_find_pin('Owner Team ID')),
        (nodes['K2Node_CustomEvent_1'],'then','Music',None,None),
        (nodes['K2Node_CustomEvent_4'],'then','ActivateVFX',None,None),
        (nodes['K2Node_CustomEvent_5'],'then','CleanVFX',None,None)]
    ignored=set()
    for node,out,_,_,_ in points:
        target,=node.node_find_pin(out).get_linked_to();ignored.update(((node.get_name(),out),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,keys,ignored if g==event else set()) for g,keys in originals}
    for _,_,key,param,pin in points:make_gate(bp,GATES[key],param,pin)
    message=event.graph_add_node(K2Node_CustomEvent);message.CustomFunctionName=MESSAGE;event.graph_reconstruct_node(message);connect(message,'then',nodes['K2Node_CallFunction_13'],'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for node,out,key,param,pin in points:
        old={n.get_name() for n in event.Nodes};insert_gate(event,node,out,getattr(bp.GeneratedClass,GATES[key]))
        if pin is not None:
            call,=[n for n in event.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction'];connect(pin.owning_node,pin.name,call,param)
    asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_ControlPointHelpersMixin.DA_ControlPointHelpersMixin')
    asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.control_point_feedback_mixin',PythonClass='LyraControlPointFeedback'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'point-feedback-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('accepted volume CDO/signature/RPC changed')
    if construction(bp,output,'point-feedback-after')!=components or timeline_exports(bp,output,'point-feedback-after')!=timelines:raise RuntimeError('accepted components/Timeline changed')
    if any(semantics(g,keys,ignored if g==event else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('accepted graphs changed beyond feedback gates')
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=37:raise RuntimeError('nine feedback gates and one native message entry required')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=17,BlueprintFallback=17):raise RuntimeError('full helper/state/feedback Profile family required')
    finally:ue.unregister_all_mixins()
    if hashlib.sha256((stage/dependency).read_bytes()).hexdigest()!=dependency_sha:raise RuntimeError('CP scoring dependency changed')
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='controlpointfeedback',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        accepted_parent_cdo_components_timeline_rpc_and_all_remaining_graphs_preserved=True,native_capture_message_custom_thunk_preserved=True,
        source_original_graph_nodes=271,parent_revision_graph_nodes=308,new_transport_nodes_this_revision=37,cumulative_transport_nodes=69,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,
        actual_registered_profile_method_counts=counts,timeline_update_finish_rpc_vfx_audio_business_migrated=True,dependency_hashes={dependency:dependency_sha},assets=[RELATIVE,SET])
