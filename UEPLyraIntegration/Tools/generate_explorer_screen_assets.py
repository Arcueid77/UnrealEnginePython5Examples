"""Add declared one-method Profiles; preserve complete original Explorer screens."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from generate_accolade_widget_assets import visuals
from mixin_graph_gates import semantics
from uep_lyra_hud.explorer_screens_mixin import CLASSES

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];widgets={}
    for kind,cls in CLASSES.items():
        relative='Plugins/GameFeatures/ShooterExplorer/Content/UserInterface/'+cls.rsplit('/',1)[-1].split('.')[0]+'.uasset'
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original Explorer screen required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,cls.removesuffix('_C'));ue.unregister_all_mixins();before=snapshot(bp,kind+'-screen-before');design=visuals(bp,out,kind+'-before');shape=ue.describe_function(bp.GeneratedClass,'BP_OnDeactivated');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};hashes={g.get_name():semantics(g,n,set()) for g,n in original}
        if sum(len(n) for _,n in original)!=3:raise RuntimeError('original Explorer deactivation footprint differs')
        event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};call=nodes['K2Node_CallFunction_14']
        if str(call.FunctionReference.MemberName)!='PopContentFromLayer' or call.FunctionReference.MemberParent!=ue.find_class('CommonUIExtensions'):raise RuntimeError('original native layer removal target differs')
        if nodes['K2Node_Event_2'].node_find_pin('then').get_linked_to()[0].owning_node!=call or call.node_find_pin('ActivatableWidget').get_linked_to()[0].owning_node!=nodes['K2Node_Self_1']:raise RuntimeError('original deactivation/self dataflow differs')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Explorer'+kind.title()+'ScreenMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.explorer_screens_mixin',PythonClass='LyraExplorerScreen'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,kind+'-screen-after')!=before or visuals(bp,out,kind+'-after')!=design or ue.describe_function(bp.GeneratedClass,'BP_OnDeactivated')!=shape:raise RuntimeError('original Explorer screen defaults/visuals/public signature changed')
        if any(semantics(g,n,set())!=hashes[g.get_name()] for g,n in original) or any(n.NodeGuid.as_dict()!=v for n,v in guids.items()):raise RuntimeError('original screen graph/GUID changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=8:raise RuntimeError('screen interface-only footprint differs')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError('one original deactivation method per Profile required')
        finally:ue.unregister_all_mixins()
        proof=dict(cdo=before,signature=shape,graph_hashes=hashes,original_node_guids={n.get_name():v for n,v in guids.items()},method_counts=counts,original_nodes=3,interface_nodes=5,new_business_nodes=0);(out/(kind+'-preservation.json')).write_text(json.dumps(proof,indent=2));widgets[kind]=proof;bp.save_package();asset.save_package();assets.extend([relative,'Content/UEPMixins/'+name+'.uasset'])
    return dict(status='passed',kind='explorerscreens',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdos_widget_trees_animations_signatures_guids_and_all_graphs_preserved=True,only_five_native_mixin_interface_nodes_per_widget_added=True,native_end_adapter_nodes=0,new_business_nodes=0,widgets=widgets,assets=assets)
