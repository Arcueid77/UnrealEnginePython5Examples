"""Keep original async factory, latent UUID, delegate identity and Timeline."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_hero_burst_cue_assets import gate,timeline_exports
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.spawning_cue_mixin import CLASS,UPDATE,WATCH,PARTS,STOP,METHODS

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCNL_Spawning.uasset'


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh spawning Cue required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins()
    before=snapshot(bp,'spawning-before');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in METHODS[:-1]};templates=timeline_exports(bp,output,'spawning-before')
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(keys) for _,keys in originals)
    if total!=118 or len(bp.Timelines)!=1:raise RuntimeError('original spawning footprint/Timeline differs')
    graph=bp.UbergraphPages[0];nodes={n.get_name():n for n in graph.Nodes};timeline=nodes['K2Node_Timeline_0']
    target,=timeline.node_find_pin('Update').get_linked_to();ignored={(timeline.get_name(),'Update'),(target.owning_node.get_name(),target.name)}
    hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
    for name,node,pin in ((WATCH,'K2Node_AsyncAction_1','execute'),(PARTS,'K2Node_MacroInstance_1','exec'),(STOP,'K2Node_MacroInstance_11','exec')):
        event=graph.graph_add_node(K2Node_CustomEvent);event.CustomFunctionName=name;graph.graph_reconstruct_node(event);connect(event,'then',nodes[node],pin)
    gate(bp,UPDATE,timeline,(('Time','SpawnLinearTime'),));ue.compile_blueprint(bp);ue.unregister_all_mixins()
    insert_gate(graph,timeline,'Update',getattr(bp.GeneratedClass,UPDATE),'Time','SpawnLinearTime')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_SpawningCueMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
    asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.spawning_cue_mixin',PythonClass='LyraSpawningCue'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'spawning-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('spawning CDO/signature/compile changed')
    if timeline_exports(bp,output,'spawning-after')!=templates:raise RuntimeError('spawning native Timeline template/curve/GUID changed')
    if any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original spawning graph changed beyond Timeline gate')
    interfaces=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=7+interfaces:raise RuntimeError('spawning transport footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={n:len(r['functions']) for n,r in row['profiles'].items()}
        if counts!=dict(Python=8,BlueprintFallback=8):raise RuntimeError('complete eight-method spawning Profiles required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='spawningcue',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdos_signatures_and_business_graphs_preserved=True,original_native_timeline_templates_curves_guids_and_bindings_preserved=True,
        original_async_factory_proxy_assignment_callbacks_latent_uuid_and_delegate_identity_preserved=True,original_native_parent_effects_and_lifetime_preserved=True,
        python_timeline_clock_added=False,new_business_nodes=0,native_end_adapter_nodes=0,original_graph_nodes=118,transport_nodes=7,interface_nodes=interfaces,
        actual_registered_profile_method_counts=counts,assets=[RELATIVE,'Content/UEPMixins/DA_SpawningCueMixin.uasset'])
