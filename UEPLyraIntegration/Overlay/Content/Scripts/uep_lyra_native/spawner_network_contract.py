"""Keep the accepted Blueprint Python layer fixed while comparing C++ rules."""
from uep_lyra_world.spawner_network_protocol import CASES,PEERS,require,validate_cases as original,validate_ack

PLAN=tuple((peer,name,profile) for peer in PEERS for name in CASES for profile in ('NativeFallback','Python'))


def validate_cases(cases):
    original(cases,PLAN,True)
    for row in cases:
        selected='python_' if row['profile']=='Python' else 'native_';other='native_' if selected=='python_' else 'python_';metrics=row['cpp_policy_delta']
        require(metrics[selected+'attempt']==1 and all(metrics[other+k]==0 for k in ('attempt','complete','reset')),'native level overlap entered wrong C++ policy')
        require(metrics[selected+'complete']==int(row['success']) and metrics[selected+'reset']==int(row['success']),'native level timer completion/reset bypassed C++ policy')
    return True
