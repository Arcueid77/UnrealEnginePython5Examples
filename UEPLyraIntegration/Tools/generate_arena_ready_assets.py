"""Migrate only GetReady Construct; preserve Cue forwards and animation data."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from mixin_graph_gates import semantics
from uep_lyra_hud.arena_ready_mixin import CLASS,CUE
RELATIVE='Plugins/GameFeatures/TopDownArena/Content/GameplayCues/W_GetReady.uasset'
CUE_RELATIVE='Plugins/GameFeatures/TopDownArena/Content/GameplayCues/GCN_GetReady.uasset'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def forwarders(bp):
    result={};total=0
    for graph in ue.blueprint_get_all_graphs(bp):
        total+=len(graph.Nodes);entries=[n for n in graph.Nodes if n.get_class().get_name() in ('K2Node_Event','K2Node_FunctionEntry')]
        if len(graph.Nodes)!=len(entries)*2:raise RuntimeError('Cue contains non-forwarding nodes')
        for entry in entries:
            function=str(entry.EventReference.MemberName) if entry.get_class().get_name()=='K2Node_Event' else str(entry.FunctionReference.MemberName);linked,=entry.node_find_pin('then').get_linked_to();call=linked.owning_node
            if call.get_class().get_name()!='K2Node_CallParentFunction' or str(call.FunctionReference.MemberName)!=function or call.node_find_pin('then').get_linked_to():raise RuntimeError('Cue is not exact static parent forwarding')
            for pin in entry.node_pins():
                if pin.direction==1 and pin.category not in ('exec','delegate'):
                    targets=pin.get_linked_to()
                    if len(targets)!=1 or targets[0].owning_node!=call or targets[0].name!=pin.name:raise RuntimeError('Cue parent payload forwarding differs')
            result[function]=call.FunctionReference.MemberParent.get_path_name()
    if total!=10 or set(result)!={'UserConstructionScript','OnApplication','OnLoopingStart','OnRecurring','OnRemoval'}:raise RuntimeError('original five Cue forwards required')
    return result

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE)!=sha(official/RELATIVE) or sha(stage/CUE_RELATIVE)!=sha(official/CUE_RELATIVE):raise RuntimeError('fresh original Arena widget/Cue required')
    cue_hash=sha(stage/CUE_RELATIVE);ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));cue=ue.load_object(Blueprint,CUE.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'arena-ready-before');templates=visuals(bp,out,'arena-ready-before');cue_before=snapshot(cue,'arena-ready-cue-before');cue_forwards=forwarders(cue);original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in ('Construct','PreConstruct','Tick')}
    if sum(len(ns) for _,ns in original)!=5:raise RuntimeError('original five-node widget footprint required')
    graph=bp.UbergraphPages[0];construct,=[n for n in graph.Nodes if n.get_class().get_name()=='K2Node_Event' and str(n.EventReference.MemberName)=='Construct'];linked,=construct.node_find_pin('then').get_linked_to();call=linked.owning_node
    if str(call.FunctionReference.MemberName)!='PlayAnimationForward' or call.node_find_pin('PlaybackSpeed').default_value!='1.000000' or call.node_find_pin('bRestoreState').default_value!='false' or call.node_find_pin('then').get_linked_to():raise RuntimeError('original native animation intent differs')
    animation,=call.node_find_pin('InAnimation').get_linked_to()
    if str(animation.owning_node.VariableReference.MemberName)!='GetReady_Intro':raise RuntimeError('original animation property differs')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ArenaReadyMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.arena_ready_mixin',PythonClass='LyraArenaReady'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=snapshot(bp,'arena-ready-after');after_templates=visuals(bp,out,'arena-ready-after');after_shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in shapes};after_hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};preservation=dict(cdo_equal=before==after,visuals_equal=templates==after_templates,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'arena-ready-preservation.json').write_text(json.dumps(preservation,indent=2))
    if int(bp.Status)==2 or before!=after or templates!=after_templates or shapes!=after_shapes or hashes!=after_hashes or preservation['bad_guids'] or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-5!=5:raise RuntimeError('original widget CDO/ABI/graphs/animation/visuals/GUID changed')
    if cue_before!=snapshot(cue,'arena-ready-cue-after') or cue_forwards!=forwarders(cue) or sha(stage/CUE_RELATIVE)!=cue_hash:raise RuntimeError('original static forwarding Cue changed')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError('Construct-only widget Profiles required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='arenaready',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_graphs_guids_widget_tree_and_animation_preserved=True,cue_child_bytes_and_static_parent_forwarders_preserved=True,cue_forwarders=cue_forwards,cue_sha256=cue_hash,cue_asset=str(stage/CUE_RELATIVE),method_counts=counts,original_nodes=5,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,source_animation='GetReady_Intro',source_playback_speed=1.,source_restore_state=False,native_animation_clock_retained=True,empty_preconstruct_and_tick_retained=True,assets=[RELATIVE,'Content/UEPMixins/DA_ArenaReadyMixin.uasset'])
