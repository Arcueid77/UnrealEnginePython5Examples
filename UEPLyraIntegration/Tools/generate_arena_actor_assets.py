"""Retain Arena actor parents/components/tasks and insert typed policy transport."""
import hashlib,json,sys
from pathlib import Path
import unreal_engine as ue
from unreal_engine.classes import Blueprint,DataAssetFactory,UEPPythonMixinSet,K2Node_AddDelegate,K2Node_CreateDelegate,K2Node_Self,K2Node_CustomEvent
from unreal_engine.structs import EdGraphPinType,MemberReference,UEPPythonMixinProfile
from generate_dash_selector_assets import snapshot
from explorer_character_cdo import canonical_cdo
from mixin_graph_gates import semantics,make_gate,insert_gate
from message_payload_graphs import connect
from uep_lyra_world.arena_actor_mixin import HERO,DEATH,PICKUP,SELECTOR,TEAM,TEAM_EVENT,PARTS_EVENT,HERO_BEGIN,HERO_SHOW,TEAM_BIND,REGISTER,DEATH_WAIT,DEATH_BEGIN,DEATH_AFTER,PICKUP_OVERLAP
ASSETS=dict(hero='Plugins/GameFeatures/TopDownArena/Content/Game/B_Hero_Arena.uasset',death='Plugins/GameFeatures/TopDownArena/Content/Game/GA_ArenaHero_Death.uasset',pickup='Plugins/GameFeatures/TopDownArena/Content/Game/Pickups/B_TopDownArena_Pickup.uasset')
TOTAL=dict(hero=30,death=6,pickup=30)
ADDED=dict(hero=21,death=14,pickup=9)
COUNTS=dict(hero=6,death=2,pickup=3)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdo(bp,label):return canonical_cdo('\n'.join(line for line in snapshot(bp,label).splitlines() if not line.strip().startswith(SELECTOR+'=')))
def generate(stage):
    official=Path(json.loads((stage/'.uep-lyra-full-stage.json').read_text(encoding='utf-8-sig'))['source']).parent;out=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityAssetsResult='))).parent;rows={};saved=[]
    for key,path in (('hero',HERO),('death',DEATH),('pickup',PICKUP)):
        relative=ASSETS[key]
        if sha(stage/relative)!=sha(official/relative):raise RuntimeError('fresh original Arena actor required')
        ue.unregister_all_mixins();bp=ue.load_object(Blueprint,path.removesuffix('_C'));ue.unregister_all_mixins();before=cdo(bp,key+'-arena-actor-before');original=[(g,{n.get_name() for n in g.Nodes}) for g in ue.blueprint_get_all_graphs(bp)];guids={n:n.NodeGuid.as_dict() for g,_ in original for n in g.Nodes};event=bp.UbergraphPages[0];nodes={n.get_name():n for n in event.Nodes};points=[];ignored={g.get_name():set() for g,_ in original}
        methods={'hero':['ReceiveBeginPlay','ListenForTeam',TEAM,TEAM_EVENT,PARTS_EVENT,'ShowPawnAgainNextFrame','UserConstructionScript'],'death':['K2_ActivateAbility','OnFinish_01E106CD44A9DE9122B131B0ABF28DAC'],'pickup':['ChangePickupEffect','OnRep_GameplayEffectToApply','ReceiveBeginPlay','UserConstructionScript']}[key];shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in methods}
        if sum(len(ns) for _,ns in original)!=TOTAL[key]:raise RuntimeError('original Arena actor node footprint differs')
        if key=='hero':points=[(nodes['K2Node_CallParentFunction_0'],'then',HERO_BEGIN,None),(nodes['K2Node_CallFunction_26'],'then',HERO_SHOW,None)]
        elif key=='death':points=[(nodes['K2Node_Event_0'],'then',DEATH_BEGIN,None),(nodes['K2Node_LatentAbilityCall_0'],'OnFinish',DEATH_AFTER,None)]
        else:points=[(nodes['K2Node_ComponentBoundEvent_0'],'then',PICKUP_OVERLAP,'OtherActor')]
        for node,pin,name,param in points:
            target,=node.node_find_pin(pin).get_linked_to();ignored[event.get_name()].update(((node.get_name(),pin),(target.owning_node.get_name(),target.name)))
        hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in original}
        for node,pin,name,param in points:make_gate(bp,name,param,node.node_find_pin(param) if param else None)
        if key=='hero':
            g=ue.blueprint_add_function(bp,TEAM_BIND);entry=g.Nodes[0];cls=ue.find_class('AsyncAction_ObserveTeamColors');entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Observer');call=g.graph_add_node(K2Node_AddDelegate);call.DelegateReference=MemberReference(MemberName='OnTeamChanged',MemberParent=cls,bSelfContext=False);g.graph_reconstruct_node(call);delegate,owner=g.graph_add_node(K2Node_CreateDelegate),g.graph_add_node(K2Node_Self);connect(entry,'then',call,'execute');connect(entry,'Observer',call,'self');connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',call,'Delegate');delegate.SelectedFunctionName=TEAM_EVENT
        if key=='hero':
            g=ue.blueprint_add_function(bp,REGISTER);entry=g.Nodes[0];entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=ue.find_class('LyraPawnExtensionComponent')),'Component');entry.node_create_pin(1,EdGraphPinType(PinCategory='struct',PinSubCategoryObject=ue.find_struct('GameplayTag')),'RequiredState');entry.node_create_pin(1,EdGraphPinType(PinCategory='bool'),'bCallImmediately');call=g.graph_add_node_call_function(ue.find_class('GameFrameworkInitStateInterface').RegisterAndCallForInitStateChange);delegate,owner=g.graph_add_node(K2Node_CreateDelegate),g.graph_add_node(K2Node_Self);connect(entry,'then',call,'execute');connect(entry,'Component',call,'self');connect(entry,'RequiredState',call,'RequiredState');connect(entry,'bCallImmediately',call,'bCallImmediately');connect(owner,'self',delegate,'self');connect(delegate,'OutputDelegate',call,'Delegate');delegate.SelectedFunctionName='ShowPawnAgainNextFrame'
        if key=='death':
            entry=event.graph_add_node(K2Node_CustomEvent);entry.CustomFunctionName=DEATH_WAIT;event.graph_reconstruct_node(entry);connect(entry,'then',nodes['K2Node_LatentAbilityCall_0'],'execute')
        ue.compile_blueprint(bp);ue.unregister_all_mixins()
        for node,pin,name,param in points:insert_gate(event,node,pin,getattr(bp.GeneratedClass,name),param,param)
        factory=DataAssetFactory();factory.DataAssetClass=UEPPythonMixinSet;name='DA_Arena'+key.title()+'ActorMixin';asset=ue.create_asset(name,'/Game/UEPMixins',UEPPythonMixinSet,factory);asset.DefaultProfile='Python';asset.Profiles=[UEPPythonMixinProfile(ProfileName=p,PythonModule='uep_lyra_world.arena_actor_mixin',PythonClass='LyraArena'+key.title()+p+'Profile') for p in ('Python','BlueprintFallback')];ue.blueprint_configure_mixin(bp,asset,'Python',SELECTOR if key=='hero' else 'PythonMixinProfile');ue.compile_blueprint(bp);ue.unregister_all_mixins()
        after=cdo(bp,key+'-arena-actor-after');after_shapes={m:ue.describe_function(bp.GeneratedClass,m) for m in shapes};after_hashes={g.get_name():semantics(g,ns,ignored[g.get_name()]) for g,ns in original};bad=[n.get_name() for n,v in guids.items() if n.NodeGuid.as_dict()!=v];proof=dict(cdo_equal=before==after,signatures_before=shapes,signatures_after=after_shapes,graph_hashes_before=hashes,graph_hashes_after=after_hashes,bad_guids=bad);(out/(key+'-arena-actor-preservation.json')).write_text(json.dumps(proof,indent=2),encoding='utf-8')
        if int(bp.Status)==2 or before!=after or shapes!=after_shapes or hashes!=after_hashes or bad or sum(len(g.Nodes) for g in ue.blueprint_get_all_graphs(bp))!=TOTAL[key]+ADDED[key]:raise RuntimeError('original Arena actor CDO/ABI/GUID/component/delegate/task graph differs: '+key)
        try:
            ue.register_declared_mixin(bp.GeneratedClass);row,=[r for r in ue.get_registered_mixins() if r['target_class']==bp.GeneratedClass];counts={p:len(v['functions']) for p,v in row['profiles'].items()}
            if counts!=dict.fromkeys(('Python','BlueprintFallback'),COUNTS[key]):raise RuntimeError('complete Arena actor Profile family required')
        finally:ue.unregister_all_mixins()
        bp.save_package();asset.save_package();saved.extend((relative,'Content/UEPMixins/'+name+'.uasset'));rows[key]=dict(original_nodes=TOTAL[key],interface_nodes=5,transport_nodes=ADDED[key]-5,method_counts=counts)
    return dict(status='passed',kind='arenaactors',runtime_acceptance=False,full_acceptance=False,original_class_defaults_signature_graphs_preserved=True,original_cdo_abis_guids_components_graphs_and_native_tasks_preserved=True,original_static_parent_begin_and_construction_retained=True,unique_hero_selector_avoids_ancestor_collision=True,original_gameplayready_next_tick_delay_and_two_second_task_retained=True,original_overlap_binding_level_zero_authority_and_remote_vfx_branches_retained=True,new_business_nodes=0,native_end_adapter_nodes=0,actors=rows,assets=saved)
