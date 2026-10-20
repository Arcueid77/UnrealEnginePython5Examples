"""Keep exact phase GAS parent, original latent UUIDs and typed countdown transport."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect,read_graph
from uep_lyra_weapons.game_phases_mixin import CLASSES,GATES,BACKENDS

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/'+v.removeprefix('/ShooterCore/').removesuffix('_C').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(warmup=66,playing=4,postgame=10)
TRANSPORT=dict(warmup=23,playing=8,postgame=14)
COUNTS=dict(warmup=5,playing=2,postgame=3)
PROBE='Content/UEPValidation/BP_GamePhaseProbe.uasset'


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;rows={};saved=[]
    if (stage/PROBE).exists():raise RuntimeError('fresh phase message fixture required')
    for label in ('playing','postgame','warmup'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original game phase family required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-phase-before');methods=['K2_ActivateAbility','K2_OnEndAbility']+(['SanitizeDurations'] if label=='warmup' else []);signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original phase graph footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};graphs={g.get_name():g for g,_ in originals};points=[];aliases=[]
        if label=='warmup':
            sg=graphs['SanitizeDurations'];points=[(sg,sg.Nodes[0],'then','sanitize',None,None),(event,nodes['K2Node_Event_0'],'then','warmup',None,None),(event,nodes['K2Node_Event_1'],'then','warmupend','bWasCancelled',nodes['K2Node_Event_1'].node_find_pin('bWasCancelled')),(event,nodes['K2Node_DynamicCast_2'],'then','ready',None,None),(event,nodes['K2Node_CallFunction_18'],'then','step',None,None)];aliases=[('wait',nodes['K2Node_CallFunction_3']),('emit',nodes['K2Node_CallFunction_0']),('playing',nodes['K2Node_CallFunction_13'])]
        elif label=='playing':points=[(event,nodes['K2Node_Event_0'],'then','playing',None,None),(event,nodes['K2Node_Event_1'],'then','playingend','bWasCancelled',nodes['K2Node_Event_1'].node_find_pin('bWasCancelled'))]
        else:points=[(event,nodes['K2Node_Event_0'],'then','postgame',None,None),(event,nodes['K2Node_CallFunction_2'],'then','block',None,None),(event,nodes['K2Node_CallFunction_4'],'then','restart',None,None)];aliases=[('postwait',nodes['K2Node_CallFunction_2']),('nexttick',nodes['K2Node_CallFunction_4'])]
        ignored={g.get_name():set() for g,_ in originals}
        for g,n,pin,key,param,param_pin in points:
            target,=n.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((n.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals}
        for g,n,pin,key,param,param_pin in points:make_gate(bp,GATES[key],param,param_pin)
        for key,target in aliases:
            node=event.graph_add_node(K2Node_CustomEvent);node.CustomFunctionName=BACKENDS[key];event.graph_reconstruct_node(node);connect(node,'then',target,'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for g,n,pin,key,param,param_pin in points:insert_gate(g,n,pin,getattr(bp.GeneratedClass,GATES[key]),param,param)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_GamePhase'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.game_phases_mixin',PythonClass='Lyra'+label.title()+'Phase'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-phase-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('original phase CDO/tags/GAS policies/signatures changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('phase graph/latent/message transport changed beyond typed entry gates')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('phase transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete phase Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    probe=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_GamePhaseProbe');read_graph(probe,'Verb',ue.find_struct('LyraVerbMessage'),ue.find_class('AsyncAction_ListenForGameplayMessage'));ue.compile_blueprint(probe)
    if int(probe.Status)==2:raise RuntimeError('native phase payload fixture compile failed')
    probe.save_package()
    return dict(status='passed',kind='gamephases',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_gas_parent_tags_latent_uuids_multicast_cosmetic_and_custom_thunk_message_graphs_preserved=True,original_default_durations_preserved=True,unconnected_postgame_end_remains_unconnected=True,new_business_nodes=0,native_end_adapter_nodes=0,phases=rows,fixture=dict(stage_only=True,asset=str(stage/PROBE),sha256=hashlib.sha256((stage/PROBE).read_bytes()).hexdigest()),assets=saved)
