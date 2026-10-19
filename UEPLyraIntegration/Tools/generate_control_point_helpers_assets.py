"""Four project entry gates; exact native Timeline/RPC/overlap business retained."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_small_burst_cue_assets import construction
from generate_hero_burst_cue_assets import timeline_exports
from mixin_graph_gates import semantics,make_gate,insert_gate
from uep_lyra_world.control_point_helpers_mixin import CLASS,GATES

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/Blueprint/B_ControlPointVolume.uasset'
DEPS=('Plugins/GameFeatures/ShooterCore/Content/ControlPoint/B_ControlPointScoring.uasset',)


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original control point volume required')
    deps={p:hashlib.sha256((stage/p).read_bytes()).hexdigest() for p in DEPS};ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'control-point-before');components=construction(bp,output,'volume-before');timelines=timeline_exports(bp,output,'volume-before')
    methods=('UserConstructionScript','CheckTimerNS','MarkThisPointContested','MarkThisPointRecaptured','ReceiveBeginPlay','RecomputeContest','Capture Audio','Activate VFX','Clean Up VFX');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=271:raise RuntimeError('original volume footprint differs')
    graphs={g.get_name():g for g,_ in originals};targets=[];ignored={g.get_name():set() for g,_ in originals}
    for method,key in (('UserConstructionScript','Construct'),('CheckTimerNS','CheckCounter'),('MarkThisPointContested','Contest'),('MarkThisPointRecaptured','Recapture')):
        g=graphs[method];entry=g.Nodes[0];first,=entry.node_find_pin('then').get_linked_to();ignored[g.get_name()].update(((entry.get_name(),'then'),(first.owning_node.get_name(),first.name)));targets.append((g,entry,GATES[key]))
    hashes={g.get_name():semantics(g,keys,ignored[g.get_name()]) for g,keys in originals}
    for g,entry,name in targets:make_gate(bp,name,None)
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for g,entry,name in targets:insert_gate(g,entry,'then',getattr(bp.GeneratedClass,name))
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ControlPointHelpersMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.control_point_helpers_mixin',PythonClass='LyraControlPointHelpers'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'control-point-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('original volume CDO/signature/RPC changed')
    if construction(bp,output,'volume-after')!=components or timeline_exports(bp,output,'volume-after')!=timelines:raise RuntimeError('original volume components/Timeline changed')
    if any(semantics(g,keys,ignored[g.get_name()])!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original volume graph changed beyond four entry gates')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=21:raise RuntimeError('four-gate volume transport differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=4,BlueprintFallback=4):raise RuntimeError('complete control point helper family required')
    finally:ue.unregister_all_mixins()
    if any(hashlib.sha256((stage/p).read_bytes()).hexdigest()!=sha for p,sha in deps.items()):raise RuntimeError('CP scoring dependency changed')
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='controlpointhelpers',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_full_cdo_components_timeline_curves_guids_rpc_signatures_and_other_business_preserved=True,
        original_graph_nodes=271,transport_nodes=16,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,actual_registered_profile_method_counts=counts,dependency_hashes=deps,
        volume_arbitration_overlap_timeline_rpc_audio_business_migrated=False,assets=[RELATIVE,'Content/UEPMixins/DA_ControlPointHelpersMixin.uasset'])
