"""Preserve all parent business graphs; add one empty native latent entry."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile
from generate_hero_default_stencil_assets import cdo,RELATIVE
from generate_character_death_transport import audit
from generate_character_inventory_wait_stub import generate as declare
from mixin_graph_gates import semantics
from uep_lyra_characters.hero_default_death_mixin import CLASS,SELECTOR,RESUME

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroDefaultBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'));prior=json.loads((baseline/'assets.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='herodefaultragdoll':raise RuntimeError('accepted three-method parent baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('parent baseline changed')
    for row in [prior['fixture'],prior['physics_control']]+prior['fixtures']:
        if hashlib.sha256(Path(row['asset']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('accepted native fixture changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=cdo(bp,'hero-parent-death-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};names=('UserConstructionScript','Death','Ragdoll','HideEquippedWeapons','UpdateCustomStencilFromTeamID','AnimMotionEffect','BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};original_death=audit();transport=declare(bp,RESUME)
    asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_HeroDefaultStencilMixin.DA_HeroDefaultStencilMixin');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.hero_default_death_mixin',PythonClass='LyraHeroDefaultDeath'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.compile_blueprint(bp);ue.unregister_all_mixins()
    after=cdo(bp,'hero-parent-death-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};after_hash={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hash,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'parent-death-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hash or proof['bad_guids']:raise RuntimeError('original parent CDO/ABI/graphs/GUID changed')
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-sum(len(ns) for _,ns in original)!=2:raise RuntimeError('only empty int32 continuation declaration permitted')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=5,BlueprintFallback=5):raise RuntimeError('complete five-method parent family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='herodefaultdeath',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_parent_bytes_cdo_public_abis_all_nodes_guids_and_business_graphs_preserved=False,original_parent_cdo_public_abis_all_nodes_guids_and_business_graphs_preserved=True,only_parent_mixin_data_asset_changed=False,only_empty_native_continuation_and_mixin_data_asset_changed=True,original_parent_selector_and_stencil_method_preserved=True,original_parent_selector_stencil_and_hide_methods_preserved=True,original_parent_selector_stencil_hide_and_ragdoll_methods_preserved=True,selector=SELECTOR,method_counts=counts,whole_parent_business_migrated=False,remaining_business=['AnimMotionEffect footstep effects'],new_business_nodes=0,native_end_adapter_nodes=0,native_continuation_nodes=2,transport=transport,original_death=original_death,fixture=prior['fixture'],physics_control=prior['physics_control'],fixtures=prior['fixtures'],assets=[RELATIVE,'Content/UEPMixins/DA_HeroDefaultStencilMixin.uasset'])
