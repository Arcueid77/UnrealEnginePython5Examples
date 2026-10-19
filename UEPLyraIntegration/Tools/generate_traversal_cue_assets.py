"""Preserve launcher Timeline/custom clear entry and teleporter macro fallback."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_hero_burst_cue_assets import timeline_exports
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.traversal_cue_mixin import CLASSES,UPDATE

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/'+n+'.uasset' for k,n in (('launcher','GCNL_Launcher_Activate'),('teleporter','GCNL_Teleporter_Activate'))}


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent
    rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh traversal Cues required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins()
        before=snapshot(bp,label+'-cue-before');methods=('OnBurst','Clear Trails') if label=='launcher' else ('OnBurst',);signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
        originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=({'launcher':98,'teleporter':92}[label]):raise RuntimeError('original traversal Cue footprint differs')
        ignored=set();graph=bp.UbergraphPages[0];timeline=None;templates=timeline_exports(bp,output,label+'-before')
        if label=='launcher':
            timeline,=[n for n in graph.Nodes if n.get_class().get_name()=='K2Node_Timeline'];target,=timeline.node_find_pin('Update').get_linked_to();ignored={(timeline.get_name(),'Update'),(target.owning_node.get_name(),target.name)}
        hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
        if timeline is not None:
            gate=ue.blueprint_add_function(bp,UPDATE);entry=gate.Nodes[0];pin=timeline.node_find_pin('NewTrack_0');entry.node_create_pin(1,EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category,PinSubCategoryObject=pin.sub_category_object),'Time')
            result=gate.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')
            ue.compile_blueprint(bp);ue.unregister_all_mixins();old={n.get_name() for n in graph.Nodes};insert_gate(graph,timeline,'Update',getattr(bp.GeneratedClass,UPDATE))
            call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction'];connect(timeline,'NewTrack_0',call,'Time')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_'+label.title()+'CueMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
        asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.traversal_cue_mixin',PythonClass='Lyra'+label.title()+'Cue'+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-cue-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('traversal full CDO/signatures/compile changed')
        if timeline_exports(bp,output,label+'-after')!=templates:raise RuntimeError('native traversal Timeline changed')
        if any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original traversal graph changed outside timeline update gate')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=4 if label=='launcher' else 0
        if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=interface+transport:raise RuntimeError('traversal transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()};expected=3 if label=='launcher' else 1
            if counts!=dict(Python=expected,BlueprintFallback=expected):raise RuntimeError('complete traversal Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,actual_registered_profile_method_counts=counts)
    return dict(status='passed',kind='traversalcues',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdos_signatures_and_business_graphs_preserved=True,original_native_parent_effects_and_timer_preserved=True,original_native_launcher_timeline_templates_curves_guids_and_bindings_preserved=True,
        original_teleporter_increment_macro_graph_retained=True,python_timeline_clock_added=False,new_business_nodes=0,native_end_adapter_nodes=0,cues=rows,assets=saved)
