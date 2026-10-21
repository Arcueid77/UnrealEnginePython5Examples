"""Owned native effect fixture and read-only original Arena actor ABI evidence."""
import hashlib,json,sys,traceback
from pathlib import Path
script=globals().get('__file__') or next(v for v in sys.argv if Path(v).name=='generate_arena_actor_probe.py')
sys.path.insert(0,str(Path(script).resolve().parent))
import unreal_engine as ue
from unreal_engine.classes import GameplayEffect
from uep_lyra_world.arena_actor_mixin import HERO,DEATH,PICKUP,TEAM,TEAM_EVENT,PARTS_EVENT
PATH='/Game/UEPValidation/GE_ArenaActorRestore'
RELATIVE='Content/UEPValidation/GE_ArenaActorRestore.uasset'
def generate(stage):
    if (stage/RELATIVE).exists():raise RuntimeError('fresh actor restore fixture required')
    classes={key:ue.load_class(path) for key,path in (('hero',HERO),('death',DEATH),('pickup',PICKUP))};signatures={}
    for key,names in (('hero',('ReceiveBeginPlay','ListenForTeam',TEAM,TEAM_EVENT,PARTS_EVENT,'ShowPawnAgainNextFrame')),('death',('K2_ActivateAbility','OnFinish_01E106CD44A9DE9122B131B0ABF28DAC')),('pickup',('ChangePickupEffect','OnRep_GameplayEffectToApply'))):signatures[key]={name:ue.describe_function(classes[key],name) for name in names}
    effect=ue.create_blueprint(GameplayEffect,PATH);ue.compile_blueprint(effect)
    if int(effect.Status)==2:raise RuntimeError('owned restore GE compile failed')
    effect.save_package()
    return dict(status='passed',stage_only=True,gameplay_business=False,native_effect_fixture=True,callbacks_replayed=False,signatures=signatures,asset=str(stage/RELATIVE),sha256=hashlib.sha256((stage/RELATIVE).read_bytes()).hexdigest())
if __name__=='__main__':
    from stage_safety import require_authoring_stage
    result=Path(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPArenaActorProbeResult=')))
    try:
        stage=require_authoring_stage(next(v.split('=',1)[1] for v in sys.argv if v.startswith('-UEPHeroAbilityStageRoot=')),ue.convert_relative_path_to_full(ue.get_content_dir()));result.write_text(json.dumps(generate(stage),indent=2),encoding='utf-8');ue.log('UEP_ARENA_ACTOR_PROBE_PASSED')
    except Exception:result.write_text(json.dumps(dict(status='failed',error=traceback.format_exc()),indent=2),encoding='utf-8');raise
