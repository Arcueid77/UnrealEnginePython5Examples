"""Whitelist only complete, explicitly marked injected Python tracebacks."""
import argparse
import json
from pathlib import Path
import re

def validate(log,expected):
    assert not re.search(r'(?im)Fatal error:|Assertion failed|Unhandled Exception|Ensure condition failed',log),'native failure in hardening log'
    blocks=[];current=None;unexpected=[];prefixes=[]
    for line in log.splitlines():
        if re.search(r'LogPython: Error: UEP_EXPECTED_HARDENING_EXCEPTION_(DAMAGE|COST_CHECK|COST_APPLY|SETTLEMENT|RESET)\s*$',line):prefixes.append(line);continue
        if 'LogPython: Error: Traceback (most recent call last):' in line:
            assert current is None,'nested/unclosed injected traceback';current=[line];continue
        if current is not None:
            current.append(line)
            if re.search(r'RuntimeError: UEP_EXPECTED_HARDENING_EXCEPTION_(DAMAGE|COST_CHECK|COST_APPLY|SETTLEMENT|RESET)\s*$',line):blocks.append(current);current=None
            continue
        if re.search(r'Log\w+:\s*Error:|Traceback \(most recent call last\):',line):unexpected.append(line)
    assert current is None and len(blocks)==expected,(len(blocks),current)
    assert len(prefixes)==expected,'expected exception summaries differ'
    assert not unexpected,unexpected[:6]
    assert re.search(r'(?s)Goodbye Python.*UEP_HARDENING_SHUTDOWN_PASSED.*Log file closed',log),'hardening shutdown ordering failed'
    return dict(status='passed',expected_python_exceptions=len(blocks),unexpected_errors=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--log',required=True);p.add_argument('--expected',type=int,default=0);a=p.parse_args()
    print(json.dumps(validate(Path(a.log).read_text(encoding='utf-8-sig'),a.expected)))
