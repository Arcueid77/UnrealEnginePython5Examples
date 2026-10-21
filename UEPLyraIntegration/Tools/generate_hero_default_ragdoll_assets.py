"""Only extend the parent DataAsset family; native one-body control is historical."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_FunctionResult
from unreal_engine.structs import UEPPythonMixinProfile,EdGraphPinType
from generate_hero_default_stencil_assets import cdo,RELATIVE
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_characters.hero_default_ragdoll_mixin import CLASS,SELECTOR
from generate_character_ragdoll_probe import audit

def physics_fixture(stage):
    relative='Content/UEPValidation/PA_HeroDefaultRagdollControl.uasset'
    if (stage/relative).exists():raise RuntimeError('fresh parent physics control required')
    source=ue.load_object(ue.find_class('PhysicsAsset'),'/Game/Characters/Heroes/Mannequin/Rig/PA_Mannequin.PA_Mannequin')
    original_relative='Content/Characters/Heroes/Mannequin/Rig/PA_Mannequin.uasset'
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    hashes={str(root/original_relative):hashlib.sha256((root/original_relative).read_bytes()).hexdigest() for root in (official,stage)}
    if len(set(hashes.values()))!=1:raise RuntimeError('official/stage original physics differs')
    asset=ue.duplicate_asset(source.get_path_name(),'/Game/UEPValidation/PA_HeroDefaultRagdollControl','PA_HeroDefaultRagdollControl')
    body,=[v for v in asset.get_property('SkeletalBodySetups') if str(v.get_property('BoneName')).lower()=='pelvis']
    if body.get_outer()!=asset:raise RuntimeError('fixture body must be owned deep copy')
    asset.set_property('SkeletalBodySetups',[body]);asset.set_property('ConstraintSetup',[]);asset.set_property('BoundsBodies',[0]);asset.post_edit_change();asset.save_package()
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=v for p,v in hashes.items()):raise RuntimeError('original physics changed')
    return dict(asset=str(stage/relative),sha256=hashlib.sha256((stage/relative).read_bytes()).hexdigest(),stage_only=True,bodies=1,constraints=0,bone='Pelvis',original_assets_unmodified=True,source_hashes=hashes)
def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroDefaultBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='herodefaultequipment':raise RuntimeError('accepted parent stencil/hide baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('parent equipment family changed')
    original_ragdoll=audit();physics=physics_fixture(stage)
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;digest=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest();ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=cdo(bp,'hero-parent-ragdoll-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};names=('UserConstructionScript','Death','Ragdoll','HideEquippedWeapons','UpdateCustomStencilFromTeamID','AnimMotionEffect','BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_HeroDefaultStencilMixin.DA_HeroDefaultStencilMixin');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.hero_default_ragdoll_mixin',PythonClass='LyraHeroDefaultRagdoll'+p+'Profile') for p in ('Python','BlueprintFallback')]
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=3,BlueprintFallback=3):raise RuntimeError('complete parent stencil/hide/ragdoll family required')
    finally:ue.unregister_all_mixins()
    after=cdo(bp,'hero-parent-ragdoll-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};after_hash={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hash,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'parent-ragdoll-preservation.json').write_text(json.dumps(proof,indent=2))
    if before!=after or shapes!=after_shapes or hashes!=after_hash or proof['bad_guids'] or hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError('original parent bytes/CDO/ABI/graphs/GUID changed')
    caller=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_HeroDefaultRagdollCaller');g=ue.blueprint_add_function(caller,'Run');e=g.Nodes[0];e.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=bp.GeneratedClass),'Target');call=g.graph_add_node_call_function(bp.GeneratedClass.Ragdoll);result=g.graph_add_node(K2Node_FunctionResult);connect(e,'then',call,'execute');connect(e,'Target',call,'self');connect(call,'then',result,'execute');ue.compile_blueprint(caller)
    if int(caller.Status)==2:raise RuntimeError('typed parent Ragdoll caller failed compile')
    caller.save_package();asset.save_package();file=stage/'Content/UEPValidation/BP_HeroDefaultRagdollCaller.uasset'
    return dict(status='passed',kind='herodefaultragdoll',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_parent_bytes_cdo_public_abis_all_nodes_guids_and_business_graphs_preserved=True,only_parent_mixin_data_asset_changed=True,original_parent_selector_and_stencil_method_preserved=True,original_parent_selector_stencil_and_hide_methods_preserved=True,selector=SELECTOR,method_counts=counts,whole_parent_business_migrated=False,remaining_business=['Health death-started native delay orchestration','AnimMotionEffect footstep effects'],new_business_nodes=0,native_end_adapter_nodes=0,original_ragdoll=original_ragdoll,fixture=dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),stage_only=True),physics_control=physics,fixtures=json.loads((baseline/'assets.json').read_text(encoding='utf-8-sig'))['fixtures'],assets=[RELATIVE,'Content/UEPMixins/DA_HeroDefaultStencilMixin.uasset'])
