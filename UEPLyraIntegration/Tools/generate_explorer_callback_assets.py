"""Extend exact accepted Explorer style DataAssets; all character bytes stay fixed."""
import hashlib
import json
from pathlib import Path
import sys
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile
from generate_explorer_character_assets import public_shapes,relative
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics
from uep_lyra_characters.explorer_helpers_mixin import CLASSES
from uep_lyra_characters.explorer_callbacks_mixin import METHODS,PARTS_EVENT,HEALTH_EVENT

def shapes(bp):
    values=public_shapes(bp)
    for name in (PARTS_EVENT,HEALTH_EVENT):values[name]=ue.describe_function(bp.GeneratedClass,name)
    return values

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPExplorerCharacterBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'));proof=json.loads((baseline/'assets.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='explorerstyle' or not proof['original_all_graphs_and_native_unarmed_payload_unchanged']:raise RuntimeError('accepted original eight-method Explorer style revision required')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;assets=[];characters={}
    for record in parent['assets']:
        if hashlib.sha256(Path(record['stage']).read_bytes()).hexdigest().upper()!=record['sha256'].upper():raise RuntimeError('Explorer style parent asset changed')
    for key in ('hero','pawn'):
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[key].removesuffix('_C'));ue.unregister_all_mixins();before=canonical_cdo(snapshot(bp,key+'-callbacks-before'));signatures=shapes(bp);originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in originals};guids={n:n.NodeGuid.as_dict() for g,_ in originals for n in g.Nodes}
        name='DA_Explorer'+key.title()+'HelpersMixin';asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/'+name+'.'+name);asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.explorer_callbacks_mixin',PythonClass='LyraExplorerCallbacks'+p+'Profile') for p in ('Python','BlueprintFallback')]
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(value['functions']) for p,value in row['profiles'].items()}
            if counts!=dict(Python=12,BlueprintFallback=12) or set(row['functions'])!=set(METHODS):raise RuntimeError('exact twelve-method Explorer family required')
        finally:ue.unregister_all_mixins()
        after=canonical_cdo(snapshot(bp,key+'-callbacks-after'));after_signatures=shapes(bp)
        if before!=after or signatures!=after_signatures or any(semantics(g,ns,set())!=hashes[g.get_name()] for g,ns in originals) or any(n.NodeGuid.as_dict()!=value for n,value in guids.items()):raise RuntimeError('Explorer callbacks altered original CDO/event ABI/graphs/GUIDs')
        (out/(key+'-callback-preservation.json')).write_text(json.dumps(dict(cdo_before=before,cdo_after=after,signatures_before=signatures,signatures_after=after_signatures,graph_hashes=hashes),indent=2));asset.save_package();assets.extend([relative(key),'Content/UEPMixins/'+name+'.uasset']);characters[key]=dict(method_counts=counts,component_bound_event_abis_preserved=True,original_all_graphs_cdo_signatures_and_guids_unchanged=True,whole_character_migrated=False)
    return dict(status='passed',kind='explorercallbacks',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,native_end_adapter_nodes=0,new_business_nodes=0,original_all_graphs_and_native_unarmed_payload_unchanged=True,original_health_and_parts_component_event_abis_preserved=True,only_mixin_profile_data_assets_changed=True,whole_characters_migrated=False,characters=characters,assets=assets)
