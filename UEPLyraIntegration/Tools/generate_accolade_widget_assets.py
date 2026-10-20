"""Typed return gates preserve native queues and complete widget/animation data."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_FunctionResult,K2Node_IfThenElse
from unreal_engine.structs import EdGraphPinType,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_hud.accolade_widgets_mixin import CLASSES,CONSTRUCT,CREATE,DESTROY,PLAY

ASSETS={k:'Plugins/GameFeatures/ShooterCore/Content/UserInterface/Notifications/Accolades/'+n+'.uasset' for k,n in (('host','W_AccoladeHostWidget'),('toast','W_AccoladeToast'))}


def kind(p):return EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object,ContainerType=p.container_type,bIsReference=p.is_reference,bIsConst=p.is_const)


def visuals(bp,output,label):
    objects=[('tree',bp.get_property('WidgetTree'))]+[(str(i)+'-animation',a) for i,a in enumerate(bp.get_property('Animations'))];values={}
    for name,obj in objects:
        file=output/(label+'-'+name+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(obj,str(file)):raise RuntimeError('native widget visuals export failed')
        data=file.read_bytes();text=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig');values[name]='\n'.join(line for line in text.splitlines() if not line.strip().startswith(('PythonMixinSet=','PythonMixinProfile=')))
    return values


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;output=Path(next(v.split('=',1)[1] for v in __import__('sys').argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    dependencies=['Plugins/GameFeatures/ShooterCore/Content/Accolades/DT_BasicShooterAccolades.uasset','Plugins/GameFeatures/ShooterCore/Content/Accolades/AccoladeDataRegistry.uasset','Plugins/GameFeatures/ShooterCore/Binaries/Win64/UnrealEditor-ShooterCoreRuntime.dll']
    dependency_hashes={r:hashlib.sha256((stage/r).read_bytes()).hexdigest() for r in dependencies};rows={};saved=[]
    for label in ('toast','host'):
        relative=ASSETS[label]
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original accolade widget required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,label+'-accolade-before');templates=visuals(bp,output,label+'-before')
        methods=('Construct','CreateAccoladeWidget','DestroyAccoladeWidget') if label=='host' else ('PlayIntroOutro','Construct','PreConstruct','Tick');signatures={n:ue.describe_function(bp.GeneratedClass,n) for n in methods};originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals)
        if total!={'host':25,'toast':11}[label]:raise RuntimeError('original accolade widget footprint differs')
        graphs={g.get_name():g for g,_ in originals};points=[]
        if label=='toast':points=[(graphs['PlayIntroOutro'],graphs['PlayIntroOutro'].Nodes[0],'then',PLAY,None,None)]
        else:
            event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[(event,nodes['K2Node_Event_1'],'then',CONSTRUCT,None,None),(event,nodes['K2Node_Event_3'],'then',DESTROY,'Widget',nodes['K2Node_Event_3'].node_find_pin('Widget'))]
        ignored={g.get_name():set() for g,_ in originals}
        for graph,node,pin,_,_,_ in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[graph.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        if label=='host':
            source=graphs['CreateAccoladeWidget'];entry=source.Nodes[0];target,=entry.node_find_pin('then').get_linked_to();ignored[source.get_name()].update(((entry.get_name(),'then'),(target.owning_node.get_name(),target.name)))
            gate=ue.blueprint_add_function(bp,CREATE);ge=gate.Nodes[0];ge.node_create_pin(1,kind(entry.node_find_pin('Entry')),'Entry');result=gate.graph_add_node(K2Node_FunctionResult);result.node_create_pin(0,EdGraphPinType(PinCategory='bool'),'UseOriginal');result.node_find_pin('UseOriginal').default_value='true';result.node_create_pin(0,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('UserWidget')),'Widget');connect(ge,'then',result,'execute')
        hashes={g.get_name():semantics(g,n,ignored[g.get_name()]) for g,n in originals}
        for graph,node,pin,name,param,param_pin in points:make_gate(bp,name,param,param_pin)
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for graph,node,pin,name,param,param_pin in points:insert_gate(graph,node,pin,getattr(bp.GeneratedClass,name),param,param)
        if label=='host':
            call=source.graph_add_node_call_function(getattr(bp.GeneratedClass,CREATE));branch=source.graph_add_node(K2Node_IfThenElse);entry.node_find_pin('then').break_link_to(target);connect(entry,'then',call,'execute');connect(entry,'Entry',call,'Entry');connect(call,'then',branch,'execute');connect(call,'UseOriginal',branch,'Condition');branch.node_find_pin('then').make_link_to(target)
            original_result=next(n for n in source.Nodes if n.get_class().get_name()=='K2Node_FunctionResult');early=source.graph_add_node(K2Node_FunctionResult);early.FunctionReference=original_result.FunctionReference;source.graph_reconstruct_node(early);connect(branch,'else',early,'execute');connect(call,'Widget',early,'ReturnValue')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Accolade'+label.title()+'Mixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.accolade_widgets_mixin',PythonClass='LyraAccolade'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-accolade-after')!=before or visuals(bp,output,label+'-after')!=templates or any(ue.describe_function(bp.GeneratedClass,n)!=v for n,v in signatures.items()):raise RuntimeError('original accolade CDO/tree/animation/signatures changed')
        if any(semantics(g,n,ignored[g.get_name()])!=hashes[g.get_name()] for g,n in originals):raise RuntimeError('original accolade graphs changed beyond typed gates')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'));transport={'host':13,'toast':4}[label]
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=transport+5:raise RuntimeError('accolade widget transport footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(r['functions']) for p,r in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),3 if label=='host' else 1):raise RuntimeError('complete accolade presentation Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,transport_nodes=transport,interface_nodes=interface,method_counts=counts)
    if any(hashlib.sha256((stage/r).read_bytes()).hexdigest()!=h for r,h in dependency_hashes.items()):raise RuntimeError('original native queue/registry/data dependencies changed')
    return dict(status='passed',kind='accoladewidgets',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_widget_trees_animations_native_queue_parent_and_business_graphs_preserved=True,localized_text_roundtripped=False,unconnected_toast_stop_branch_remains_unreachable=True,new_business_nodes=0,native_end_adapter_nodes=0,widgets=rows,dependency_hashes=dependency_hashes,assets=saved)
