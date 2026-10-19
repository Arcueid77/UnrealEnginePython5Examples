"""Retain original parent calls, Chaos delegate identity and disconnected Tick."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CallParentFunction,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,MemberReference,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_small_burst_cue_assets import construction
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_weapons.physics_field_mixin import CLASSES,PARENTS,BIND,AFTER

ASSETS={kind:'Content/Effects/Physics/'+name+'.uasset' for kind,name in (('example','B_ExamplePhysicsField'),('sphere','B_ShatterSphere'))}


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original project physics asset required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins()
        before=snapshot(bp,label+'-physics-before');scs=construction(bp,output,label+'-before');methods=('UserConstructionScript','ReceiveBeginPlay','ReceiveTick') if label=='example' else ('ReceiveBeginPlay','SphereIsBroken')
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(keys) for _,keys in originals)
        if total!=({'example':7,'sphere':20}[label]):raise RuntimeError('original project physics footprint differs')
        graph=bp.UbergraphPages[0];nodes={n.get_name():n for n in graph.Nodes};ignored=set()
        if label=='sphere':
            assign=nodes['K2Node_AssignDelegate_0'];target,=assign.node_find_pin('then').get_linked_to();ignored={(assign.get_name(),'then'),(target.owning_node.get_name(),target.name)}
            if nodes['K2Node_Event_2'].node_find_pin('then').get_linked_to() or nodes['K2Node_VariableSet_3'].node_find_pin('execute').get_linked_to():raise RuntimeError('source shatter Tick must remain disconnected')
        hashes={g.get_name():semantics(g,keys,ignored if g==graph else set()) for g,keys in originals}
        if label=='example':
            sources={}
            for g,keys in originals:
                for node in g.Nodes:
                    if node.get_class().get_name()=='K2Node_CallParentFunction':sources[str(node.FunctionReference.MemberName)]=node
            for kind,method in (('construction','UserConstructionScript'),('begin','ReceiveBeginPlay'),('tick','ReceiveTick')):
                source=sources[method];g=ue.blueprint_add_function(bp,PARENTS[kind]);entry=g.Nodes[0];call=g.graph_add_node(K2Node_CallParentFunction)
                call.FunctionReference=MemberReference(MemberName=method,MemberParent=source.FunctionReference.MemberParent,bSelfContext=False);g.graph_reconstruct_node(call);connect(entry,'then',call,'execute')
                if kind=='tick':
                    pin=call.node_find_pin('DeltaSeconds');entry.node_create_pin(1,EdGraphPinType(PinCategory=pin.category,PinSubCategory=pin.sub_category),'DeltaSeconds');connect(entry,'DeltaSeconds',call,'DeltaSeconds')
                if len(g.Nodes)!=2:raise RuntimeError('parent transport contains extra business')
        else:
            event=graph.graph_add_node(K2Node_CustomEvent);event.CustomFunctionName=BIND;graph.graph_reconstruct_node(event);connect(event,'then',assign,'execute')
            make_gate(bp,AFTER,None);ue.compile_blueprint(bp);ue.unregister_all_mixins();insert_gate(graph,assign,'then',getattr(bp.GeneratedClass,AFTER))
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_'+('ExamplePhysicsField' if label=='example' else 'ShatterSphere')+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
        prefix='LyraExamplePhysicsField' if label=='example' else 'LyraShatterSphere';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.physics_field_mixin',PythonClass=prefix+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-physics-after')!=before or construction(bp,output,label+'-after')!=scs or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('original physics CDO/signature/templates changed')
        if any(semantics(g,keys,ignored if g==graph else set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original physics graph changed beyond explicit gate')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport=6 if label=='example' else 5
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=interface+transport:raise RuntimeError('physics transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={n:len(r['functions']) for n,r in row['profiles'].items()}
            if counts!=dict(Python=3,BlueprintFallback=3):raise RuntimeError('complete project physics Profile families required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,actual_registered_profile_method_counts=counts)
    return dict(status='passed',kind='physicsfields',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdos_signatures_business_graphs_and_component_templates_preserved=True,original_engine_field_parent_and_geometry_collection_dependency_retained=True,
        original_chaos_delegate_identity_and_disconnected_shatter_tick_preserved=True,new_business_nodes=0,native_end_adapter_nodes=0,actors=rows,assets=saved)
