"""Join immutable local Pawn binding history to native ASC takeover log lines.

This tool never runs Unreal or repairs actors. Actor names are only joined
inside one peer's captured log/history; they are not cross-peer wire identity.
"""
import argparse,hashlib,json,re
from pathlib import Path

TAKEOVER=re.compile(r'Setting up ASC \[(?P<asc>[^\]]+)\] on pawn \[(?P<new>[^\]]+)\] owner \[(?P<owner>[^\]]+)\], existing \[(?P<old>[^\]]+)\]')

def local_name(value):return value.rsplit('.',1)[-1] if isinstance(value,str) else None
def bound_attribute_health(row):
    return [a.get('health') for a in (row.get('player_state_asc') or {}).get('health_attributes',[])]

def analyze(peer,events,log):
    takeovers=[dict(m.groupdict(),line=line) for line,text in enumerate(log.splitlines(),1) if (m:=TAKEOVER.search(text)) and m['old'] not in ('None',m['new'])]
    ordered=sorted(events,key=lambda r:(float(r['elapsed']),r['file']))
    previous={};gaps=[]
    for event in ordered:
        row=event.get('data',{});actor=row.get('actor')
        if not actor or 'health' not in row:continue
        canonical=row.get('player_state_pawn')==actor
        ready=bool(row.get('init_features')) and all(f.get('state')=='InitState.GameplayReady' for f in row['init_features'])
        binding_empty=row.get('health_set') is None and row.get('extension_asc') is None and row.get('actor_asc') is None
        attributes=bound_attribute_health(row)
        if row.get('health')==0 and canonical and ready and binding_empty and attributes and all(isinstance(h,(int,float)) and h>0 for h in attributes):
            matching=[t for t in takeovers if t['old']==local_name(actor) and t['owner']==local_name(row.get('player_state'))]
            replacements=[]
            for t in matching:
                lifecycle=[dict(file=e['file'],kind=e['kind'],elapsed=e['elapsed'],python_stack=e['data'].get('python_stack')) for e in ordered
                    if local_name(e.get('data',{}).get('actor'))==t['new'] and e['kind'] in ('native-construction','native-begin-play','native-destroyed-before-end-play','native-end-play')]
                replacements.append(dict(native_log=t,lifecycle=lifecycle))
            before=previous.get(actor)
            gaps.append(dict(file=event['file'],elapsed=event['elapsed'],actor=actor,role=row.get('role'),canonical_player_state=row.get('player_state'),
                native_attribute_health=attributes,component_health=0,previous_binding_file=before['file'] if before else None,
                previous_component_health=before['data'].get('health') if before else None,native_takeovers=replacements))
        previous[actor]=event
    return dict(peer=peer,local_native_takeovers=takeovers,canonical_gameplayready_empty_binding_rows=gaps,
        cross_peer_identity_claimed=False,cause_or_fix_proven=False,health_written=False)

def inspect(directory,peers=('A','B0')):
    root=Path(directory);reports=[];hashes=[]
    def bind(p):hashes.append(dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    for peer in peers:
        logfile=root/(peer+'.log')
        if not logfile.is_file():continue
        events=[];bind(logfile)
        for p in root.glob(peer+'-early-readiness-*.json'):
            row=json.loads(p.read_text(encoding='utf-8-sig'));row['file']=p.name;events.append(row);bind(p)
        reports.append(analyze(peer,events,logfile.read_text(encoding='utf-8-sig')))
    if not reports:raise ValueError('captured peer logs and histories required')
    return dict(schema_version=1,status='reviewed_capture',directory=str(root.resolve()),peers=reports,input_hashes=hashes,
        full_acceptance=False,production_race_repair_claimed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    result=inspect(args.directory);Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],peer_count=len(result['peers']),canonical_empty_binding_rows=sum(len(p['canonical_gameplayready_empty_binding_rows']) for p in result['peers']),production_race_repair_claimed=False)))
