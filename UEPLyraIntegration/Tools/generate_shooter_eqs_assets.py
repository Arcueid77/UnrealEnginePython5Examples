"""Typed context returns/native generator callback; independent stage EQS queries."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.shooter_eqs_mixin import CLASSES,GATES

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/'+v.removeprefix('/ShooterCore/').removesuffix('_C').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(points=16,enemy=8,weapon=35,enemies=17)
FIXTURES=['Content/UEPValidation/EQS_Shooter'+k.title()+'Probe.uasset' for k in CLASSES]


def fixtures(stage):
    result=[]
    for label,relative in zip(CLASSES,FIXTURES):
        factory=DataAssetFactory();factory.DataAssetClass=ue.find_class('EnvQuery');name=Path(relative).stem;query=ue.create_asset(name,'/Game/UEPValidation',ue.find_class('EnvQuery'),factory);option=ue.new_object(ue.find_class('EnvQueryOption'),query)
        if label=='enemies':generator=ue.new_object(ue.load_class(CLASSES[label]),option)
        else:generator=ue.new_object(ue.find_class('EnvQueryGenerator_CurrentLocation'),option);generator.set_property('QueryContext',ue.load_class(CLASSES[label]))
        option.set_property('Generator',generator);query.set_property('Options',[option]);query.save_package();result.append(dict(stage_only=True,label=label,asset=str(stage/relative),sha256=hashlib.sha256((stage/relative).read_bytes()).hexdigest()))
    return result


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;rows={};saved=[]
    if any((stage/p).exists() for p in FIXTURES):raise RuntimeError('fresh independent EQS fixtures required')
    for label in CLASSES:
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original shooter EQS asset required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-eqs-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals);method='DoItemGeneration' if label=='enemies' else 'ProvideSingleLocation' if label=='enemy' else 'ProvideActorsSet';signature=ue.describe_function(bp.GeneratedClass,method);graph=next(g for g,_ in originals if g.get_name()==method);entry=graph.Nodes[0];target,=entry.node_find_pin('then').get_linked_to();ignored={(entry.get_name(),'then'),(target.owning_node.get_name(),target.name)};hashes={g.get_name():semantics(g,n,ignored if g==graph else set()) for g,n in originals};guids={(g.get_name(),n.get_name()):n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        if total!=TOTAL[label]:raise RuntimeError('original EQS footprint differs')
        gate=ue.blueprint_add_function(bp,GATES[label]);ge=gate.Nodes[0];ge.set_property('ExtraFlags',int(ge.get_property('ExtraFlags'))|0x40000000);gr=gate.graph_add_node(K2Node_FunctionResult);out=None if label=='enemies' else 'Location' if label=='enemy' else 'Actors';field='UseOriginal' if out else 'ReturnValue';gr.node_create_pin(0,EdGraphPinType(PinCategory='bool'),field);gr.node_find_pin(field).default_value='true'
        if out:
            ge.node_create_pin(1,kind(entry.node_find_pin('QuerierActor')),'QuerierActor');old=next(n for n in graph.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');sourceout='ResultingLocation' if label=='enemy' else 'ResultingActorsSet';gr.node_create_pin(0,kind(old.node_find_pin(sourceout)),out)
            if label=='enemy':gr.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'HasResult')
        connect(ge,'then',gr,'execute');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if out:
            call=graph.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[label]));branch=graph.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(entry,'QuerierActor',call,'QuerierActor');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=graph.graph_add_node(K2Node_FunctionResult);early.FunctionReference=old.FunctionReference;graph.graph_reconstruct_node(early)
            if label=='enemy':
                write=graph.graph_add_node(K2Node_IfThenElse);connect(branch,'else',write,'execute');connect(call,'HasResult',write,'Condition');connect(write,'then',early,'execute')
            else:connect(branch,'else',early,'execute')
            connect(call,out,early,sourceout)
        else:insert_gate(graph,entry,'then',getattr(bp.GeneratedClass,GATES[label]))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_ShooterEQS'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.shooter_eqs_mixin',PythonClass='LyraShooterEQS'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-eqs-after')!=before or ue.describe_function(bp.GeneratedClass,method)!=signature:raise RuntimeError('original EQS CDO/config/signature changed')
        if any(semantics(g,n,ignored if g==graph else set())!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=guids[g.get_name(),n.get_name()] for g,names in originals for n in g.Nodes if n.get_name() in names):raise RuntimeError('original EQS graph/local scopes/node GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=4 if label=='enemies' else 6 if label=='enemy' else 5
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=transport+5:raise RuntimeError('EQS transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),1):raise RuntimeError('both EQS Profiles required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='shootereqs',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_return_types_local_scopes_node_guids_world_queries_team_and_native_generator_graphs_preserved=True,absent_target_leaves_location_out_parameter_unwritten=True,native_eqs_scheduler_replaced=False,new_business_nodes=0,native_end_adapter_nodes=0,contexts=rows,fixtures=fixtures(stage),assets=saved)
