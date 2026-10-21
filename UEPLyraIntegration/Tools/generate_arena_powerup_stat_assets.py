"""Keep soft-reference transport, native Delay UUID and complete original data."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from message_payload_graphs import connect
from mixin_graph_gates import semantics
from uep_lyra_hud.arena_powerup_stat_mixin import CLASS,PREPARE,BIND,BOUND,DELAY,NUMBER
RELATIVE='Plugins/GameFeatures/TopDownArena/Content/UserInterface/Player/W_Powerup_Stat.uasset'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def kind(p):return EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object,ContainerType=p.container_type,bIsReference=p.is_reference,bIsConst=p.is_const)

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE)!=sha(official/RELATIVE):raise RuntimeError('fresh original powerup stat required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'arena-stat-before');templates=visuals(bp,out,'arena-stat-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in ('Configure','UpdateText','ListenFor',BOUND)}
    if sum(len(ns) for _,ns in original)!=28:raise RuntimeError('original twenty-eight stat nodes required')
    graphs={g.get_name():g for g,_ in original};configure=graphs['Configure'];entry=configure.Nodes[0];macro,=entry.node_find_pin('then').get_linked_to();image,=[n for n in configure.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='SetBrushFromLazyDisplayAsset'];soft=entry.node_find_pin('Display Asset');image_source,=image.node_find_pin('LazyObject').get_linked_to()
    if (image_source.owning_node,image_source.name)!=(soft.owning_node,soft.name) or image.node_find_pin('bMatchTextureSize').default_value!='false':raise RuntimeError('original lazy soft-reference forwarding differs')
    ignored={(entry.get_name(),'then'),(macro.owning_node.get_name(),macro.name)};hashes={g.get_name():semantics(g,ns,ignored if g==configure else set()) for g,ns in original}
    gate=ue.blueprint_add_function(bp,PREPARE);start=gate.Nodes[0]
    for name,source in (('AbilityTarget','Ability Target'),('Attribute','Attribute')):start.node_create_pin(1,kind(entry.node_find_pin(source)),name)
    result=gate.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(start,'then',result,'execute')
    event=bp.UbergraphPages[0];delay,=[n for n in event.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='Delay'];continuation,=delay.node_find_pin('then').get_linked_to()
    if delay.node_find_pin('Duration').default_value!='0.100000' or str(continuation.owning_node.FunctionReference.MemberName)!='ListenFor':raise RuntimeError('original retry Delay/continuation differs')
    retry=event.graph_add_node(K2Node_CustomEvent);retry.CustomFunctionName=DELAY;event.graph_reconstruct_node(retry);connect(retry,'then',delay,'execute')
    bind=ue.blueprint_add_function(bp,BIND);start=bind.Nodes[0];cls=ue.find_class('AbilityAsync_WaitAttributeChanged');start.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Observer');add=bind.graph_add_node(K2Node_AddDelegate);add.DelegateReference=MemberReference(MemberName='Changed',MemberParent=cls,bSelfContext=False);bind.graph_reconstruct_node(add);delegate,owner=bind.graph_add_node(K2Node_CreateDelegate),bind.graph_add_node(K2Node_Self);connect(start,'then',add,'execute');connect(start,'Observer',add,'self');connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',add,'Delegate');delegate.SelectedFunctionName=BOUND
    graph=ue.blueprint_add_function(bp,NUMBER);start=graph.Nodes[0];source_format,=[n for n in graphs['UpdateText'].Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='Conv_Int64ToText'];start.node_create_pin(1,kind(source_format.node_find_pin('Value')),'Value');format_node=graph.graph_add_node_call_function(ue.find_class('KismetTextLibrary').Conv_Int64ToText);text=graph.graph_add_node_variable_get('BonusText');setter=graph.graph_add_node_call_function(ue.find_class('TextBlock').SetText);connect(start,'then',setter,'execute');connect(start,'Value',format_node,'Value');connect(format_node,'ReturnValue',setter,'InText');connect(text,'BonusText',setter,'self')
    formatting={name:source_format.node_find_pin(name).default_value for name in ('bAlwaysSign','bUseGrouping','MinimumIntegralDigits','MaximumIntegralDigits')}
    for name,value in formatting.items():format_node.node_find_pin(name).default_value=value
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    call=configure.graph_add_node_call_function(getattr(bp.GeneratedClass,PREPARE));branch=configure.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(macro);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'ReturnValue',branch,'Condition');branch.node_find_pin('then').connect(macro);connect(branch,'else',image,'execute');connect(entry,'Ability Target',call,'AbilityTarget');connect(entry,'Attribute',call,'Attribute')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ArenaPowerupStatMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.arena_powerup_stat_mixin',PythonClass='LyraArenaPowerupStat'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=snapshot(bp,'arena-stat-after');after_templates=visuals(bp,out,'arena-stat-after');after_shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in shapes};after_hashes={g.get_name():semantics(g,ns,ignored if g==configure else set()) for g,ns in original};proof=dict(cdo_equal=before==after,visuals_equal=templates==after_templates,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v],ignored_original_execution_endpoints=sorted(ignored));(out/'arena-powerup-stat-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or templates!=after_templates or shapes!=after_shapes or hashes!=after_hashes or proof['bad_guids'] or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=46:raise RuntimeError('original stat CDO/ABI/GUID/tree/animation or graph transport differs')
    new_soft,=image.node_find_pin('LazyObject').get_linked_to();new_continuation,=delay.node_find_pin('then').get_linked_to()
    if (new_soft.owning_node,new_soft.name)!=(soft.owning_node,soft.name) or (new_continuation.owning_node,new_continuation.name)!=(continuation.owning_node,continuation.name):raise RuntimeError('soft argument or original retry continuation changed')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=4,BlueprintFallback=4):raise RuntimeError('four complete stat methods required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='arenapowerupstat',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_graphs_guids_tree_animation_preserved=True,soft_reference_never_crosses_python=True,native_ftext_format_and_set_kept_together=True,original_retry_delay_and_uuid_preserved=True,retry_seconds=.1,retry_guid=delay.NodeGuid.as_dict(),retry_original_continuation='ListenFor',formatting=formatting,method_counts=counts,original_nodes=28,interface_nodes=5,transport_nodes=13,new_business_nodes=0,native_end_adapter_nodes=0,assets=[RELATIVE,'Content/UEPMixins/DA_ArenaPowerupStatMixin.uasset'])
