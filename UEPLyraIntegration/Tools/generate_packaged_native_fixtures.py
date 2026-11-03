"""Create only the three typed VM observers needed by packaged network tests."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import unreal_engine as ue

def arg(name):return next(v.split('=',1)[1] for v in sys.argv if v.startswith('-'+name+'='))

def run():
    source=Path(globals().get('__file__') or next(v for v in sys.argv if v.endswith('generate_packaged_native_fixtures.py'))).resolve();sys.path.insert(0,str(source.parent))
    from stage_safety import require_authoring_stage
    from message_payload_graphs import read_graph,broadcast_graph
    from uep_lyra_hud.elimination_feed_relay_mixin import STRUCT
    stage=require_authoring_stage(arg('UEPPackagedFixtureStageRoot'),ue.convert_relative_path_to_full(ue.get_content_dir()))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
    overlay=source.parents[1]/'Overlay';protected=[dict(path=str(stage/p.relative_to(overlay)),sha256=sha(stage/p.relative_to(overlay))) for p in overlay.rglob('*.uasset')]
    proxy=ue.find_class('AsyncAction_ListenForGameplayMessage');router=ue.find_class('GameplayMessageSubsystem')
    specs=[('BP_EliminationFeedProbe','Feed',ue.load_object(ue.find_class('ScriptStruct'),STRUCT),True),('BP_AccoladeRelayProbe','Notification',ue.find_struct('LyraNotificationMessage'),True),('BP_AutoRespawnResetProbe','Reset',ue.find_struct('LyraPlayerResetMessage'),False)]
    assets=[]
    for name,suffix,payload,verb in specs:
        relative='Content/UEPValidation/'+name+'.uasset'
        if (stage/relative).exists():raise RuntimeError('Fresh packaged native fixture required: '+name)
        bp=ue.create_blueprint(ue.find_class('Object'),'/Game/UEPValidation/'+name);read_graph(bp,suffix,payload,proxy)
        if verb:broadcast_graph(bp,'Verb',ue.find_struct('LyraVerbMessage'),router)
        ue.compile_blueprint(bp)
        if int(bp.Status)==2:raise RuntimeError('Packaged native typed fixture compile failed: '+name)
        bp.save_package();assets.append(dict(relative_path=relative,sha256=sha(stage/relative),stage_only=True,typed_vm_reader=True))
    for row in protected:
        if sha(Path(row['path']))!=row['sha256']:raise RuntimeError('Fixture authoring modified a production overlay asset')
    return dict(status='passed',stage_only=True,production_assets_unchanged=True,fixture_count=3,assets=assets,packaged_runtime=False)

result=Path(arg('UEPPackagedFixtureResult'))
try:report=run()
except Exception:report=dict(status='failed',error=traceback.format_exc())
result.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
(ue.log if report['status']=='passed' else ue.log_error)('UEP_PACKAGED_NATIVE_FIXTURES_'+report['status'].upper())
if report['status']!='passed':raise RuntimeError(report['error'])
