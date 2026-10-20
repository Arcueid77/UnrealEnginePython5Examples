"""Only change Profile DataAssets; retain original five input binding/frame ABIs."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile
from generate_explorer_character_assets import relative,input_bindings
from generate_explorer_beginplay_assets import signatures
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics
from uep_lyra_characters.explorer_helpers_mixin import CLASSES
from uep_lyra_characters.explorer_init_mixin import resolve
from uep_lyra_characters.explorer_input_mixin import bindings

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCharacterBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='explorerbeginplay':raise RuntimeError('accepted twenty-route Explorer startup baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('Explorer startup parent changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];reports={}
    for key in CLASSES:
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();callbacks={k:resolve(bp.GeneratedClass,k) for k in ('team','experience')};before=canonical_cdo(snapshot(bp,key+'-input-before'));sigs=signatures(bp,callbacks);names=bindings(bp.GeneratedClass);input_sigs={n:ue.describe_function(bp.GeneratedClass,name) for n,name in names.items()};original_bindings=input_bindings(bp.GeneratedClass);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/'+name+'.'+name);asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_input_mixin',PythonClass='LyraExplorerInput'+key.title()+p+'Profile') for p in ('Python','BlueprintFallback')]
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict(Python=25,BlueprintFallback=20) or not set(names.values()).issubset(set(row['profiles']['Python']['functions'])) or set(names.values())&set(row['profiles']['BlueprintFallback']['functions']):raise RuntimeError('Explorer input Python/Original fallback method family differs')
        finally:ue.unregister_all_mixins()
        after=canonical_cdo(snapshot(bp,key+'-input-after'));after_sigs=signatures(bp,callbacks)
        if before!=after or sigs!=after_sigs or original_bindings!=input_bindings(bp.GeneratedClass) or names!=bindings(bp.GeneratedClass) or input_sigs!={n:ue.describe_function(bp.GeneratedClass,fn) for n,fn in names.items()} or any(semantics(g,ns,set())!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('Explorer input altered original CDO/ABI/bindings/graphs/GUIDs')
        (out/(key+'-input-preservation.json')).write_text(json.dumps(dict(cdo_before=before,cdo_after=after,signatures_before=sigs,signatures_after=after_sigs,input_signatures=input_sigs,input_bindings=original_bindings,native_receiver_names=names,graph_hashes=hashes),indent=2));asset.save_package();reports[key]=dict(method_counts=counts,native_receiver_names=names,original_action_assets_triggered_bindings_function_frames_and_all_graphs_preserved=True,blueprint_profile_uses_native_original_input_frame=True);assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset'])
    return dict(status='passed',kind='explorerinput',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,original_character_bytes_graphs_cdos_guids_public_abis_and_enhancedinput_bindings_preserved=True,only_mixin_profile_data_assets_changed=True,native_original_finputactionvalue_frames_retained_on_blueprint_fallback=True,whole_characters_migrated=False,characters=reports,assets=assets)
