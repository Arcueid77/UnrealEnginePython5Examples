"""Join immutable local Pawn binding history to native ASC takeover log lines.

This tool never runs Unreal or repairs actors. Actor names are only joined
inside one peer's captured log/history; they are not cross-peer wire identity.
"""
import argparse,datetime,hashlib,json,re
from pathlib import Path

TAKEOVER=re.compile(r'Setting up ASC \[(?P<asc>[^\]]+)\] on pawn \[(?P<new>[^\]]+)\] owner \[(?P<owner>[^\]]+)\], existing \[(?P<old>[^\]]+)\]')
STAMP=re.compile(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d+)\]')

def phase_timing(directory):
    root=Path(directory);events={}
    for peer in ('server','A','B0'):
        file=root/(peer+'.log')
        if not file.is_file():continue
        rows=[]
        for line,text in enumerate(file.read_text(encoding='utf-8-sig').splitlines(),1):
            stamp=STAMP.search(text)
            if not stamp:continue
            kind=None;takeover=TAKEOVER.search(text)
            if "Beginning Phase 'ShooterGame.GamePhase.Playing'" in text:kind='playing'
            elif 'OnExperienceLoadComplete(' in text:kind='experience-loaded'
            elif takeover and takeover['old'] not in ('None',takeover['new']):kind='asc-takeover'
            if kind:
                value=datetime.datetime.strptime(stamp[1],'%Y.%m.%d-%H.%M.%S:%f').replace(tzinfo=datetime.timezone.utc)
                row=dict(kind=kind,line=line,utc=value.isoformat(),unix=value.timestamp())
                if kind=='asc-takeover':row.update(takeover.groupdict())
                rows.append(row)
        events[peer]=rows
    starts=[r for r in events.get('server',[]) if r['kind']=='playing']
    start=starts[0]['unix'] if starts else None
    for rows in events.values():
        for row in rows:
            row['seconds_from_authority_playing']=None if start is None else round(row['unix']-start,6)
    return dict(events=events,authority_playing_observed=start is not None,
        timestamp_offsets_assume_same_host_clock=True,cross_peer_actor_identity_claimed=False,cause_or_fix_proven=False)

def local_name(value):return value.rsplit('.',1)[-1] if isinstance(value,str) else None
def event_order(event):
    sequence=re.search(r'-early-readiness-(\d+)\.json$',event['file'])
    return (float(event['elapsed']),int(sequence[1]) if sequence else 0)
def bound_attribute_health(row):
    return [a.get('health') for a in (row.get('player_state_asc') or {}).get('health_attributes',[])]

