"""Keep original latent Delay, dynamic timer delegates/handles and rich-text data."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse,K2Node_CustomEvent
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from generate_message_widget_assets import move_node
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.credits_widgets_mixin import CLASSES,GATES,START,STOP,WRITE,DELAY,PREFIX,SUFFIX

ASSETS={k:'Content/UI/Credits/'+p.rsplit('/',1)[-1].split('.')[0]+'.uasset' for k,p in CLASSES.items()}
TOTAL=dict(credits=54,bar=13)
TRANSPORT=dict(credits=39,bar=13)
COUNTS=dict(credits=7,bar=3)

def gate(bp,label,key,params,output=None):
    g=ue.blueprint_add_function(bp,GATES[label][key]);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    if key=='focus':entry.set_property('ExtraFlags',int(entry.get_property('ExtraFlags'))|0x40000000)
    for name,p in params:entry.node_create_pin(1,kind(p),name)
    result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal' if output else 'ReturnValue');result.node_find_pin('UseOriginal' if output else 'ReturnValue').default_value='true'
    if output:result.node_create_pin(0,kind(output),'ReturnValue' if key=='focus' else 'IsVisible')
    connect(entry,'then',result,'execute')

def move_group(bp,source,nodes,name,members,entry_target,last):
    links=[(n.get_name(),p.name,q.owning_node.get_name(),q.name) for n in source.Nodes if n.get_name() in members for p in n.node_pins() if p.direction==1 for q in p.get_linked_to() if q.owning_node.get_name() in members];g=ue.blueprint_add_function(bp,name);entry=g.Nodes[0];result=g.graph_add_node(K2Node_FunctionResult)
    for member in members:move_node(source,g,nodes[member])
    for a,p,b,q in links:connect(nodes[a],p,nodes[b],q)
    connect(entry,'then',nodes[entry_target],'execute');connect(nodes[last],'then',result,'execute');return g

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original credits widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-credits-before');templates=visuals(bp,output,label+'-before');graphs={g.get_name():g for g in ue.blueprint_get_all_graphs(bp)};originals=[(g,{n.get_name() for n in g.Nodes}) for g in graphs.values()];total=sum(len(n) for _,n in originals)
        if total!=TOTAL[label]:raise RuntimeError('original credits widget footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];groups={};helpers={};ret=None
        if label=='credits':
            for method,key,param in (('ScrollCredits','scroll',None),('ToggleScrollTimer','toggle','EnableTimer'),('Reset','reset',None),('CaptureEndPoint','capture',None)):
                g=graphs[method];entry=g.Nodes[0];points.append((g,entry,'then',key,((param,entry.node_find_pin(param)),) if param else ()))
            points.extend(((event,nodes['K2Node_Event_0'],'then','construct',()),(event,nodes['K2Node_Event_29'],'then','activate',())));g=graphs['BP_GetDesiredFocusTarget'];ret=(g,g.Nodes[0],next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult'),'focus','ReturnValue');timer=graphs['ToggleScrollTimer'];tn={n.get_name():n for n in timer.Nodes};groups={START:(timer,{'K2Node_Self_683','K2Node_CreateDelegate_1573','K2Node_CallFunction_48471','K2Node_VariableSet_1145'},'K2Node_CallFunction_48471','K2Node_VariableSet_1145'),STOP:(timer,{'K2Node_CallFunction_630','K2Node_VariableGet_2875'},'K2Node_CallFunction_630','K2Node_CallFunction_630'),WRITE:(event,{'K2Node_VariableGet_0','K2Node_CallFunction_1','K2Node_VariableGet_2','K2Node_CallFunction_2'},'K2Node_CallFunction_1','K2Node_CallFunction_1')}
            if nodes['K2Node_CommutativeAssociativeBinaryOperator_0'].node_find_pin('B').default_value!=PREFIX or nodes['K2Node_CommutativeAssociativeBinaryOperator_0'].node_find_pin('D').default_value!=SUFFIX:raise RuntimeError('original rich-text template bytes differ')
        else:
            g=graphs['ResetVisibility'];points=[(g,g.Nodes[0],'then','reset',()),(event,nodes['K2Node_ComponentBoundEvent_0'],'then','click',())];g=graphs['GetCurrentVisibility'];ret=(g,g.Nodes[0],next(n for n in g.Nodes if n.get_class().get_name()=='K2Node_FunctionResult'),'visible','IsVisible')
        methods=set()
        for g,_ in originals:
            if g.get_name()!='EventGraph':methods.add(g.get_name())
            for n in g.Nodes:
                if n.get_class().get_name()=='K2Node_Event':methods.add(str(n.EventReference.MemberName))
                if n.get_class().get_name()=='K2Node_ComponentBoundEvent':methods.add(str(n.CustomFunctionName))
        signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods};ignored={g.get_name():set() for g,_ in originals}
        for g,node,pin,key,params in points+[(ret[0],ret[1],'then',ret[3],())]:
            target,=node.node_find_pin(pin).get_linked_to();ignored[g.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        moved_by_graph={g.get_name():set().union(*(members for src,members,_,_ in groups.values() if src==g)) if any(src==g for src,_,_,_ in groups.values()) else set() for g,_ in originals};hashes={g.get_name():semantics(g,n-moved_by_graph[g.get_name()],ignored[g.get_name()]) for g,n in originals};group_hash={name:semantics(src,members,set()) for name,(src,members,_,_) in groups.items()};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        if label=='credits':
            binding=dict(name=str(tn['K2Node_CreateDelegate_1573'].SelectedFunctionName),guid=tn['K2Node_CreateDelegate_1573'].SelectedFunctionGuid.as_dict());(output/'timer-binding-before.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
        for name,(source,members,target,last) in groups.items():helpers[name]=move_group(bp,source,{n.get_name():n for n in source.Nodes},name,members,target,last)
        if label=='credits':tn['K2Node_CreateDelegate_1573'].SelectedFunctionName='ScrollCredits';tn['K2Node_CreateDelegate_1573'].SelectedFunctionGuid=ue.find_struct('Guid')(**binding['guid'])
        for g,node,pin,key,params in points:gate(bp,label,key,params)
        gate(bp,label,ret[3],(),ret[2].node_find_pin(ret[4]))
        if label=='credits':alias=event.graph_add_node(K2Node_CustomEvent);alias.CustomFunctionName=DELAY;event.graph_reconstruct_node(alias);connect(alias,'then',nodes['K2Node_CallFunction_3798'],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2:raise RuntimeError('credits native timer/text declaration compile failed')
        if label=='credits':
            timer=graphs['ToggleScrollTimer'];start=timer.graph_add_node_call_function(getattr(bp.GeneratedClass,START));stop=timer.graph_add_node_call_function(getattr(bp.GeneratedClass,STOP));connect(tn['K2Node_IfThenElse_3792'],'then',start,'execute');connect(tn['K2Node_Knot_5406'],'OutputPin',stop,'execute');write=event.graph_add_node_call_function(getattr(bp.GeneratedClass,WRITE));connect(nodes['K2Node_MacroInstance_0'],'Completed',write,'execute')
        for g,node,pin,key,params in points:
            prior={n.get_name() for n in g.Nodes};insert_gate(g,node,pin,getattr(bp.GeneratedClass,GATES[label][key]));call,=[n for n in g.Nodes if n.get_name() not in prior and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:p.make_link_to(call.node_find_pin(name))
        g,entry,result,key,out=ret;target,=entry.node_find_pin('then').get_linked_to();call=g.graph_add_node_call_function(getattr(bp.GeneratedClass,GATES[label][key]));branch=g.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target);early=g.graph_add_node(K2Node_FunctionResult);early.FunctionReference=result.FunctionReference;g.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'ReturnValue' if key=='focus' else 'IsVisible',early,out)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset_name='DA_Credits'+label.title()+'Mixin';asset=ue.create_asset(asset_name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.credits_widgets_mixin',PythonClass='LyraCredits'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins();current={m:ue.describe_function(bp.GeneratedClass,m) for m in signatures};comparison={m:dict(v) for m,v in current.items()}
        if label=='credits':
            delta=signatures['ToggleScrollTimer']['flags']^current['ToggleScrollTimer']['flags']
            if delta not in (0,0x00800000):raise RuntimeError('unexpected timer public signature flag delta')
            comparison['ToggleScrollTimer']['flags']=signatures['ToggleScrollTimer']['flags']
        (output/(label+'-signatures.json')).write_text(json.dumps(dict(before=signatures,after=current),indent=2),encoding='utf-8')
        if int(bp.Status)==2 or snapshot(bp,label+'-credits-after')!=before or visuals(bp,output,label+'-after')!=templates or comparison!=signatures:raise RuntimeError('credits CDO/visual/public signature changed')
        if any(semantics(g,n-moved_by_graph[g.get_name()],ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals) or any(semantics(helpers[name],members,set())!=group_hash[name] for name,(_,members,_,_) in groups.items()) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original credits graph/timer/text partitions or GUIDs changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=TRANSPORT[label]+5:raise RuntimeError('credits transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[label]):raise RuntimeError('complete credits Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+asset_name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=TRANSPORT[label],interface_nodes=interface,method_counts=counts)
    return dict(status='passed',kind='creditswidgets',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_public_signatures_node_guids_and_partitions_preserved=True,original_one_second_delay_and_point01_looping_timer_delegate_handle_clear_nodes_retained=True,original_timer_max_once_per_frame_false=True,original_rich_string_templates_and_native_string_to_text_setter_preserved=True,original_no_deactivation_or_destruct_timer_cleanup_added=True,source_visibility_compares_only_collapsed_and_const_null_focus_preserved=True,only_compiler_internal_timer_frame_hasdefaults_flag_may_move=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,assets=saved)
