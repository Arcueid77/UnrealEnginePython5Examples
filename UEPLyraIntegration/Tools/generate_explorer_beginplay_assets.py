"""Exact original parent call and named Spawned registration, native next-tick resume."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile
from generate_explorer_character_assets import relative
from generate_explorer_init_assets import shapes
from generate_character_begin_play_parent import generate as parent_transport
from generate_character_visibility_transport import generate as visibility_transport
from generate_character_inventory_wait_stub import generate as resume_stub
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics
from uep_lyra_characters.explorer_init_mixin import CLASSES,resolve
from uep_lyra_characters.visibility_mixin import SHOW,RESUME
from uep_lyra_characters.begin_play_mixin import PARENT

def signatures(bp,callbacks):
    values=shapes(bp,callbacks);values[SHOW]=ue.describe_function(bp.GeneratedClass,SHOW);return values
def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCharacterBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='explorerinit':raise RuntimeError('accepted seventeen-method Explorer initialization baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('Explorer initialization parent changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];reports={};pending=[]
    for key in CLASSES:
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();callbacks={k:resolve(bp.GeneratedClass,k) for k in ('team','experience')};before=canonical_cdo(snapshot(bp,key+'-begin-before'));sigs=signatures(bp,callbacks);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes};event=bp.UbergraphPages[0];source=next(n for n in event.Nodes if n.get_class().get_name()=='K2Node_CallParentFunction' and str(n.FunctionReference.MemberName)=='ReceiveBeginPlay')
        registration=next(n for n in event.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='RegisterAndCallForInitStateChange')
        if registration.node_find_pin('RequiredState').default_value!='(TagName="InitState.Spawned")' or registration.node_find_pin('bCallImmediately').default_value!='true':raise RuntimeError('original Explorer Spawned/immediate registration differs')
        native_parent=parent_transport(bp,source);native_registration=visibility_transport(bp);native_resume=resume_stub(bp,RESUME);ue.compile_blueprint(bp);ue.unregister_all_mixins()
        name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/'+name+'.'+name);asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_beginplay_mixin',PythonClass='LyraExplorerBeginPlay'+key.title()+p+'Profile') for p in ('Python','BlueprintFallback')]
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict(Python=20,BlueprintFallback=20) or not {'ReceiveBeginPlay',SHOW,RESUME}.issubset(set(row['functions'])):raise RuntimeError('complete twenty-method Explorer startup family required')
        finally:ue.unregister_all_mixins()
        after=canonical_cdo(snapshot(bp,key+'-begin-after'));after_sigs=signatures(bp,callbacks)
        if int(bp.Status)==2 or before!=after or sigs!=after_sigs or any(semantics(g,ns,set())!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('Explorer BeginPlay changed original CDO/ABI/graphs/GUIDs')
        added=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-sum(len(ns) for _,ns in originals)
        if added!=8:raise RuntimeError('Explorer startup transport footprint differs')
        (out/(key+'-begin-preservation.json')).write_text(json.dumps(dict(cdo_before=before,cdo_after=after,signatures_before=sigs,signatures_after=after_sigs,original_graph_hashes=hashes),indent=2));reports[key]=dict(method_counts=counts,transport_nodes_added=added,parent=native_parent,registration=native_registration,resume=native_resume,required_state='InitState.Spawned',original_cdo_public_signatures_all_graphs_and_guids_preserved=True);pending.extend([bp,asset]);assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset'])
    for obj in pending:obj.save_package()
    return dict(status='passed',kind='explorerbeginplay',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,original_static_parent_begin_and_spawned_registration_payload_preserved=True,original_all_graphs_guids_cdos_and_public_abis_preserved=True,whole_characters_migrated=False,characters=reports,assets=assets)
