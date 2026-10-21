"""Migrate Arena player UI lifecycle without rewriting original nine nodes."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics
from uep_lyra_hud.arena_player_ui_mixin import CLASS,TAG

RELATIVE='Plugins/GameFeatures/TopDownArena/Content/UserInterface/Player/B_PlayerUIComponent.uasset'
def sha(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()

def audit(bp):
    graph,=bp.UbergraphPages;nodes=list(graph.Nodes)
    if len(nodes)!=9:raise RuntimeError('original nine component nodes required')
    events={str(n.EventReference.MemberName):n for n in nodes if n.get_class().get_name()=='K2Node_Event'}
    calls={str(n.FunctionReference.MemberName):n for n in nodes if n.get_class().get_name()=='K2Node_CallFunction'}
    if set(events)!={'ReceiveBeginPlay','ReceiveEndPlay'} or set(calls)!={'K2_RegisterExtensionAsData','Unregister','GetOwner'}:raise RuntimeError('original native component calls differ')
    register=calls['K2_RegisterExtensionAsData'];unregister=calls['Unregister']
    def linked(node,pin,source,output):
        actual,=node.node_find_pin(pin).get_linked_to()
        if actual.owning_node!=source or actual.name!=output:raise RuntimeError('original UI lifecycle dataflow differs: '+pin)
    linked(register,'execute',events['ReceiveBeginPlay'],'then');linked(unregister,'execute',events['ReceiveEndPlay'],'then')
    if register.node_find_pin('ExtensionPointTag').default_value!='(TagName="'+TAG+'")' or int(register.node_find_pin('Priority').default_value)!=-1:raise RuntimeError('original extension tag/priority differs')
    cast,=[n for n in nodes if n.get_class().get_name()=='K2Node_DynamicCast']
    if cast.TargetType!=ue.find_class('LyraPlayerState') or any(p.category=='exec' for p in cast.node_pins()):raise RuntimeError('original pure PlayerState cast differs')
    linked(cast,'Object',calls['GetOwner'],'ReturnValue');linked(register,'Data',cast,'AsLyra Player State')
    store,=[n for n in nodes if n.get_class().get_name()=='K2Node_VariableSet'];get,=[n for n in nodes if n.get_class().get_name()=='K2Node_VariableGet']
    if str(store.VariableReference.MemberName)!=str(get.VariableReference.MemberName) or str(store.VariableReference.MemberName)!='ExtensionHandle':raise RuntimeError('original retained handle property differs')
    linked(store,'execute',register,'then');linked(store,'ExtensionHandle',register,'ReturnValue');linked(unregister,'Handle',get,'ExtensionHandle')
    if store.node_find_pin('then').get_linked_to() or unregister.node_find_pin('then').get_linked_to():raise RuntimeError('original registration/unregistration continuation differs')
    return dict(nodes=9,tag=TAG,data='pure_cast<LyraPlayerState>(GetOwner())',priority=-1,context=None,unconditional_unregister=True,reset_handle=False)

def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if sha(stage/RELATIVE)!=sha(official/RELATIVE):raise RuntimeError('fresh original Arena component required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();source=audit(bp);before=snapshot(bp,'arena-player-ui-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in ('ReceiveBeginPlay','ReceiveEndPlay')}
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;asset=ue.create_asset('DA_ArenaPlayerUIMixin','/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_hud.arena_player_ui_mixin',PythonClass='LyraArenaPlayerUI'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=snapshot(bp,'arena-player-ui-after');after_shapes={n:ue.describe_function(bp.GeneratedClass,n) for n in shapes};after_hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'arena-player-ui-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hashes or proof['bad_guids'] or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=14:raise RuntimeError('original component CDO/ABI/graphs/GUIDs changed')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=2,BlueprintFallback=2):raise RuntimeError('only component Begin/End Profiles required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='arenaplayerui',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_graphs_guids_preserved=True,original_ui_policy=source,method_counts=counts,original_nodes=9,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,assets=[RELATIVE,'Content/UEPMixins/DA_ArenaPlayerUIMixin.uasset'])
