"""Audit the Game target's generated MSVC output and PCH paths."""
import argparse
import hashlib
import json
from pathlib import Path
import re

def audit(stage,engine):
    stage,engine=stage.resolve(),engine.resolve();checked=[];files=[]
    for path in stage.rglob('*.rsp'):
        if '/Intermediate/Build/' not in path.as_posix() or '/LyraGame/' not in path.as_posix():continue
        source=path.read_text(encoding='utf-8-sig');values=[]
        for pattern in (r'(?im)^/(?:Fo|Fd|Fp|OUT:|PDB:|IMPLIB:)"([^\"]+)"',r'(?im)^/(?:sourceDependencies|experimental:log)\s+"([^\"]+)"'):
            values.extend(re.findall(pattern,source))
        for value in values:
            output=Path(value);output=(engine/'Engine/Source'/output).resolve()
            if not output.is_relative_to(stage):raise ValueError('Game compiler path escapes its owned stage: '+str(output))
            checked.append(str(output))
        if values:files.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper()))
    if not files or len(checked)<100:raise ValueError('Complete generated Game response files required')
    return dict(status='passed',scope='generated-Game-MSVC-output-and-PCH-paths',response_files=files,checked_path_count=len(checked),
        outside_stage_paths=0,stage=str(stage),engine_binary_write_paths_found=False)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('stage','engine','result'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=audit(a.stage,a.engine);a.result.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in r.items() if k!='response_files'}))
