"""Preserve original Arena phase GAS policies, tags, Delay nodes and GUIDs."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.arena_phases_mixin import CLASSES,WARM_WAIT,WARM_AFTER,PLAY,POST_WAIT,POST_AFTER
ASSETS={key:'Plugins/GameFeatures/TopDownArena/Content/Game/Modes/'+path.split('/')[-1].split('.')[0]+'.uasset' for key,path in CLASSES.items()}
TOTAL=dict(warmup=39,playing=4,postgame=6)
TRANSPORT=dict(warmup=6,playing=0,postgame=5)
COUNTS=dict(warmup=5,playing=2,postgame=2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def alias(graph,name,target):
    entry=graph.graph_add_node(K2Node_CustomEvent);entry.CustomFunctionName=name;graph.graph_reconstruct_node(entry);connect(entry,'then',target,'execute')
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for key in ('playing','postgame','warmup'):
        relative=ASSETS[key]
        if sha(stage/relative)!=sha(official/relative):raise RuntimeError('fresh original Arena phase required: '+key)
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,key+'-arena-phase-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};methods=['K2_ActivateAbility','K2_OnEndAbility']+(['ClearUserFacingCue','ActivateUserFacingCue'] if key=='warmup' else []);shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in methods};event=bp.UbergraphPages[0];ignored=set();delay=None;gate=None
        if sum(len(ns) for _,ns in original)!=TOTAL[key]:raise RuntimeError('original Arena phase footprint differs')
        if key in ('warmup','postgame'):
            delay,=[n for n in event.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='Delay'];target,=delay.node_find_pin('then').get_linked_to();ignored={(delay.get_name(),'then'),(target.owning_node.get_name(),target.name)};duration,=delay.node_find_pin('Duration').get_linked_to();variable=str(duration.owning_node.VariableReference.MemberName)
            if variable!=('GetReadyTime' if key=='warmup' else 'NewGameTime') or float(bp.GeneratedClass.get_cdo().get_property(variable))!=(3. if key=='warmup' else 10.):raise RuntimeError('original phase Delay duration input/default differs')
            gate=WARM_AFTER if key=='warmup' else POST_AFTER
        hashes={g.get_name():semantics(g,ns,ignored if g==event else set()) for g,ns in original}
        if gate:
            make_gate(bp,gate,None);alias(event,WARM_WAIT if key=='warmup' else POST_WAIT,delay)
            if key=='warmup':
                start,=[n for n in event.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='K2_StartPhase'];alias(event,PLAY,start)
                if start.node_find_pin('Phase').default_object.get_path_name()!=CLASSES['playing']:raise RuntimeError('original native StartPlaying class differs')
            ue.compile_blueprint(bp);ue.unregister_all_mixins();insert_gate(event,delay,'then',getattr(bp.GeneratedClass,gate))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Arena'+key.title()+'PhaseMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.arena_phases_mixin',PythonClass='LyraArena'+key.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        after=snapshot(bp,key+'-arena-phase-after');after_shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in shapes};after_hashes={g.get_name():semantics(g,ns,ignored if g==event else set()) for g,ns in original};bad=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v];proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=bad,ignored_original_execution_endpoints=sorted(ignored));(out/(key+'-arena-phase-preservation.json')).write_text(json.dumps(proof,indent=2),encoding='utf-8')
        if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hashes or bad or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=TOTAL[key]+TRANSPORT[key]+5:raise RuntimeError('original Arena phase GAS/CDO/ABI/GUID/Delay graphs changed: '+key)
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[key]):raise RuntimeError('complete Arena phase profiles required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[key]=dict(original_nodes=TOTAL[key],transport_nodes=TRANSPORT[key],interface_nodes=5,method_counts=counts,delay_guid=delay.NodeGuid.as_dict() if delay else None)
    return dict(status='passed',kind='arenaphases',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_gas_tags_graphs_guids_and_delays_preserved=True,default_warmup_three_and_postgame_ten_seconds_preserved=True,original_true_skip_branch_unconnected=True,postgame_empty_end_event_retained=True,original_gas_phase_parent_retained=True,new_business_nodes=0,native_end_adapter_nodes=0,phases=rows,assets=saved)
