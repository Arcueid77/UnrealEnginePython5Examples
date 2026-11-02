"""Stage-only UI worlds, avoiding the unchanged uncooked weapon Niagara blocker."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue


def arg(name):return next(a.split('=',1)[1] for a in sys.argv if a.startswith('-'+name+'='))


def generate(stage):
    mode=ue.create_blueprint(ue.find_class('GameModeBase'),'/Game/UEPValidation/BP_EscapeUIGameMode');ue.compile_blueprint(mode)
    cdo=mode.GeneratedClass.get_cdo();cdo.PlayerControllerClass=ue.find_class('CommonPlayerController');cdo.PlayerStateClass=ue.find_class('PlayerState');cdo.GameStateClass=ue.find_class('GameStateBase');cdo.DefaultPawnClass=ue.find_class('SpectatorPawn');cdo.HUDClass=ue.find_class('HUD');mode.save_package()
    assets=['Content/UEPValidation/BP_EscapeUIGameMode.uasset']
    for name in ('L_EscapeUI_A','L_EscapeUI_B'):
        factory=ue.new_object(ue.find_class('WorldFactory'));world=ue.create_asset(name,'/Game/UEPValidation',ue.find_class('World'),factory)
        settings,=[a for a in world.all_actors() if a.is_a(ue.find_class('WorldSettings'))];settings.set_property('DefaultGameMode',mode.GeneratedClass)
        world.actor_spawn(ue.find_class('PlayerStart'));world.save_package();assets.append('Content/UEPValidation/'+name+'.umap')
    return dict(status='passed',assets_saved=True,asset_family_count=3,policy_events=0,assets=assets,stage_only=True,original_game_instance_and_common_ui_policy_retained=True,weapon_or_niagara_assets_modified=False,asset_hashes={p:hashlib.sha256((stage/p).read_bytes()).hexdigest().upper() for p in assets})


result=Path(arg('UEPNativeEscapeAssetsResult'))
try:
    script=Path(globals().get('__file__') or next(a for a in sys.argv if a.endswith('generate_native_escape_fixtures.py'))).resolve();sys.path.insert(0,str(script.parent))
    from stage_safety import require_authoring_stage
    stage=require_authoring_stage(arg('UEPNativeEscapeStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()));report=generate(stage)
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(ue.log if report['status']=='passed' else ue.log_error)('UEP_NATIVE_ESCAPE_ASSETS_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
