"""Audit the exact native permission-loss errors intentionally caused by logout."""
import argparse
import json
from pathlib import Path
import re
from uep_lyra_weapons.hero_burst_cue_contract import require

PROFILES=('BlueprintFallback','Python')
EXPECTED=re.compile(r'(?m)^\[\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3}\]\[\s*\d+\]LogCommonGame: Error: HandlePrivilegeChanged: Player 0 no longer has permission to play the game!\r?$')
UNEXPECTED=re.compile(r'(?im)(Log\w+:\s*Error:|Fatal error:|Assertion failed|Unhandled Exception|Ensure condition failed|Traceback)')

def audit(text):
    records=[]
    for profile in PROFILES:
        begin='UEP_IDENTITY_LOGOUT_BEGIN '+profile;end='UEP_IDENTITY_LOGOUT_END '+profile
        require(text.count(begin)==text.count(end)==1,'identity logout ownership markers missing or repeated: '+profile)
        block=text.split(begin,1)[1].split(end,1)[0];matches=list(EXPECTED.finditer(block));require(len(matches)==1,'each actual owned logout must cause exactly one original primary privilege-loss log: '+profile)
        records.append(dict(profile=profile,count=1,native_source='CommonGameInstance::HandlePrivilegeChanged',line=matches[0].group(0).rstrip()))
    require(len(list(EXPECTED.finditer(text)))==2,'unexpected permission-loss log outside owned logout windows')
    cleaned=EXPECTED.sub('',text);require(not UNEXPECTED.search(cleaned),'unexpected error remains in native identity logout log')
    return cleaned,dict(status='passed',expected_native_permission_loss_errors=2,records=records,other_native_errors_allowed=False,raw_log_modified=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--log',required=True);parser.add_argument('--clean-log',required=True);parser.add_argument('--result',required=True);args=parser.parse_args();raw=Path(args.log);clean=Path(args.clean_log);require(raw.resolve()!=clean.resolve(),'raw native log must be preserved');text,report=audit(raw.read_text(encoding='utf-8-sig'));clean.write_text(text,encoding='utf-8');Path(args.result).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
