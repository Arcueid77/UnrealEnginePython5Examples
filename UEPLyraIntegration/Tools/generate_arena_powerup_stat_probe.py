"""Owned typed stat caller, soft texture and native instant GameplayEffect."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_powerup_stat_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import Blueprint,GameplayEffect
from unreal_engine.structs import EdGraphPinType
from message_payload_graphs import connect
from uep_lyra_hud.arena_powerup_stat_mixin import CLASS,BOUND
PATH='/Game/UEPValidation/BP_ArenaPowerupStatProbe'
RELATIVE='Content/UEPValidation/BP_ArenaPowerupStatProbe.uasset'
TEXTURE='/Game/UEPValidation/T_ArenaStatSoftProbe.T_ArenaStatSoftProbe'
EFFECT='/Game/UEPValidation/GE_ArenaStatProbe.GE_ArenaStatProbe_C'
def kind(p):return EdGraphPinType(PinCategory=p.category,PinSubCategory=p.sub_category,PinSubCategoryObject=p.sub_category_object,ContainerType=p.container_type,bIsReference=p.is_reference,bIsConst=p.is_const)
def generate(stage):
    if any((stage/p).exists() for p in (RELATIVE,'Content/UEPValidation/T_ArenaStatSoftProbe.uasset','Content/UEPValidation/GE_ArenaStatProbe.uasset')):raise RuntimeError('fresh stat probe assets required')
    cls=ue.load_class(CLASS);signatures={name:ue.describe_function(cls,name) for name in ('Configure','UpdateText','ListenFor',BOUND)};source=ue.load_object(Blueprint,'/TopDownArena/UserInterface/Player/W_PlayerTile.W_PlayerTile');configure,=[g for g in source.FunctionGraphs if g.get_name()=='Configure'];calls=[n for n in configure.Nodes if n.get_class().get_name()=='K2Node_CallFunction' and str(n.FunctionReference.MemberName)=='Configure'];source_call,=[n for n in calls if 'BombsRemaining' in n.node_find_pin('Attribute').default_value]
    texture=ue.load_object(ue.find_class('Texture2D'),'/TopDownArena/UserInterface/Player/Texture/T_Bombs.T_Bombs').duplicate('/Game/UEPValidation/T_ArenaStatSoftProbe','T_ArenaStatSoftProbe');texture.save_package()
    bp=ue.create_blueprint(ue.find_class('Object'),PATH)
    for name,target in (('Configure','Configure'),('Update','UpdateText')):
        graph=ue.blueprint_add_function(bp,name);entry=graph.Nodes[0];call=graph.graph_add_node_call_function(getattr(cls,target));entry.node_create_pin(1,EdGraphPinType(PinCategory='object',PinSubCategoryObject=cls),'Widget');connect(entry,'then',call,'execute');connect(entry,'Widget',call,'self')
        if name=='Configure':
            entry.node_create_pin(1,kind(call.node_find_pin('Ability Target')),'Target');connect(entry,'Target',call,'Ability Target');call.node_find_pin('Attribute').default_value=source_call.node_find_pin('Attribute').default_value;call.node_find_pin('Display Asset').default_value=TEXTURE
        else:entry.node_create_pin(1,kind(call.node_find_pin('Value')),'Value');connect(entry,'Value',call,'Value')
        if len(graph.Nodes)!=2:raise RuntimeError('stat typed caller has unexpected nodes')
    ue.compile_blueprint(bp)
    if int(bp.Status)==2:raise RuntimeError('stat typed caller compile failed')
    effect=ue.create_blueprint(GameplayEffect,'/Game/UEPValidation/GE_ArenaStatProbe');ue.compile_blueprint(effect)
    if int(effect.Status)==2:raise RuntimeError('stat native effect fixture compile failed')
    bp.save_package();effect.save_package()
    files=[RELATIVE,'Content/UEPValidation/T_ArenaStatSoftProbe.uasset','Content/UEPValidation/GE_ArenaStatProbe.uasset']
    return dict(status='passed',stage_only=True,gameplay_business=False,typed_virtual_calls=True,callback_replayed=False,signatures=signatures,nodes=4,soft_reference_kept_in_native_pin=True,texture=TEXTURE,effect=EFFECT,assets=[dict(asset=str(stage/file),sha256=hashlib.sha256((stage/file).read_bytes()).hexdigest()) for file in files],asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaPowerupStatProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()));result.write_text(json.dumps(generate(stage),indent=2));ue.log('UEP_ARENA_POWERUP_STAT_PROBE_PASSED')
    except Exception:result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2));raise