def correlate_retired_pawns(events):
    """Match one run's server-assigned Legacy GUIDs,never cross-peer names."""
    runs={e['run_id'] for rows in events.values() for e in rows}
    if len(runs)>1:raise ValueError('Mixed native runs cannot establish retired-Pawn identity')
    def wire(row,key='network_identity'):
        value=row.get(key) or {}
        return (value['transport'],value['wire_id']) if value.get('valid') and value.get('transport')=='Legacy' and value.get('wire_id') else None
    authority=sorted(events.get('server',[]),key=event_order);retired={}
    for event in authority:
        row=event['data'];key=(wire(row),wire(row,'player_state_network_identity'))
        if event['kind']!='native-reset' or row.get('role')!=3 or None in key:continue
        end=next((e for e in authority if e['kind']=='native-end-play' and event_order(e)>event_order(event) and e['data'].get('actor')==row.get('actor')),None)
        if end:retired.setdefault(key,[]).append((event,end))
    joins=[]
    for peer,rows in events.items():
        if peer=='server':continue
        ordered=sorted(rows,key=event_order)
        for birth in ordered:
            row=birth['data'];key=(wire(row),wire(row,'player_state_network_identity'))
            if birth['kind']!='native-begin-play' or row.get('role')!=1 or len(retired.get(key,[]))!=1:continue
            stale=row.get('actor');current=row.get('player_state_pawn')
            if not current or current==stale or (row.get('player_state_asc') or {}).get('avatar')!=stale:continue
            previous=[e for e in ordered if event_order(e)<event_order(birth) and e['data'].get('actor')==current and e['data'].get('health',0)>0
                and (e['data'].get('player_state_asc') or {}).get('avatar')==current and wire(e['data'],'player_state_network_identity')==key[1]]
            end=next((e for e in ordered if e['kind']=='native-end-play' and event_order(e)>event_order(birth) and e['data'].get('actor')==stale),None)
            if not previous or end is None:continue
            after=[]
            for e in ordered:
                value=e['data'];attributes=bound_attribute_health(value)
                if event_order(e)<=event_order(end) or value.get('actor')!=current:continue
                if value.get('player_state_pawn')!=current or value.get('health')!=0:continue
                if any(value.get(k) is not None for k in ('health_set','actor_asc','extension_asc')):continue
                if (value.get('player_state_asc') or {}).get('avatar') is not None:continue
                if attributes and all(isinstance(v,(int,float)) and v>0 for v in attributes):after.append(e)
            if not after:continue
            prior=previous[-1];reset,retirement=retired[key][0]
            if wire(prior['data']) is None or wire(prior['data'])==key[0] or wire(after[0]['data'])!=wire(prior['data']):continue
            current_authority=next((e for e in authority if event_order(e)>event_order(reset) and e['data'].get('role')==3
                and wire(e['data'])==wire(prior['data']) and wire(e['data'],'player_state_network_identity')==key[1]
                and e['data'].get('health',0)>0 and e['data'].get('player_state_pawn')==e['data'].get('actor')
                and (e['data'].get('player_state_asc') or {}).get('avatar')==e['data'].get('actor')),None)
            if current_authority is None:continue
            joins.append(dict(peer=peer,run_id=birth['run_id'],stale_pawn_wire=list(key[0]),player_state_wire=list(key[1]),
                current_pawn_wire=list(wire(prior['data'])),authority_reset_file=reset['file'],authority_retirement_file=retirement['file'],
                authority_current_binding_file=current_authority['file'],
                previous_healthy_file=prior['file'],late_retired_pawn_birth_file=birth['file'],late_retired_pawn_end_file=end['file'],
                current_empty_binding_file=after[0]['file'],current_pawn=current,late_retired_pawn=stale,
                cross_peer_actor_names_used_for_identity=False,gameplay_repair_proven=False))
    return joins

def analyze(peer,events,log):
    takeovers=[dict(m.groupdict(),line=line) for line,text in enumerate(log.splitlines(),1) if (m:=TAKEOVER.search(text)) and m['old'] not in ('None',m['new'])]
    ordered=sorted(events,key=event_order)
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
    root=Path(directory);reports=[];hashes=[];raw_events={}
    def bind(p):hashes.append(dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    for peer in peers:
        logfile=root/(peer+'.log')
        if not logfile.is_file():continue
        events=[];bind(logfile)
        for p in root.glob(peer+'-early-readiness-*.json'):
            row=json.loads(p.read_text(encoding='utf-8-sig'));row['file']=p.name;events.append(row);bind(p)
        raw_events[peer]=events;reports.append(analyze(peer,events,logfile.read_text(encoding='utf-8-sig')))
    if not reports:raise ValueError('captured peer logs and histories required')
    serverlog=root/'server.log'
    if serverlog.is_file():bind(serverlog)
    if 'server' not in raw_events:
        raw_events['server']=[]
        for p in root.glob('server-early-readiness-*.json'):
            row=json.loads(p.read_text(encoding='utf-8-sig'));row['file']=p.name;raw_events['server'].append(row);bind(p)
    return dict(schema_version=1,status='reviewed_capture',directory=str(root.resolve()),peers=reports,input_hashes=hashes,native_phase_timing=phase_timing(root),
        retired_authority_pawn_replication_joins=correlate_retired_pawns(raw_events),
        full_acceptance=False,production_race_repair_claimed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    result=inspect(args.directory);Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],peer_count=len(result['peers']),canonical_empty_binding_rows=sum(len(p['canonical_gameplayready_empty_binding_rows']) for p in result['peers']),production_race_repair_claimed=False)))
