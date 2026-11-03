"""Verify staged CPython receipt files and the actual runtime's configured home."""
import argparse
import hashlib
import json
from pathlib import Path
import re

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def require(value,message):
    if not value:raise ValueError(message)

def inspect(package,engine,receipt,log,working):
    package,engine,working=package.resolve(),engine.resolve(),working.resolve()
    data=json.loads(receipt.read_text(encoding='utf-8-sig'));prefix='$(EngineDir)/Binaries/ThirdParty/Python3/Win64/'
    rows=[];normalized=[]
    for row in data['RuntimeDependencies']:
        value=row['Path'].replace('\\','/')
        if value.startswith(prefix):
            relative=Path('Engine/Binaries/ThirdParty/Python3/Win64')/value[len(prefix):]
        elif '/Engine/Binaries/ThirdParty/Python3/Win64/' in value:
            relative=Path('Engine/Binaries/ThirdParty/Python3/Win64')/value.split('/Engine/Binaries/ThirdParty/Python3/Win64/',1)[1]
        else:continue
        source=engine/relative;target=package/relative
        require(target.resolve().is_relative_to(package) and source.is_file() and target.is_file(),'CPython receipt dependency missing: '+str(relative))
        if sha(source)!=sha(target):
            # UAT stages .ini text with Windows line endings. Permit exactly
            # that byte transformation; retain strict hashes for every other
            # byte, binary, Python module and standard-library dependency.
            normalize=lambda value:value.removeprefix(b'\xef\xbb\xbf').replace(b'\r\n',b'\n')
            require(source.suffix.casefold()=='.ini' and normalize(source.read_bytes())==normalize(target.read_bytes()),'CPython receipt dependency changed: '+str(relative))
            normalized.append(dict(relative_path=relative.as_posix(),source_sha256=sha(source),packaged_sha256=sha(target),transformation='UAT INI UTF-8 BOM and line endings only'))
        rows.append(dict(relative_path=relative.as_posix(),sha256=sha(target)))
    require(len(rows)>=10 and any(Path(row['relative_path']).name=='python311.dll' for row in rows),'complete staged CPython runtime receipt missing')
    homes=re.findall(r'Initialized engine CPython at (.+)',log.read_text(encoding='utf-8-sig'))
    require(len(homes)==1,'actual initialized CPython home marker missing')
    home=Path(homes[0].strip());home=(working/home).resolve() if not home.is_absolute() else home.resolve()
    require(home.is_relative_to(package) and home.is_dir(),'actual CPython home is outside the package')
    require((home/'Lib/encodings/__init__.py').is_file() and (home/'Lib/json/__init__.py').is_file(),'packaged standard library missing')
    return dict(status='passed',receipt_python_files=len(rows),actual_python_home=str(home),runtime_home_inside_package=True,dependency_files=rows,staging_line_ending_normalizations=normalized)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('package','engine','receipt','log','working','result'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=inspect(a.package,a.engine,a.receipt,a.log,a.working);a.result.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in r.items() if k!='dependency_files'}))
