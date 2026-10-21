"""Add only parent declared stencil routing with a collision-free selector name."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics
from uep_lyra_characters.hero_default_stencil_mixin import CLASS,SELECTOR
RELATIVE='Content/Characters/Heroes/B_Hero_Default.uasset'
def cdo(bp,label):return '\n'.join(line for line in snapshot(bp,label).splitlines() if not line.strip().startswith(SELECTOR+'='))
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent
    if hashlib.sha256((stage/RELATIVE).read_bytes()).digest()!=hashlib.sha256((official/RELATIVE).read_bytes()).digest():raise RuntimeError('fresh original Hero parent required')
    ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=cdo(bp,'hero-parent-stencil-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};names=('UserConstructionScript','Death','Ragdoll','HideEquippedWeapons','UpdateCustomStencilFromTeamID','AnimMotionEffect','BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature');shapes={name:ue.describe_function(bp.GeneratedClass,name) for name in names}
    if sum(len(ns) for _,ns in original)!=69:raise RuntimeError('original Hero parent full footprint differs')
    factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_HeroDefaultStencilMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.hero_default_stencil_mixin',PythonClass='LyraHeroDefaultStencil'+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python',SELECTOR);ue.compile_blueprint(bp);ue.unregister_all_mixins();after=cdo(bp,'hero-parent-stencil-after');after_shapes={name:ue.describe_function(bp.GeneratedClass,name) for name in names};after_hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(status=int(bp.Status),cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'hero-parent-stencil-preservation.json').write_text(json.dumps(proof,indent=2))
    if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hashes or proof['bad_guids']:raise RuntimeError('original Hero parent CDO/ABI/graphs or GUID changed')
    if sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-69!=5:raise RuntimeError('Hero parent interface-only footprint differs')
    try:
        ue.register_declared_mixin(bp.GeneratedClass);r,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in r['profiles'].items()}
        if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError('one-method parent stencil family required')
    finally:ue.unregister_all_mixins()
    bp.save_package();asset.save_package()
    return dict(status='passed',kind='herodefaultstencil',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_all_parent_cdo_properties_public_abis_nodes_guids_and_business_graphs_preserved=True,unique_parent_selector_avoids_child_owned_python_mixin_profile_collision=True,selector=SELECTOR,original_nodes=69,interface_nodes=5,new_business_nodes=0,native_end_adapter_nodes=0,method_counts=counts,whole_parent_business_migrated=False,remaining_business=['Ragdoll','HideEquippedWeapons','Health death-started native delay orchestration','AnimMotionEffect footstep effects'],assets=[RELATIVE,'Content/UEPMixins/DA_HeroDefaultStencilMixin.uasset'])
