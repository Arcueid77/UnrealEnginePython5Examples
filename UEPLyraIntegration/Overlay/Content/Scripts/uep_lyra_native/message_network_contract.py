"""Independent gates for native damage, production rules, and two actual owners."""
import argparse
import json
from pathlib import Path
from .message_validation_contract import require

PEERS=('server','A','B0')
EXPECTED=dict(kills=5,deaths=1,assists=1,team=5,other=0)


def validate(r):
    require(r['status']=='passed' and r['error'] is None,'peer/finalizer failed')
    require(r['profile'] in ('Python','NativeFallback'),'wrong profile')
    require(r['native_mode']==('DedicatedServer' if r['peer']=='server' else 'Client'),'actual native mode required')
    require(r['result']['stat_delta']==EXPECTED,'native GAS score/assist replication differs')
    require(r['observer_scopes_closed'] and r['selectors_restored'] and r['relay_profiles_restored'],'network cleanup incomplete')
    require(r['actual_native_damage_spec_applied']==(r['peer']=='server'),'only authority may apply native damage')
    require(not any(r[k] for k in ('synthetic_verb_messages','health_attribute_writes','score_stat_writes','damage_immunity_writes')),'synthetic health/score/message mutation forbidden')
    if r['peer']=='server':
        require(r['server_waited_for_client_process_exit'],'authority exited before actual client exits')
        require(r['native_processor_counts']==dict(streak=1,chain=1,assist=1),'natural authority processors required')
        require(len(r['applied_specs'])==6 and [s['amount'] for s in r['applied_specs']]==[25.,75.,100.,100.,100.,100.],'native six-spec damage inputs differ')
        events=r['result']['native_messages']
        require(sum(e['verb']=='Lyra.Elimination.Message' for e in events)==5,'five native health deaths required')
        require(sum(e['verb']=='Lyra.Damage.Message' for e in events)==6,'six native damage receipts required')
        assists=[e for e in events if e['verb']=='Lyra.Assist.Message']
        require(len(assists)==1 and assists[0]['instigator']=='helper' and assists[0]['target']=='B0' and assists[0]['magnitude']==25.,'native helper assist attribution differs')
        streak=[e for e in events if '.EliminationStreak.' in e['verb']]
        chain=[e for e in events if '.EliminationChain.' in e['verb']]
        require(len(streak)==1 and streak[0]['magnitude']==5 and streak[0]['instigator']=='A','native five-kill streak absent')
        require([e['magnitude'] for e in chain]==[2.,3.,4.] and all(e['instigator']=='A' for e in chain),'native rapid chain thresholds differ')
        selected='python_' if r['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_'
        for kind,m in r['processor_metrics'].items():
            require(m[selected+'eliminations']==5 and m[other+'eliminations']==0,'wrong native rule dispatch: '+kind)
            if kind=='assist':require(m[selected+'damage']==6 and m[other+'damage']==0,'wrong native damage dispatch')
    else:
        require(r['native_processor_counts']==dict(streak=0,chain=0,assist=0),'authority-only processors appeared on client')
        require(len(r['result']['kill_notifications'])==5,'native multicast kill notifications absent')
        awards=r['result']['award_messages']
        expected=4 if r['peer']=='A' else 0
        require(len(awards)==expected,'native owner award relay filter differs')
        if expected:
            require(sorted(e['payload_tag'] for e in awards)==sorted([
                'Lyra.ShooterGame.Accolade.EliminationChain.2x','Lyra.ShooterGame.Accolade.EliminationChain.3x',
                'Lyra.ShooterGame.Accolade.EliminationChain.4x','Lyra.ShooterGame.Accolade.EliminationStreak.5']), 'wrong real owner award payloads')
        if r['peer']=='B0':require(r['result']['native_death_started']>=1,'victim native death delegate missing')


def validate_directory(path):
    rows={p:json.loads((path/(p+'.json')).read_text(encoding='utf-8-sig')) for p in PEERS}
    for r in rows.values():validate(r)
    require(len({r['run_id'] for r in rows.values()})==len({r['profile'] for r in rows.values()})==1,'mixed peer inputs')
    require(rows['A']['result']['stat_delta']==rows['B0']['result']['stat_delta']==rows['server']['result']['stat_delta'],'native authority/client score mismatch')
    return dict(status='passed',profile=rows['server']['profile'],peers=list(PEERS),actual_damage_and_network=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    print(json.dumps(validate_directory(a.directory),indent=2))
