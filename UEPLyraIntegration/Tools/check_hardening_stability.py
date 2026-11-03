"""Post-warmup operational budgets for a sustained private game process."""
import argparse
import json
from pathlib import Path
import statistics

def require(v,m):
    if not v:raise AssertionError(m)

def validate(report,samples):
    require(report['status']=='passed' and report['mode']=='Soak','closed actual soak required')
    start=report['runtime_started_seconds'];warm=report['warmup_seconds'] if report['duration_requested']>=1200 else 10.
    rows=[r for r in samples if start+warm<=r['elapsed_seconds']<=start+report['runtime_elapsed_seconds']]
    require(len(rows)>=3,'post-warmup operating-system samples missing')
    first,last=rows[:3],rows[-3:];private_growth=statistics.median(r['private_bytes'] for r in last)-statistics.median(r['private_bytes'] for r in first)
    handle_growth=statistics.median(r['handles'] for r in last)-statistics.median(r['handles'] for r in first)
    scoped=[s for s in report['post_gc_samples'] if s['elapsed']>=warm]
    require(scoped,'post-GC gameplay object samples missing')
    actor_growth=max(s['actors'] for s in scoped)-min(s['actors'] for s in scoped)
    registration_growth=max(s['registrations'] for s in scoped)-min(s['registrations'] for s in scoped)
    require(private_growth<=256*1024*1024,'private-memory growth exceeds declared 256 MiB operational budget')
    require(handle_growth<=32,'handle growth exceeds declared operational budget')
    require(actor_growth<=25 and registration_growth==0,'scoped actor/router population did not remain bounded')
    require(max(s['contexts'] for s in scoped)<=8,'temporary policy contexts survive quiescent full GC')
    return dict(status='passed',long_soak=report['duration_requested']>=1200,post_warmup_os_samples=len(rows),post_warmup_gc_samples=len(scoped),
        private_growth_bytes=private_growth,handle_growth=handle_growth,actor_population_range=actor_growth,mixin_registration_range=registration_growth,
        maximum_quiescent_contexts=max(s['contexts'] for s in scoped),budgets=dict(private_growth_bytes=268435456,handle_growth=32,actor_population_range=25,mixin_registration_range=0,quiescent_contexts=8),
        limits='bounded twenty-minute headless workload; no universal leak-freedom or rendered-frame performance claim')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',required=True);p.add_argument('--samples',required=True);a=p.parse_args();load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
    print(json.dumps(validate(load(a.report),load(a.samples)),indent=2))
