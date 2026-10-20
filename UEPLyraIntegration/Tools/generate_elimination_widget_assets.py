"""Keep native list subscriptions/delegates/timer; gate presentation policy."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_CustomEvent,K2Node_CallDelegate
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals,kind
from mixin_graph_gates import semantics,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.elimination_widgets_mixin import CLASSES,GATES,START,EMIT

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/UserInterface/Notifications/EliminationFeed/'+n+'.uasset' for k,n in (('feed','W_EliminationFeed'),('entry','W_EliminationFeedEntryWidget'))}


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    deps={r:hashlib.sha256((stage/r).read_bytes()).hexdigest() for r in ('Plugins/GameFeatures/ShooterCore/Content/UserInterface/Notifications/EliminationFeed/ElimFeedEntry.uasset','Plugins/GameFeatures/ShooterCore/Content/UserInterface/Notifications/EliminationFeed/EliminationFeedMessage.uasset')}
    for label in ('entry','feed'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original elimination widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-elim-before');templates=visuals(bp,output,label+'-before');methods=('OnInitialized','RemoveToast','UpdateDisplayVisibility') if label=='feed' else ('OnListItemObjectSet','OnTimerElapsed','SetTeamColors','SetWeaponIconAndNameText','Construct','PreConstruct');signatures={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
        originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!={'feed':23,'entry':85}[label]:raise RuntimeError('original elimination widget footprint differs')
        graphs={g.get_name():g for g,_ in originals};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes}
        if label=='feed':
            listener=nodes['K2Node_AsyncAction_ListenForGameplayMessages_0']
            if listener.node_find_pin('MatchType').default_value!='ExactMatch' or listener.node_find_pin('Channel').default_value!='(TagName="Lyra.AddNotification.KillFeed")':raise RuntimeError('original feed listener differs')
            points=[(event,listener,'OnMessageReceived','message',(('Payload',listener.node_find_pin('Payload')),)),(event,nodes['K2Node_CustomEvent_0'],'then','remove',(('ItemPtr',nodes['K2Node_CustomEvent_0'].node_find_pin('ItemPtr')),)),(graphs['UpdateDisplayVisibility'],graphs['UpdateDisplayVisibility'].Nodes[0],'then','visibility',())]
        else:
            text_entry=graphs['SetWeaponIconAndNameText'].Nodes[0]
            points=[(graphs['SetTeamColors'],graphs['SetTeamColors'].Nodes[0],'then','colors',()),(graphs['SetWeaponIconAndNameText'],text_entry,'then','text',tuple((n,text_entry.node_find_pin(n)) for n in ('AttackerName','AttackeeName','InstigatorTags'))),(event,nodes['K2Node_DynamicCast_1'],'then','assign',(('Item',nodes['K2Node_DynamicCast_1'].node_find_pin('AsElim Feed Entry')),)),(event,nodes['K2Node_CustomEvent_0'],'then','expire',())]
        ignored={g.get_name():set() for g,_ in originals}
        for graph,node,out,key,params in points:
            target,=node.node_find_pin(out).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),out),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals}
        for graph,node,out,key,params in points:
            gate=ue.blueprint_add_function(bp,GATES[key]);entry=gate.Nodes[0];result=gate.graph_add_node(K2Node_FunctionResult)
            for n,p in params:entry.node_create_pin(1,kind(p),n)
            result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'ReturnValue');result.node_find_pin('ReturnValue').default_value='true';connect(entry,'then',result,'execute')
        if label=='entry':
            start=event.graph_add_node(K2Node_CustomEvent);start.CustomFunctionName=START;event.graph_reconstruct_node(start);connect(start,'then',nodes['K2Node_CallFunction_2'],'execute')
            emit=ue.blueprint_add_function(bp,EMIT);entry=emit.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('Object')),'ItemPtr');call=ue.new_object(K2Node_CallDelegate);call.DelegateReference=nodes['K2Node_CallDelegate_0'].DelegateReference;emit.graph_add_node(call);connect(entry,'then',call,'execute');connect(entry,'ItemPtr',call,'ItemPtr')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,out,key,params in points:
            old={n.get_name() for n in graph.Nodes};insert_gate(graph,node,out,getattr(bp.GeneratedClass,GATES[key]));call,=[n for n in graph.Nodes if n.get_name() not in old and n.get_class().get_name()=='K2Node_CallFunction']
            for name,p in params:connect(p.owning_node,p.name,call,name)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Elimination'+('List' if label=='feed' else 'Entry')+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.elimination_widgets_mixin',PythonClass='LyraElimination'+('List' if label=='feed' else 'Entry')+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-elim-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('original feed/entry CDO/visuals/animation/signatures changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original elimination widget graph changed beyond typed gates')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport={'feed':12,'entry':19}[label]
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=transport+5:raise RuntimeError('elimination widget transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),3 if label=='feed' else 4):raise RuntimeError('complete elimination widget Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts)
    if any(hashlib.sha256((stage/r).read_bytes()).hexdigest()!=h for r,h in deps.items()):raise RuntimeError('original item/UDS data dependency changed')
    return dict(status='passed',kind='eliminationwidgets',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_widget_trees_animations_exact_listener_list_binding_timer_delegate_and_graphs_preserved=True,native_expiry_seconds=6.,expiry_uses_current_list_item=True,unconnected_construct_set_colors_stays_unreachable=True,source_split_screen_filter_todo_unchanged=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,dependency_hashes=deps,assets=saved)
