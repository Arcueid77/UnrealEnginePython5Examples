"""CP entry gates preserve authority, original phase/timer nodes and public ABI."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_GetSubsystem
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_weapons.cp_scoring_mixin import CLASS,GATES,WAIT,POSTGAME,CLEAR_TIMER,SET_TARGET

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/ControlPoint/B_ControlPointScoring.uasset'
DEPS=('Plugins/GameFeatures/ShooterCore/Content/Game/B_ShooterGameScoring_Base.uasset','Plugins/GameFeatures/ShooterCore/Content/Elimination/B_TeamDeathMatchScoring.uasset')
TIMER='UEPCPNativeStartScoring'


def kind(p):return EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object,ContainerType=p.container_type,bIsReference=p.is_reference,bIsConst=p.is_const)


def gate(bp,name,source,args,outputs=None):
    g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for target,original in args:entry.node_create_pin(1,kind(source.node_find_pin(original)),target)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if outputs else 'ReturnValue');result.node_find_pin('UseOriginal' if outputs else 'ReturnValue').default_value='true'
    if outputs:
        for p in outputs:result.node_create_pin(0,kind(p),p.name)
    connect(entry,'then',result,'execute')


def clear_timer(bp,name):
    g=ue.blueprint_add_function(bp,name);get=g.graph_add_node_variable_get('ScoringTimer');call=g.graph_add_node_call_function(ue.find_class('KismetSystemLibrary').K2_ClearAndInvalidateTimerHandle);connect(g.Nodes[0],'then',call,'execute');connect(get,'ScoringTimer',call,'Handle');return g,call


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh CP scoring asset required')
    deps={p:hashlib.sha256((stage/p).read_bytes()).hexdigest() for p in DEPS};ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'cp-before')
    methods=('ReceiveBeginPlay','GameStarted','Scoring','CapturePoint','RegisterControlPoint','ContestPoint','RecapturePointByTeam','GetTeamColor','GetTeamScoreCP','GetPointStatus','ClearUserFacingCue','ActivateUserFacingCue','HandleVictory','OnRep_TargetScore');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=145:raise RuntimeError('original CP footprint differs')
    graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
    points=[(event,nodes['K2Node_MacroInstance_2'],'Authority','Begin',nodes['K2Node_Event_0'],()),(event,nodes['K2Node_CustomEvent_0'],'then','GameStarted',nodes['K2Node_CustomEvent_0'],(('Phase','Phase'),)),(event,nodes['K2Node_CustomEvent_3'],'then','Scoring',nodes['K2Node_CustomEvent_3'],()),(event,nodes['K2Node_MacroInstance_1'],'Authority','Capture',nodes['K2Node_CustomEvent_1'],(('Pawns','Pawns'),('ControlPoint','ControlPoint'))),(event,nodes['K2Node_CustomEvent_2'],'then','Register',nodes['K2Node_CustomEvent_2'],(('ControlPoint','ControlPoint'),)),(event,nodes['K2Node_MacroInstance_4'],'Authority','Contest',nodes['K2Node_CustomEvent_4'],(('ControlPoint','Control Point'),)),(event,nodes['K2Node_MacroInstance_0'],'Authority','Recapture',nodes['K2Node_CustomEvent_5'],(('ControlPoint','Control Point'),('TeamId','Team ID')))]
    for method,key,args in (('ClearUserFacingCue','ClearCue',()),('ActivateUserFacingCue','ActivateCue',(('GameplayCueTag','GameplayCueTag'),('Parameters','Parameters'))),('HandleVictory','Victory',(('TeamId','TeamId'),))):
        g=graphs[method];points.append((g,g.Nodes[0],'then',key,g.Nodes[0],args))
    queries=[]
    for method,key in (('GetTeamColor','Color'),('GetTeamScoreCP','Score'),('GetPointStatus','Status')):
        g=graphs[method];ret,=[n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult'];queries.append((g,g.Nodes[0],ret,key,[p for p in ret.node_pins() if p.category!='exec']))
    ignored={g.get_name():set() for g,_ in originals}
    for g,node,output,key,source,args in points:
        target,=node.node_find_pin(output).get_linked_to();ignored[g.get_name()].update(((node.get_name(),output),(target.owning_node.get_name(),target.name)))
    for g,entry,ret,key,out in queries:
        target,=entry.node_find_pin('then').get_linked_to();ignored[g.get_name()].update(((entry.get_name(),'then'),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,keys,ignored[g.get_name()]) for g,keys in originals}
    for g,node,output,key,source,args in points:gate(bp,GATES[key],source,args)
    for g,entry,ret,key,out in queries:gate(bp,GATES[key],entry,(('TeamID','TeamID'),),out)
    for name,target in ((WAIT,nodes['K2Node_AsyncAction_1']),(TIMER,nodes['K2Node_CallFunction_26'])):
        node=event.graph_add_node(K2Node_CustomEvent);node.CustomFunctionName=name;event.graph_reconstruct_node(node);connect(node,'then',target,'execute')
    g=ue.blueprint_add_function(bp,SET_TARGET);entry=g.Nodes[0];setnode=g.graph_add_node_variable_set('TargetScore');entry.node_create_pin(1,kind(nodes['K2Node_VariableSet_2'].node_find_pin('TargetScore')),'Value');connect(entry,'then',setnode,'execute');connect(entry,'Value',setnode,'TargetScore')
    clear_timer(bp,CLEAR_TIMER)
    g,clear=clear_timer(bp,POSTGAME);entry=g.Nodes[0];[entry.node_find_pin('then').break_link_to(p) for p in list(entry.node_find_pin('then').get_linked_to())];phase=g.graph_add_node_call_function(ue.find_class('LyraGamePhaseSubsystem').K2_StartPhase);sub=ue.new_object(K2Node_GetSubsystem,g);sub.CustomClass=ue.find_class('LyraGamePhaseSubsystem');g.graph_add_node(sub);connect(sub,'ReturnValue',phase,'self');original=next(n for n in graphs['HandleVictory'].Nodes if n.get_name()=='K2Node_CallFunction_3');phase.node_find_pin('Phase').default_object=original.node_find_pin('Phase').default_object;connect(entry,'then',phase,'execute');connect(phase,'then',clear,'execute')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for g,node,output,key,source,args in points:
        previous,=node.node_find_pin(output).get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[key]));branch=g.graph_add_node(K2Node_IfThenElse);node.node_find_pin(output).break_link_to(previous);connect(node,output,call,'execute');connect(call,'then',branch,'execute');connect(call,'ReturnValue',branch,'Condition');branch.node_find_pin('then').make_link_to(previous)
        for target,original in args:connect(source,original,call,target)
    for g,entry,ret,key,out in queries:
        previous,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[key]));branch=g.graph_add_node(K2Node_IfThenElse);result=g.graph_add_node(K2Node_FunctionResult)
        for p in out:
            if p.name not in {v.name for v in result.node_pins()}:result.node_create_pin(0,kind(p),p.name)
            connect(call,p.name,result,p.name)
        entry.node_find_pin('then').break_link_to(previous);connect(entry,'then',call,'execute');connect(entry,'TeamID',call,'TeamID');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(previous);connect(branch,'else',result,'execute')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_CPScoringMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.cp_scoring_mixin',PythonClass='LyraCPScoring'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'cp-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('original CP CDO/signatures changed')
    if any(semantics(g,keys,ignored[g.get_name()])!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original CP graph changed beyond gates')
    interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total
    if interface!=5 or added!=72:raise RuntimeError('CP transport footprint differs: '+str((added,interface)))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=18,BlueprintFallback=18):raise RuntimeError('complete CP/shared-base Profile family required')
    finally:ue.unregister_all_mixins()
    if any(hashlib.sha256((stage/p).read_bytes()).hexdigest()!=sha for p,sha in deps.items()):raise RuntimeError('shared base/TDM dependency changed')
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='cpscoring',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_signatures_graphs_authority_phase_timer_repnotify_and_shared_base_preserved=True,
        typed_gates_preserve_array_inputs_and_public_multi_output_abi=True,original_graph_nodes=145,transport_nodes=67,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,actual_registered_profile_method_counts=counts,dependency_hashes=deps,assets=[RELATIVE,'Content/UEPMixins/DA_CPScoringMixin.uasset'])
