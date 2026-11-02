"""Independent report gate for the native Arena death policy replacement."""
import argparse
import json
from pathlib import Path
from uep_lyra_world.arena_actor_contract import validate as original
from uep_lyra_weapons.hero_burst_cue_contract import require


def validate(report):
    original(report)
    require(report['mode']=='Python' and report['previous_blueprint_policy_fixed']=='Python','previous Arena Blueprint policies changed')
    m=report['native_lifecycle_counts']
    if report['native_profile']=='Python':
        require(m['death_python']>0 and m['death_activate']==m['death_end']==1 and m['death_start']>=1 and m['death_finish']>=1,'Arena native Python lifecycle route missing')
    else:
        require(report['native_profile']=='NativeLifecycleFallback' and m['death_native']>0 and m['death_activate']==m['death_end']==m['death_start']==m['death_finish']==0,'Arena native fallback route changed')
    return dict(status='passed',profile=report['native_profile'],native_death_task=True,native_duration_seconds=2.,previous_blueprint_policy='Python',network_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True)
    print(json.dumps(validate(json.loads(Path(parser.parse_args().report).read_text(encoding='utf-8-sig')))))
