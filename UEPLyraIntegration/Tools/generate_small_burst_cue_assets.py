"""Keep static Cue/CDO and latent heal parent graphs/templates unchanged."""
import hashlib
import json
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet
from unreal_engine.structs import UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from mixin_graph_gates import semantics
from uep_lyra_weapons.small_burst_cue_mixin import CLASSES

ASSETS={
    'pickup':'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCN_InteractPickUp.uasset',
    'melee':'Plugins/GameFeatures/ShooterCore/Content/GameplayCues/GCN_Weapon_Melee.uasset',
    'heal':'Content/GameplayCueNotifies/GCN_Character_Heal.uasset',
    'grenade':'Plugins/GameFeatures/ShooterCore/Content/Weapons/Grenade/GCN_Grenade_Detonate.uasset'}


def construction(bp,output,prefix):
    obj=bp.get_property('SimpleConstructionScript')
    if obj is None:return None
    result={};objects=[('construction',obj)]+[(node.get_name()+'-component',node.ComponentTemplate) for node in obj.AllNodes if node.ComponentTemplate is not None]
    for label,value in objects:
        path=output/(prefix+'-'+label+'.t3d')
        if not ue.new_object(ue.find_class('ObjectExporterT3D')).export_to_file(value,str(path)):raise RuntimeError('original construction/component templates export failed')
        data=path.read_bytes();result[label]=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    return result


def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent
    output=Path(next(a.split('=',1)[1] for a in __import__('sys').argv if a.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for label,relative in ASSETS.items():
        if hashlib.sha256((stage/relative).read_bytes()).digest()!=hashlib.sha256((official/relative).read_bytes()).digest():raise RuntimeError('fresh original small Burst Cue required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,CLASSES[label].removesuffix('_C'));ue.unregister_all_mixins()
        before=snapshot(bp,label+'-burst-before');signature=ue.describe_function(bp.GeneratedClass,'OnBurst');scs=construction(bp,output,label+'-before')
        originals=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];total=sum(len(n) for _,n in originals);hashes={g.get_name():semantics(g,keys,set()) for g,keys in originals}
        if total!={'pickup':10,'melee':3,'heal':4,'grenade':9}[label]:raise RuntimeError('original small Burst Cue footprint differs')
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_SmallBurst'+label.title()+'CueMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python'
        asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_weapons.small_burst_cue_mixin',PythonClass='LyraSmallBurst'+label.title()+p+'Profile') for p in ('Python','BlueprintFallback')]
        ue.blueprint_configure_mixin(bp,asset,'Python','PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        if int(bp.Status)==2 or snapshot(bp,label+'-burst-after')!=before or ue.describe_function(bp.GeneratedClass,'OnBurst')!=signature:raise RuntimeError('original small Burst CDO/signature/compile changed')
        if construction(bp,output,label+'-after')!=scs or any(semantics(g,keys,set())!=hashes[g.get_name()] for g,keys in originals):raise RuntimeError('original small Burst graphs or component templates changed')
        interface=sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp) if g.get_name() in ('GetPythonMixinSet','GetPythonMixinProfile'))
        if interface!=5 or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))-total!=interface:raise RuntimeError('interface-only small Burst authoring required')
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={n:len(r['functions']) for n,r in row['profiles'].items()}
            if counts!=dict(Python=1,BlueprintFallback=1):raise RuntimeError('complete single-method small Burst Profiles required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[label]=dict(original_graph_nodes=total,interface_nodes=interface,transport_nodes=0,actual_registered_profile_method_counts=counts)
    return dict(status='passed',kind='smallburstcues',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,
        original_full_cdos_signatures_graphs_and_construction_templates_preserved=True,original_static_parent_effects_and_latent_heal_parent_lifetime_preserved=True,
        new_business_nodes=0,native_end_adapter_nodes=0,cues=rows,assets=saved)
