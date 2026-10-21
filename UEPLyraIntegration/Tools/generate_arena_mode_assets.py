"""Base-owned policy gates preserve static parent calls and inherited empty events."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.arena_mode_mixin import BASE,LIVES,LOCAL,GATES,START,WARMUP,POSTGAME
PATHS={k:'Plugins/GameFeatures/TopDownArena/Content/Game/Modes/'+p.split('/')[-1].split('.')[0]+'.uasset' for k,p in (('base',BASE),('lives',LIVES),('local',LOCAL))}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;bps={};proofs={};originals={};shapes={};defaults={};guids={};hashes={};ignored={};points={}
    for key,cls in (('base',BASE),('lives',LIVES),('local',LOCAL)):
        if sha(stage/PATHS[key])!=sha(official/PATHS[key]):raise RuntimeError('fresh original Arena mode family required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,cls.removesuffix('_C'));ue.unregister_all_mixins();bps[key]=bp;defaults[key]=snapshot(bp,key+'-arena-mode-before');originals[key]=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids[key]={n:n.NodeGuid.as_dict() for g,_ in originals[key] for n in g.Nodes};methods=['ReceiveBeginPlay','ReceiveTick','GetRoundTimeRemaining','OnEliminationScored']+(['Warmup Ended'] if key=='base' else ['Spawn Local Players'] if key=='local' else []);shapes[key]={name:ue.describe_function(bp.GeneratedClass,name) for name in methods};ignored[key]={g.get_name():set() for g,_ in originals[key]};points[key]=[]
        if sum(len(ns) for _,ns in originals[key])!={'base':59,'lives':3,'local':13}[key]:raise RuntimeError('original mode footprint differs')
    lives_parent,=[n for g,_ in originals['lives'] for n in g.Nodes if n.get_class().get_name()=='K2Node_CallParentFunction'];lives_parent_before=lives_parent.FunctionReference.clone()
    base=bps['base'];event=base.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
    points['base']=[(event,nodes['K2Node_MacroInstance_0'],'Authority','begin',None),(event,nodes['K2Node_MacroInstance_1'],'Authority','tick',None),(event,nodes['K2Node_CustomEvent_1'],'then','warmup',None),(event,nodes['K2Node_AsyncAction_1'],'OnReady','ready',None)]
    for n in event.Nodes:
        if n.get_class().get_name()=='K2Node_AsyncAction_ListenForGameplayMessages':
            channel=n.node_find_pin('Channel').default_value;key='elimination' if 'Lyra.Elimination.Message' in channel else 'assist' if 'Lyra.Assist.Message' in channel else None
            if key is None or n.node_find_pin('MatchType').default_value!='ExactMatch':raise RuntimeError('original Arena exact message channel differs')
            points['base'].append((event,n,'OnMessageReceived',key,n.node_find_pin('Payload')))
    local_event=bps['local'].UbergraphPages[0];ln={n.get_name():n for n in local_event.Nodes};points['local']=[(local_event,ln['K2Node_CallParentFunction_0'],'then','localbegin',None),(local_event,ln['K2Node_CustomEvent_0'],'then','localspawn',None)]
    for key in bps:
        for graph,node,pin,gate,payload in points[key]:
            target,=node.node_find_pin(pin).get_linked_to();ignored[key][graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes[key]={g.get_name():semantics(g,ns,ignored[key][g.get_name()]) for g,ns in originals[key]}
    payloads={key:payload for _,_,_,key,payload in points['base'] if payload is not None}
    for key,name in GATES.items():make_gate(base,name,'Payload' if key in payloads else None,payloads.get(key))
    for name,target in ((START,nodes['K2Node_ExecutionSequence_0']),(WARMUP,nodes['K2Node_CallFunction_1']),(POSTGAME,nodes['K2Node_CallFunction_3'])):
        entry=event.graph_add_node(K2Node_CustomEvent);entry.CustomFunctionName=name;event.graph_reconstruct_node(entry);connect(entry,'then',target,'execute')
    ue.compile_blueprint(base);ue.unregister_all_mixins()
    for key in ('base','local'):
        for graph,node,pin,gate,payload in points[key]:insert_gate(graph,node,pin,getattr(base.GeneratedClass,GATES[gate]),'Payload' if payload is not None else None,'Payload' if payload is not None else None)
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ArenaModeMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.arena_mode_mixin',PythonClass='LyraArenaMode'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(base,asset,'Python','PythonMixinProfile');ue.compile_blueprint(base);ue.unregister_all_mixins();ue.compile_blueprint(bps['local']);ue.unregister_all_mixins()
    for key,bp in bps.items():
        after=snapshot(bp,key+'-arena-mode-after');after_shapes={name:ue.describe_function(bp.GeneratedClass,name) for name in shapes[key]};rebind=None
        if key=='lives':
            current=lives_parent.FunctionReference.clone()
            if current.as_dict()!=lives_parent_before.as_dict():
                if str(current.MemberName)!=str(lives_parent_before.MemberName) or str(current.MemberName)!='ReceiveBeginPlay' or current.MemberParent!=base.GeneratedClass or lives_parent_before.MemberParent!=ue.find_class('ActorComponent'):raise RuntimeError('unexpected Lives parent-reference mutation')
                rebind=dict(node=lives_parent.get_name(),member='ReceiveBeginPlay',before=lives_parent_before.MemberParent.get_path_name(),after=current.MemberParent.get_path_name(),normalized_for_semantic_comparison_only=True,original_package_not_saved=True)
                lives_parent.FunctionReference=lives_parent_before.clone()
            try:after_hashes={g.get_name():semantics(g,ns,ignored[key][g.get_name()]) for g,ns in originals[key]}
            finally:lives_parent.FunctionReference=current
        else:after_hashes={g.get_name():semantics(g,ns,ignored[key][g.get_name()]) for g,ns in originals[key]}
        bad=[n.get_name() for n,v in guids[key].items() if n.NodeGuid.as_dict()!=v];p=dict(cdo_equal=defaults[key]==after,signatures_before=shapes[key],signatures_after=after_shapes,graph_hashes_before=hashes[key],graph_hashes_after=after_hashes,bad_guids=bad,compiler_parent_reference_rebind=rebind);(out/(key+'-arena-mode-preservation.json')).write_text(json.dumps(p,indent=2),encoding='utf-8')
        total=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp));expected={'base':95,'local':17,'lives':3}[key]
        if int(bp.Status)==2 or not p['cdo_equal'] or shapes[key]!=after_shapes or hashes[key]!=after_hashes or bad or total!=expected:raise RuntimeError('original mode CDO/ABI/GUID/authority/graph partition changed: '+key)
        proofs[key]=dict(original_nodes={'base':59,'local':13,'lives':3}[key],transport_nodes={'base':31,'local':4,'lives':0}[key],interface_nodes=5 if key=='base' else 0)
    try:
        ue.register_declared_mixin(base.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==base.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=9,BlueprintFallback=9):raise RuntimeError('complete base-owned mode policy required')
    finally:ue.unregister_all_mixins()
    if sha(stage/PATHS['lives'])!=sha(official/PATHS['lives']):raise RuntimeError('Lives static parent forwarding bytes changed')
    base.save_package();bps['local'].save_package();asset.save_package()
    return dict(status='passed',kind='arenamode',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_guids_authority_messages_parent_calls_and_graphs_preserved=True,lives_original_bytes_and_empty_events_preserved=True,lives_asset=str(stage/PATHS['lives']),lives_sha256=sha(stage/PATHS['lives']),base_owned_gates_avoid_child_mixin_selector_collision=True,original_native_message_factories_and_experience_delegate_retained=True,original_round_duration=120.,method_counts=counts,new_business_nodes=0,native_end_adapter_nodes=0,components=proofs,assets=[PATHS['base'],PATHS['local'],'Content/UEPMixins/DA_ArenaModeMixin.uasset'])
