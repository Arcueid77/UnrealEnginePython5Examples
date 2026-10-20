"""Typed AI gates preserve original controller inheritance and native BT schedules."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import kind
from generate_small_burst_cue_assets import construction
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.shooter_ai_mixin import CLASSES,GATES,BACKENDS

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/'+v.removeprefix('/ShooterCore/').removesuffix('_C').split('.')[0]+'.uasset' for k,v in CLASSES.items()}
TOTAL=dict(controller=33,allowed=3,ammo=14,reload=2,focus=11,shoot=62)
TRANSPORT=dict(controller=18,allowed=5,ammo=4,reload=4,focus=4,shoot=9)
COUNTS=dict(controller=4,allowed=1,ammo=1,reload=1,focus=1,shoot=2)
FIXTURES=('Content/UEPValidation/BB_ShooterAIProbe.uasset','Content/UEPValidation/BT_ShooterAIProbe.uasset')


def defaults(bp,label):
    # Native CDO compilation may reorder sibling subobject declarations.
    # Retain every header/property and array order; compare subobjects by content.
    stack=[];root=None
    for raw in snapshot(bp,label).splitlines():
        line=raw.strip()
        if line.startswith('Begin Object'):
            node=[line,[],[]]
            if stack:stack[-1][2].append(node)
            else:root=node
            stack.append(node)
        elif line=='End Object':stack.pop()
        elif stack and line:stack[-1][1].append(line)
    if stack or root is None:raise RuntimeError('complete native CDO object export required')
    def canonical(node):return node[0],tuple(node[1]),tuple(sorted(canonical(child) for child in node[2]))
    return canonical(root)


def gate(bp,key,params,output=None):
    graph=ue.blueprint_add_function(bp,GATES[key]);entry=graph.Nodes[0];result=graph.graph_add_node(K2Node_FunctionResult)
    for name,pin in params:entry.node_create_pin(1,kind(pin),name)
    field='UseOriginal' if output else 'ReturnValue';result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),field);result.node_find_pin(field).default_value='true'
    if output:result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),output)
    connect(entry,'then',result,'execute')


def fixture(stage):
    factory=DataAssetFactory();factory.DataAssetClass=ue.find_class('BlackboardData');board=ue.create_asset('BB_ShooterAIProbe','/Game/UEPValidation',ue.find_class('BlackboardData'),factory);booltype=ue.new_object(ue.find_class('BlackboardKeyType_Bool'),board);actor=ue.new_object(ue.find_class('BlackboardKeyType_Object'),board);actor.set_property('BaseClass',ue.find_class('Actor'));board.set_property('Keys',[ue.find_struct('BlackboardEntry')(EntryName='OutOfAmmo',KeyType=booltype),ue.find_struct('BlackboardEntry')(EntryName='TargetEnemy',KeyType=actor)])
    factory=ue.new_object(ue.find_class('BehaviorTreeFactory'));tree=ue.create_asset('BT_ShooterAIProbe','/Game/UEPValidation',ue.find_class('BehaviorTree'),factory);tree.set_property('BlackboardAsset',board);root=ue.new_object(ue.find_class('BTComposite_Sequence'),tree);wait=ue.new_object(ue.find_class('BTTask_Wait'),tree);services=[]
    for key in ('ammo','focus','shoot','reload'):
        service=ue.new_object(ue.load_class(CLASSES[key]),tree);service.set_property('NodeName','UEP_'+key)
        if key in ('ammo','shoot'):service.set_property('OutOfAmmo',ue.find_struct('BlackboardKeySelector')(SelectedKeyName='OutOfAmmo'))
        if key in ('focus','shoot'):service.set_property('TargetEnnemy',ue.find_struct('BlackboardKeySelector')(SelectedKeyName='TargetEnemy'))
        services.append(service)
    root.set_property('Services',services);decorator=ue.new_object(ue.load_class(CLASSES['allowed']),tree);root.set_property('Children',[ue.find_struct('BTCompositeChild')(ChildTask=wait,Decorators=[decorator])]);tree.set_property('RootNode',root);board.save_package();tree.save_package();return [dict(stage_only=True,asset=str(stage/p),sha256=hashlib.sha256((stage/p).read_bytes()).hexdigest()) for p in FIXTURES]


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[];children={}
    if any((stage/p).exists() for p in FIXTURES):raise RuntimeError('fresh AI blackboard/tree fixtures required')
    for label in ('passive','cp'):
        relative=ASSETS[label];bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));children[label]=dict(bp=bp,relative=relative,sha256=hashlib.sha256((stage/relative).read_bytes()).hexdigest(),cdo=defaults(bp,label+'-ai-child-before'),templates=construction(bp,output,label+'-ai-child-before'))
        if children[label]['sha256']!=hashlib.sha256((official/relative).read_bytes()).hexdigest():raise RuntimeError('original AI child asset required')
    for label in ('controller','allowed','ammo','reload','focus','shoot'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original shooter AI asset required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=defaults(bp,label+'-ai-before');templates=construction(bp,output,label+'-ai-before');originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original AI graph footprint differs')
        graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];ret=None
        if label=='controller':points=[(event,nodes['K2Node_AsyncAction_2'],'OnReady','ready',()),(event,nodes['K2Node_CallParentFunction_0'],'then','possess',()),(event,nodes['K2Node_CustomEvent_0'],'then','death',()),(event,nodes['K2Node_AsyncAction_0'],'OnTeamChanged','team',())];methods=('ReceiveBeginPlay','ReceivePossess','ReceiveUnPossess','OnDeathStarted')
        elif label in ('ammo','reload','focus'):
            node=next(n for n in event.Nodes if n.get_class().get_name()=='K2Node_Event');param='ControlledPawn' if label=='reload' else 'OwnerController';points=[(event,node,'then',label,((param,node.node_find_pin(param)),))];methods=('ReceiveTickAI',) if label=='ammo' else ('ReceiveActivationAI',)
        elif label=='shoot':
            node=nodes['K2Node_Event_2'];points=[(event,node,'then','shoot',tuple((n,node.node_find_pin(n)) for n in ('OwnerController','ControlledPawn')))];methods=('ReceiveTickAI','GetCurrentWeapon');g=graphs['GetCurrentWeapon'];entry=g.Nodes[0];ret=(g,entry,'weapon',tuple((n,entry.node_find_pin(n)) for n in ('Pawn','Controller')),'CanShoot','CanShoot')
        else:methods=('PerformConditionCheck',);g=graphs['PerformConditionCheck'];ret=(g,g.Nodes[0],'allowed',(),'Allowed','ReturnValue')
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for g,n,pin,key,params in points:
            target,=n.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((n.get_name(),pin),(target.owning_node.get_name(),target.name)))
        if ret:
            g,n,key,params,out,sourceout=ret;target,=n.node_find_pin('then').get_linked_to();ignored[g.get_name()].update(((n.get_name(),'then'),(target.owning_node.get_name(),target.name)));gate(bp,key,params,out)
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals};guids={(g.get_name(),n.get_name()):n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        for g,n,pin,key,params in points:gate(bp,key,params)
        if label=='controller':
            for key,target in (('bind',nodes['K2Node_AssignDelegate_0']),('observe',nodes['K2Node_AsyncAction_0'])):
                node=event.graph_add_node(K2Node_CustomEvent);node.CustomFunctionName=BACKENDS[key];event.graph_reconstruct_node(node);connect(node,'then',target,'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for g,n,pin,key,params in points:
            previous={v.get_name() for v in g.Nodes};insert_gate(g,n,pin,getattr(bp.GeneratedClass,GATES[key]));call,=[v for v in g.Nodes if v.get_name() not in previous and v.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        if ret:
            g,n,key,params,out,sourceout=ret;target,=n.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[key]));branch=g.graph_add_node(K2Node_IfThenElse);n.node_find_pin('then').break_link_to(target);connect(n,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target)
            for name,p in params:p.make_link_to(call.node_find_pin(name))
            old=next(v for v in g.Nodes if v.get_class().get_name()=='K2Node_FunctionResult');early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=old.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,out,early,sourceout)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_ShooterAI'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.shooter_ai_mixin',PythonClass='LyraShooter'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or defaults(bp,label+'-ai-after')!=before or construction(bp,output,label+'-ai-after')!=templates or any(ue.describe_function(bp.GeneratedClass,m)!=v for m,v in signatures.items()):raise RuntimeError('original AI CDO/templates/BT intervals/signatures changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(n.NodeGuid.as_dict()!=guids[g.get_name(),n.get_name()] for g,names in originals for n in g.Nodes if n.get_name() in names):raise RuntimeError('original AI graph/scoped variables/GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('AI transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete shooter AI Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    for label,child in children.items():
        if defaults(child['bp'],label+'-ai-child-after')!=child['cdo'] or construction(child['bp'],output,label+'-ai-child-after')!=child['templates'] or hashlib.sha256((stage/child['relative']).read_bytes()).hexdigest()!=child['sha256']:raise RuntimeError('original passive/CP child bytes/defaults/templates changed')
    fixtures=fixture(stage)
    return dict(status='passed',kind='shooterai',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_templates_scoped_variables_node_guids_bt_schedules_async_factories_health_delegates_parent_calls_and_graphs_preserved=True,passive_empty_overrides_and_cp_parent_forwarder_retained=True,new_business_nodes=0,native_end_adapter_nodes=0,nodes=rows,children={k:dict(relative=v['relative'],sha256=v['sha256']) for k,v in children.items()},fixtures=fixtures,assets=saved)
