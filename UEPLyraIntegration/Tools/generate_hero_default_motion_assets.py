"""Extend the accepted parent family without saving its Blueprint again."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,K2Node_FunctionResult
from unreal_engine.structs import UEPPythonMixinProfile
from generate_hero_default_stencil_assets import cdo,RELATIVE
from generate_footstep_assets import kind
from mixin_graph_gates import semantics
from message_payload_graphs import connect
from uep_lyra_characters.hero_default_motion_mixin import CLASS,SELECTOR

def generate(stage):
    baseline=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroDefaultBaseline=')));parent=json.loads((baseline/'summary.json').read_text(encoding='utf-8-sig'));prior=json.loads((baseline/'assets.json').read_text(encoding='utf-8-sig'))
    if parent['status']!='passed' or prior['kind']!='herodefaultdeath':raise RuntimeError('accepted five-method parent baseline required')
    for row in parent['assets']:
        if hashlib.sha256(Path(row['stage']).read_bytes()).hexdigest().upper()!=row['sha256'].upper():raise RuntimeError('parent death baseline changed')
    out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;digest=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest();ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASS.removesuffix('_C'));ue.unregister_all_mixins();before=cdo(bp,'hero-parent-motion-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];hashes={g.get_name():semantics(g,ns,set()) for g,ns in original};guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};names=('UserConstructionScript','Death','Ragdoll','HideEquippedWeapons','UpdateCustomStencilFromTeamID','AnimMotionEffect','BndEvt__HealthComponent_K2Node_ComponentBoundEvent_0_LyraHealth_DeathEvent__DelegateSignature','UEPHeroDefaultAfterDeathDelay');shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};asset=ue.load_object(ue.find_class('UEPPythonMixinSet'),'/Game/UEPMixins/DA_HeroDefaultStencilMixin.DA_HeroDefaultStencilMixin');asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_characters.hero_default_motion_mixin',PythonClass='LyraHeroDefaultMotion'+p+'Profile') for p in ('Python','BlueprintFallback')]
    try:
        ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
        if counts!=dict(Python=6,BlueprintFallback=6):raise RuntimeError('complete six-method parent family required')
    finally:ue.unregister_all_mixins()
    after=cdo(bp,'hero-parent-motion-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in names};after_hash={g.get_name():semantics(g,ns,set()) for g,ns in original};proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hash,bad_guids=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v]);(out/'parent-motion-preservation.json').write_text(json.dumps(proof,indent=2))
    if before!=after or shapes!=after_shapes or hashes!=after_hash or proof['bad_guids'] or hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest()!=digest:raise RuntimeError('accepted parent bytes/CDO/ABI/graphs/GUID changed')
    caller=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/BP_HeroDefaultMotionCaller');g=ue.blueprint_add_function(caller,'CallMotion');e=g.Nodes[0];call=g.graph_add_node_call_function(bp.GeneratedClass.AnimMotionEffect);result=g.graph_add_node(K2Node_FunctionResult)
    for pin in call.node_pins():
        if pin.direction==0 and pin.category not in ('exec','delegate'):
            name='Target' if pin.name=='self' else pin.name;e.node_create_pin(1,kind(pin),name);connect(e,name,call,pin.name)
    connect(e,'then',call,'execute');connect(call,'then',result,'execute');ue.compile_blueprint(caller)
    if int(caller.Status)==2:raise RuntimeError('typed parent motion caller failed compile')
    caller.save_package();asset.save_package();file=stage/'Content/UEPValidation/BP_HeroDefaultMotionCaller.uasset'
    return dict(status='passed',kind='herodefaultmotion',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_parent_bytes_cdo_public_abis_all_nodes_guids_and_business_graphs_preserved=True,only_parent_mixin_data_asset_changed=True,original_parent_selector_and_stencil_method_preserved=True,original_parent_selector_stencil_and_hide_methods_preserved=True,original_parent_selector_stencil_hide_ragdoll_and_death_methods_preserved=True,selector=SELECTOR,method_counts=counts,whole_parent_business_migrated=False,remaining_business=['AnimMotionEffect client/server runtime acceptance'],new_business_nodes=0,native_end_adapter_nodes=0,motion_caller=dict(asset=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),stage_only=True),fixture=prior['fixture'],physics_control=prior['physics_control'],fixtures=prior['fixtures'],assets=[RELATIVE,'Content/UEPMixins/DA_HeroDefaultStencilMixin.uasset'])
