"""Retain list delegates and move original localized clock nodes intact."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node,raw_text
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_hud.arena_hud_mixin import LIST,TIMER,READY,BIND,RENDER
ASSETS={key:'Plugins/GameFeatures/TopDownArena/Content/UserInterface/'+name+'.uasset' for key,name in (('list','W_TopDownPlayers'),('timer','W_RoundTimer'))}
MOVED={'K2Node_FormatText_0','K2Node_VariableGet_8','K2Node_CallFunction_4','K2Node_CallFunction_8','K2Node_CallFunction_6'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def binder(bp):
    g=ue.blueprint_add_function(bp,BIND);entry=g.Nodes[0];cls=ue.find_class('AsyncAction_ExperienceReady');entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Observer');add=g.graph_add_node(K2Node_AddDelegate);add.DelegateReference=MemberReference(MemberName='OnReady',MemberParent=cls,bSelfContext=False);g.graph_reconstruct_node(add);delegate,owner=g.graph_add_node(K2Node_CreateDelegate),g.graph_add_node(K2Node_Self);connect(entry,'then',add,'execute');connect(entry,'Observer',add,'self');connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',add,'Delegate');delegate.SelectedFunctionName=READY
    if len(g.Nodes)!=4:raise RuntimeError('ExperienceReady exact delegate transport differs')
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for key,path in (('list',LIST),('timer',TIMER)):
        relative=ASSETS[key]
        if sha(stage/relative)!=sha(official/relative):raise RuntimeError('fresh original Arena HUD required: '+key)
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,path.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,key+'-arena-hud-before');templates=visuals(bp,out,key+'-arena-hud-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};methods=('OnGetWidgetClassForData_0','OnConfigureWidgetForData_0','Construct','Tick','PreConstruct') if key=='list' else ('Construct','Tick',READY);shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in methods};total=sum(len(ns) for _,ns in original)
        if total!={'list':9,'timer':17}[key]:raise RuntimeError('original Arena HUD footprint differs')
        if key=='list':hashes={g.get_name():semantics(g,ns,set()) for g,ns in original}
        else:
            event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};remaining={n.get_name() for n in event.Nodes}-MOVED;ignored={(nodes['K2Node_CallFunction_3'].get_name(),'then')};hashes=dict(remaining=semantics(event,remaining,ignored),moved=semantics(event,MOVED,set()));literal=raw_text(nodes['K2Node_FormatText_0'],out/'arena-round-format-before.t3d');links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in event.Nodes if n.get_name() in MOVED for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in MOVED];g=ue.blueprint_add_function(bp,RENDER);entry=g.Nodes[0]
            for name,source in (('MinuteValue','K2Node_CallFunction_8'),('SecondValue','K2Node_CallFunction_6')):entry.node_create_pin(1,kind(nodes[source].node_find_pin('Value')),name)
            for name in MOVED:move_node(event,g,nodes[name])
            for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
            connect(entry,'then',nodes['K2Node_CallFunction_4'],'execute');connect(entry,'MinuteValue',nodes['K2Node_CallFunction_8'],'Value');connect(entry,'SecondValue',nodes['K2Node_CallFunction_6'],'Value');binder(bp);ue.compile_blueprint(bp);ue.unregister_all_mixins();call=event.graph_add_node_call_function(getattr(bp.GeneratedClass,RENDER));connect(nodes['K2Node_CallFunction_3'],'then',call,'execute');connect(nodes['K2Node_PromotableOperator_2'],'ReturnValue',call,'MinuteValue');connect(nodes['K2Node_CallFunction_9'],'ReturnValue',call,'SecondValue')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Arena'+('List' if key=='list' else 'Round')+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.arena_hud_mixin',PythonClass='LyraArena'+('List' if key=='list' else 'Round')+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        after=snapshot(bp,key+'-arena-hud-after');after_templates=visuals(bp,out,key+'-arena-hud-after');after_shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in shapes};bad=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]
        if key=='list':after_hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};transport=0
        else:
            after_hashes=dict(remaining=semantics(event,remaining,ignored),moved=semantics(g,MOVED,set()));transport=6
            if raw_text(nodes['K2Node_FormatText_0'],out/'arena-round-format-after.t3d')!=literal:raise RuntimeError('original Arena clock localized FText changed')
        proof=dict(cdo_equal=before==after,visuals_equal=templates==after_templates,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=bad);(out/(key+'-arena-hud-preservation.json')).write_text(json.dumps(proof,indent=2),encoding='utf-8')
        if int(bp.Status)==2 or before!=after or templates!=after_templates or shapes!=after_shapes or hashes!=after_hashes or bad or sum(len(gr.Nodes) for gr in ue.blueprint_get_all_graphs(bp))!=total+transport+5:raise RuntimeError('original Arena HUD CDO/ABI/GUIDs/tree/graph partitions differ: '+key)
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),2 if key=='list' else 3):raise RuntimeError('complete Arena HUD Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[key]=dict(original_nodes=total,method_counts=counts,interface_nodes=5,transport_nodes=transport,new_business_nodes=0)
    return dict(status='passed',kind='arenahud',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_guids_trees_graph_partitions_preserved=True,original_localized_clock_nodes_moved_intact=True,original_ftext_namespace_key_format_rounding_and_digits_preserved=True,empty_list_widget_events_retained=True,native_umg_tick_and_experience_next_tick_retained=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
