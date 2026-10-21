"""Only the parent DataAsset family changes; original parent bytes stay fixed."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint
from unreal_engine.structs import UEPPythonMixinProfile
from generate_hero_default_stencil_assets import cdo,RELATIVE
from mixin_graph_gates import semantics
from uep_lyra_characters.hero_default_equipment_mixin import CLASS,SELECTOR
def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroDefaultBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or parent['kind']!='herodefaultstencil':raise RuntimeError('accepted parent stencil baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('parent stencil assets changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;digest=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest();ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=cdo(bp,'hero-parent-hide-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};names=('UserConstructionScript','Death','Ragdoll','HideEquippedWeapons','UpdateCustomStencilFromTeamID','AnimMotionEffect','BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_HeroDefaultStencilMixin.DA_HeroDefaultStencilMixin');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.hero_default_equipment_mixin',PythonClass='LyraHeroDefaultEquipment'+p+'Profile') for p in ('Python','BlueprintFallback')]
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=2,BlueprintFallback=2):raise RuntimeError('complete parent stencil/hide family required')
    finally:ue.unregister_all_mixins()
    after=cdo(bp,'hero-parent-hide-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};after_hash={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hash,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'parent-hide-preservation.json').write_text(json.dumps(proof,indent=2))
    if before!=after or shapes!=after_shapes or hashes!=after_hash or proof['bad_guids'] or hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError('parent bytes/CDO/ABI/graphs/GUID changed')
    # Stage-only native virtual caller and equipment definitions; no production grants.
    from unreal_engine.classes import K2Node_FunctionResult
    from unreal_engine.structs import EdGraphPinType
    from message_payload_graphs import connect
    caller=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_HeroDefaultEquipmentCaller');g=ue.blueprint_add_function(caller,'Hide');e=g.Nodes[0];e.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=bp.GeneratedClass),'Target');call=g.graph_add_node_call_function(bp.GeneratedClass.HideEquippedWeapons);result=g.graph_add_node(K2Node_FunctionResult);connect(e,'then',call,'execute');connect(e,'Target',call,'self');connect(call,'then',result,'execute');ue.compile_blueprint(caller);fixtures=[];pending=[caller]
    for key,instance,actor_count in (('Weapon','LyraWeaponInstance',2),('Other','LyraEquipmentInstance',1),('EmptyWeapon','LyraWeaponInstance',0)):
        name='BP_ParentHide'+key+'Definition';fixture=ue.create_blueprint(ue.find_class('LyraEquipmentDefinition'),'/Game/UEPValidation/'+name);ue.compile_blueprint(fixture);defaults=fixture.GeneratedClass.get_cdo();defaults.set_property('InstanceType',ue.find_class(instance));defaults.set_property('AbilitySetsToGrant',[]);defaults.set_property('ActorsToSpawn',[ue.find_struct('LyraEquipmentActorToSpawn')(ActorToSpawn=ue.find_class('Actor'),AttachSocket='None',AttachTransform=ue.FTransform()) for _ in range(actor_count)]);pending.append(fixture)
    if any(int(obj.Status)==2 for obj in pending):raise RuntimeError('parent equipment native fixtures failed compile')
    for obj in pending:obj.save_package();name=obj.get_name();file=stage/'Content/UEPValidation'/(name+'.uasset');fixtures.append(dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),stage_only=True,package='/Game/UEPValidation/'+name+'.'+name+'_C'))
    asset.save_package()
    return dict(status='passed',kind='herodefaultequipment',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_parent_bytes_cdo_public_abis_all_nodes_guids_and_business_graphs_preserved=True,only_parent_mixin_data_asset_changed=True,original_parent_selector_and_stencil_method_preserved=True,selector=SELECTOR,method_counts=counts,whole_parent_business_migrated=False,remaining_business=['Ragdoll','Health death-started native delay orchestration','AnimMotionEffect footstep effects'],new_business_nodes=0,native_end_adapter_nodes=0,fixtures=fixtures,assets=[RELATIVE,'Content/UEPMixins/DA_HeroDefaultStencilMixin.uasset'])
