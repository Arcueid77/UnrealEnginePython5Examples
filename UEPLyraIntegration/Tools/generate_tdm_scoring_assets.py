"""Preserve TDM native phase/timer/RepNotify paths; gate public business entries."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_GetSubsystem
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_footstep_assets import kind
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_weapons.tdm_scoring_mixin import CLASS,GATES,WAIT,TIMER,POSTGAME,CLEAR_TIMER,SET_TARGET,SET_TIME

RELATIVE='Plugins/GameFeatures/ShooterCore/Content/Elimination/B_TeamDeathMatchScoring.uasset'
BASE='Plugins/GameFeatures/ShooterCore/Content/Game/B_ShooterGameScoring_Base.uasset'
CP='Plugins/GameFeatures/ShooterCore/Content/ControlPoint/B_ControlPointScoring.uasset'


def gate(bp,name,source,args,outputs=None):
    g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for arg in args:entry.node_create_pin(1,kind(source.node_find_pin(arg)),arg)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if outputs else 'ReturnValue');result.node_find_pin('UseOriginal' if outputs else 'ReturnValue').default_value='true'
    if outputs:
        for pin in outputs:result.node_create_pin(0,kind(pin),pin.name)
    connect(entry,'then',result,'execute')


def setter(bp,name,field,source):
    g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];node=g.graph_add_node_variable_set(field);entry.node_create_pin(1,kind(source.node_find_pin(field)),'Value');connect(entry,'Value',node,field);connect(entry,'then',node,'execute')


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh TDM scoring asset required')
    dependencies={relative:hashlib.sha256((stage/relative).read_bytes()).hexdigest() for relative in (BASE,CP)}
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,'tdm-before')
    methods=('ReceiveBeginPlay','GameStarted','CountDown','ForceGameOver','GetTeamScore','OnEliminationScored','SetDamageEnabled','ActivateUserFacingCue','ClearUserFacingCue','RestartAllPlayers','HandleVictory','OnRep_TargetScore','OnRep_CountDownTime');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
    originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
    if total!=123:raise RuntimeError('original TDM footprint differs')
    graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[]
    points.append((event,nodes['K2Node_MacroInstance_0'],'Authority','Begin',nodes['K2Node_Event_0'],()))
    for node,key,args in (('K2Node_CustomEvent_0','GameStarted',('Phase',)),('K2Node_CustomEvent_3','CountDown',()),('K2Node_CustomEvent_1','ForceGameOver',())):points.append((event,nodes[node],'then',key,nodes[node],args))
    for method,key,args in (('OnEliminationScored','Elimination',()),('SetDamageEnabled','SetDamage',('AllowDamage',)),('ActivateUserFacingCue','ActivateCue',('GameplayCueTag','Parameters')),('ClearUserFacingCue','ClearCue',()),('RestartAllPlayers','Restart',()),('HandleVictory','Victory',('TeamId',))):
        g=graphs[method];entry=g.Nodes[0];node=next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_CallParentFunction') if method=='OnEliminationScored' else entry;points.append((g,node,'then',key,entry,args))
    query=graphs['GetTeamScore'];qentry=query.Nodes[0];qresult,=[n for n in query.Nodes if n.get_class().get_name()=='K2Node_FunctionResult'];outpins=[p for p in qresult.node_pins() if p.category!='exec'];ignored={g.get_name():set() for g,_ in originals}
    for g,node,output,key,source,args in points:
        target,=node.node_find_pin(output).get_linked_to();ignored[g.get_name()].update(((node.get_name(),output),(target.owning_node.get_name(),target.name)))
    target,=qentry.node_find_pin('then').get_linked_to();ignored[query.get_name()].update(((qentry.get_name(),'then'),(target.owning_node.get_name(),target.name)))
    hashes={g.get_name():semantics(g,keys,ignored[g.get_name()]) for g,keys in originals}
    for g,node,output,key,source,args in points:gate(bp,GATES[key],source,args)
    gate(bp,GATES['TeamScore'],qentry,('TeamId',),outpins)
    for name,target in ((WAIT,nodes['K2Node_AsyncAction_1']),(TIMER,nodes['K2Node_CallFunction_7']),(POSTGAME,next(n for n in graphs['HandleVictory'].Nodes if n.get_name()=='K2Node_CallFunction_3'))):
        target_graph=event if name!=POSTGAME else graphs['HandleVictory']
        if name==POSTGAME:
            # Custom events belong to the Ubergraph; call the exact phase function
            # through a two-node function using the same original default class.
            g=ue.blueprint_add_function(bp,name);call=g.graph_add_node_call_function(getattr(ue.find_class('LyraGamePhaseSubsystem'),'K2_StartPhase'))
            subsystem=ue.new_object(K2Node_GetSubsystem,g);subsystem.CustomClass=ue.find_class('LyraGamePhaseSubsystem');g.graph_add_node(subsystem);connect(subsystem,'ReturnValue',call,'self');call.node_find_pin('Phase').default_object=target.node_find_pin('Phase').default_object;connect(g.Nodes[0],'then',call,'execute')
        else:
            entry=event.graph_add_node(K2Node_CustomEvent);entry.CustomFunctionName=name;event.graph_reconstruct_node(entry);connect(entry,'then',target,'execute')
    setter(bp,SET_TARGET,'TargetScore',nodes['K2Node_VariableSet_2']);setter(bp,SET_TIME,'CountDownTime',nodes['K2Node_VariableSet_5'])
    g=ue.blueprint_add_function(bp,CLEAR_TIMER);entry=g.Nodes[0];get=g.graph_add_node_variable_get('TimerCountdown');clear=g.graph_add_node_call_function(ue.find_class('KismetSystemLibrary').K2_ClearAndInvalidateTimerHandle);connect(entry,'then',clear,'execute');connect(get,'TimerCountdown',clear,'Handle')
    ue.compile_blueprint(bp);ue.unregister_all_mixins()
    for g,node,output,key,source,args in points:
        previous,=node.node_find_pin(output).get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[key]));branch=g.graph_add_node(K2Node_IfThenElse);node.node_find_pin(output).break_link_to(previous);connect(node,output,call,'execute');connect(call,'then',branch,'execute');connect(call,'ReturnValue',branch,'Condition');branch.node_find_pin('then').make_link_to(previous)
        for arg in args:connect(source,arg,call,arg)
    previous,=qentry.node_find_pin('then').get_linked_to();call=query.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES['TeamScore']));branch=query.graph_add_node(K2Node_IfThenElse);result=query.graph_add_node(K2Node_FunctionResult)
    for pin in outpins:
        if pin.name not in {p.name for p in result.node_pins()}:result.node_create_pin(0,kind(pin),pin.name)
        connect(call,pin.name,result,pin.name)
    qentry.node_find_pin('then').break_link_to(previous);connect(qentry,'then',call,'execute');connect(qentry,'TeamId',call,'TeamId');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(previous);connect(branch,'else',result,'execute')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_TDMScoringMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.tdm_scoring_mixin',PythonClass='LyraTDMScoring'+p+'Profile') for p in ('Python','BlueprintFallback')]
    ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    if int(bp.Status)==2 or snapshot(bp,'tdm-after')!=before or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('TDM original CDO/signatures changed')
    if any(semantics(g,keys,ignored[g.get_name()])!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('TDM original graph changed beyond gates')
    interfaces=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total
    if interfaces!=5 or added!=62:raise RuntimeError('TDM transport footprint differs: '+str((added,interfaces)))
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
        if counts!=dict(Python=16,BlueprintFallback=16):raise RuntimeError('complete TDM/shared-base Profile family required')
    finally:ue.unregister_all_mixins()
    if any(hashlib.sha256((stage/p).read_bytes()).hexdigest()!=v for p,v in dependencies.items()):raise RuntimeError('base/CP dependency changed')
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='tdmscoring',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_signatures_graphs_native_repnotify_timer_phase_and_shared_base_preserved=True,
        base_owned_business_gates_cover_static_callers=True,original_graph_nodes=123,transport_nodes=57,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,actual_registered_profile_method_counts=counts,dependency_hashes=dependencies,assets=[RELATIVE,'Content/UEPMixins/DA_TDMScoringMixin.uasset'])
