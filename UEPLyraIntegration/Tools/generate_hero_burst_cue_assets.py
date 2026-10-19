"""Retain original native Timeline templates/curves, routing only business events."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.hero_burst_cue_mixin import CLASSES,UPDATE,FINISH

ASSETS={kind:'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/'+name+'.uasset' for kind,name in (('dash','GCNL_Dash'),('death','GCNL_Death'))}
SETS=['Content/UEPMixins/DA_DashCueMixin.uasset','Content/UEPMixins/DA_DeathCueMixin.uasset']


def kind(pin):return EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category,PinSubCategoryObject=pin.sub_category_object,bIsReference=pin.is_reference,bIsConst=pin.is_const)


def gate(bp,name,timeline,parameters):
    graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for arg,source in parameters:entry.node_create_pin(1,kind(timeline.node_find_pin(source)),arg)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')


def timeline_exports(bp,output,prefix):
    result={}
    for timeline in bp.Timelines:
        file=output/(prefix+'-'+timeline.get_name()+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(timeline,str(file)):raise RuntimeError('timeline template export failed')
        result[timeline.get_name()]=file.read_text(encoding='utf-8-sig')
        for i,track in enumerate(timeline.FloatTracks):
            curve=track.CurveFloat;file=output/(prefix+'-'+timeline.get_name()+'-curve'+str(i)+'.t3d')
            if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(curve,str(file)):raise RuntimeError('timeline curve export failed')
            result[timeline.get_name()+'-curve'+str(i)]=file.read_text(encoding='utf-8-sig')
    return result


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent
    rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh hero burst Cue required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins()
        before=snapshot(bp,label+'-cue-before');signature=ue.describe_function(bp.GeneratedClass,'OnBurst');templates=timeline_exports(bp,output,label+'-before')
        originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(keys) for _,keys in originals)
        if total!={'dash':63,'death':91}[label] or len(bp.Timelines)!=1:raise RuntimeError('original hero burst footprint/timeline differs')
        graph=bp.UbergraphPages[0];timeline,=[n for n in graph.Nodes if n.get_class().get_name()=='K2Node_Timeline']
        tracks=('Deform','RibbonTrail') if label=='dash' else ('KillTimeline','EdgeGlow')
        ignored=set()
        for endpoint in ('Update','Finished'):
            target,=timeline.node_find_pin(endpoint).get_linked_to();ignored.update(((timeline.get_name(),endpoint),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
        gate(bp,UPDATE,timeline,(('ValueA',tracks[0]),('ValueB',tracks[1])));gate(bp,FINISH,timeline,())
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for endpoint,name in (('Update',UPDATE),('Finished',FINISH)):
            old={n.get_name() for n in graph.Nodes};insert_gate(graph,timeline,endpoint,getattr(bp.GeneratedClass,name))
            if endpoint=='Update':
                call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
                for arg,source in (('ValueA',tracks[0]),('ValueB',tracks[1])):connect(timeline,source,call,arg)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_'+label.title()+'CueMixin'
        asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
        asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.hero_burst_cue_mixin',PythonClass='Lyra'+label.title()+'Cue'+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-cue-after')!=before or ue.describe_function(bp.GeneratedClass,'OnBurst')!=signature:raise RuntimeError('hero burst CDO/signature/compile changed')
        if timeline_exports(bp,output,label+'-after')!=templates:raise RuntimeError('original native timeline template/curve/GUID changed')
        if any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original hero burst graph changed beyond update/finish gates')
        interfaces=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=8+interfaces:raise RuntimeError('hero burst transport count differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={n:len(r['functions']) for n,r in row['profiles'].items()}
            if counts!=dict(Python=3,BlueprintFallback=3):raise RuntimeError('complete three-method hero burst Profiles required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'))
        rows[label]=dict(original_graph_nodes=total,original_native_timeline_templates_curves_guids_and_event_bindings_preserved=True,transport_nodes=8,interface_nodes=interfaces,actual_registered_profile_method_counts=counts)
    return dict(status='passed',kind='heroburstcues',runtime_acceptance=False,full_acceptance=False,
        original_class_defaults_signature_graphs_preserved=True,original_full_cdos_signatures_and_business_graphs_preserved=True,
        original_native_parent_effects_and_five_second_minimum_timer_preserved=True,native_timeline_tick_update_and_finish_retained=True,
        python_timeline_clock_added=False,new_business_nodes=0,native_end_adapter_nodes=0,cues=rows,assets=saved)
