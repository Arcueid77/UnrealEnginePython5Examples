"""Resolve captured Win64 addresses offline using existing matching local PDBs.

Never attaches to a game,executes a target DLL,downloads symbols or initializes
DbgHelp inside Unreal. Missing local symbols remain explicitly unresolved.
"""
import argparse,ctypes,hashlib,json,os,struct
from pathlib import Path

class Symbol(ctypes.Structure):
    _fields_=[('SizeOfStruct',ctypes.c_ulong),('TypeIndex',ctypes.c_ulong),('Reserved',ctypes.c_ulonglong*2),
        ('Index',ctypes.c_ulong),('Size',ctypes.c_ulong),('ModBase',ctypes.c_ulonglong),('Flags',ctypes.c_ulong),
        ('Value',ctypes.c_ulonglong),('Address',ctypes.c_ulonglong),('Register',ctypes.c_ulong),('Scope',ctypes.c_ulong),
        ('Tag',ctypes.c_ulong),('NameLen',ctypes.c_ulong),('MaxNameLen',ctypes.c_ulong),('Name',ctypes.c_char*1)]

class ModuleInfo(ctypes.Structure):
    _fields_=[('SizeOfStruct',ctypes.c_ulong),('BaseOfImage',ctypes.c_ulonglong),('ImageSize',ctypes.c_ulong),
        ('TimeDateStamp',ctypes.c_ulong),('CheckSum',ctypes.c_ulong),('NumSyms',ctypes.c_ulong),('SymType',ctypes.c_int),
        ('ModuleName',ctypes.c_char*32),('ImageName',ctypes.c_char*256),('LoadedImageName',ctypes.c_char*256),('LoadedPdbName',ctypes.c_char*256),
        ('CVSig',ctypes.c_ulong),('CVData',ctypes.c_char*780),('PdbSig',ctypes.c_ulong),('PdbSig70',ctypes.c_ubyte*16),('PdbAge',ctypes.c_ulong),
        ('PdbUnmatched',ctypes.c_int),('DbgUnmatched',ctypes.c_int),('LineNumbers',ctypes.c_int),('GlobalSymbols',ctypes.c_int),
        ('TypeInfo',ctypes.c_int),('SourceIndexed',ctypes.c_int),('Publics',ctypes.c_int),('MachineType',ctypes.c_ulong),('Reserved',ctypes.c_ulong)]

def provenance(symbols):
    text='\n'.join(symbols);result=[]
    for label,needles in (
        ('blueprint-reinstancing',('FBlueprintCompileReinstancer','ReinstanceObjects','ReinstanceInner')),
        ('construction-rerun',('RerunConstructionScripts',)),
        ('object-duplication',('StaticDuplicateObject','DuplicateObjectEx')),
        ('native-spawn',('UWorld::SpawnActor','UWorld::SpawnActorDeferred')),
        ('native-destruction',('UWorld::DestroyActor',)),
        ('native-restart',('RestartPlayer','SpawnDefaultPawnFor')),
        ('native-ability-reset',('ULyraGameplayAbility_Reset::ActivateAbility',))):
        if any(n in text for n in needles):result.append(label)
    return result

def image_size(path):
    # Offline symbol contexts cannot query the original process's mapped PE
    # headers. Supply SizeOfImage explicitly rather than a zero-length range.
    with Path(path).open('rb') as source:
        header=source.read(64)
        if len(header)!=64 or header[:2]!=b'MZ':raise ValueError('Captured module is not a PE image')
        source.seek(struct.unpack_from('<I',header,0x3c)[0]);nt=source.read(84)
        if len(nt)!=84 or nt[:4]!=b'PE\0\0':raise ValueError('Captured module PE header missing')
        value=struct.unpack_from('<I',nt,24+56)[0]
        if not value:raise ValueError('Captured module image range is empty')
        return value

class Resolver:
    def __init__(self,search_path):
        if os.name!='nt':raise OSError('Offline native symbol resolution requires Windows')
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True);self.kernel.GetCurrentProcess.restype=ctypes.c_void_p
        self.process=self.kernel.GetCurrentProcess()
        bundled=Path(search_path).parent/'ThirdParty/DbgHelp/dbghelp.dll'
        self.dbghelp_path=str(bundled) if bundled.is_file() else 'dbghelp.dll'
        self.dbg=ctypes.WinDLL(self.dbghelp_path,use_last_error=True);self.loaded={};self.cache={}
        self.dbg.SymSetOptions.argtypes=(ctypes.c_ulong,);self.dbg.SymSetOptions.restype=ctypes.c_ulong
        # Exact local symbols;no symsrv autodetection or interactive prompts.
        self.dbg.SymSetOptions(0x2|0x4|0x10|0x200|0x400|0x80000|0x02000000)
        self.dbg.SymInitializeW.argtypes=(ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_int);self.dbg.SymInitializeW.restype=ctypes.c_int
        self.dbg.SymLoadModuleExW.argtypes=(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_ulonglong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong)
        self.dbg.SymLoadModuleExW.restype=ctypes.c_ulonglong
        self.dbg.SymFromAddr.argtypes=(ctypes.c_void_p,ctypes.c_ulonglong,ctypes.POINTER(ctypes.c_ulonglong),ctypes.POINTER(Symbol));self.dbg.SymFromAddr.restype=ctypes.c_int
        self.dbg.SymGetModuleInfo64.argtypes=(ctypes.c_void_p,ctypes.c_ulonglong,ctypes.POINTER(ModuleInfo));self.dbg.SymGetModuleInfo64.restype=ctypes.c_int
        self.dbg.SymCleanup.argtypes=(ctypes.c_void_p,);self.dbg.SymCleanup.restype=ctypes.c_int
        if not self.dbg.SymInitializeW(self.process,str(search_path),False):raise ctypes.WinError(ctypes.get_last_error())
    def close(self):self.dbg.SymCleanup(self.process)
    def module_info(self,base):
        info=ModuleInfo();info.SizeOfStruct=ctypes.sizeof(ModuleInfo)
        if not self.dbg.SymGetModuleInfo64(self.process,base,ctypes.byref(info)):return dict(pdb_matched=False,symbol_type=None)
        pdb=bytes(info.LoadedPdbName).decode('utf-8',errors='replace')
        return dict(symbol_type=info.SymType,pdb_matched=info.SymType in (3,7) and not info.PdbUnmatched and not info.DbgUnmatched and bool(pdb),
            loaded_pdb=pdb,pdb_age=info.PdbAge,pdb_guid=bytes(info.PdbSig70).hex(),global_symbols=bool(info.GlobalSymbols))
    def resolve(self,frame):
        address=int(frame['address'],16);module=frame.get('module')
        if not module:return dict(frame,symbol=None,reason='unidentified-module')
        base=int(frame['base'],16);offset=int(frame['rva'],16)
        if base+offset!=address:raise ValueError('Captured native address/base/offset disagree')
        path=Path(module['path']);stat=path.stat()
        if stat.st_size!=module['file_size'] or str(stat.st_mtime_ns)!=module['mtime_ns']:raise ValueError('Captured module file changed before resolution: '+str(path))
        if base in self.loaded and self.loaded[base]['path']!=str(path):raise ValueError('Captured module base reused for another image in the same symbol context')
        if base not in self.loaded:
            loaded=int(self.dbg.SymLoadModuleExW(self.process,None,str(path),None,base,image_size(path),None,0))
            self.loaded[base]=dict(path=str(path),base=hex(base),loaded=loaded==base,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pdb_present=path.with_suffix('.pdb').is_file())
        key=(base,offset)
        if key not in self.cache:
            buf=ctypes.create_string_buffer(ctypes.sizeof(Symbol)+4096);info=ctypes.cast(buf,ctypes.POINTER(Symbol));info.contents.SizeOfStruct=ctypes.sizeof(Symbol);info.contents.MaxNameLen=4096
            displacement=ctypes.c_ulonglong()
            ok=self.dbg.SymFromAddr(self.process,address,ctypes.byref(displacement),info)
            self.cache[key]=dict(symbol=ctypes.string_at(ctypes.addressof(buf)+Symbol.Name.offset,info.contents.NameLen).decode('utf-8',errors='replace') if ok else None,
                displacement=hex(displacement.value) if ok else None,reason=None if ok else 'no-matching-local-symbol',winerror=None if ok else ctypes.get_last_error())
        return dict(frame,**self.cache[key])

def resolve_directory(directory,search_path):
    root=Path(directory);groups={};records=[];inputs=[];modules=[];reader=None
    for path in sorted(root.glob('*-early-readiness-*.json')):
        record=json.loads(path.read_text(encoding='utf-8-sig'));data=record.get('data',{})
        if data.get('native_callstack_error'):raise ValueError('Native observer reported stack capture error: '+path.name)
        if data.get('native_callstack'):groups.setdefault(data['native_callstack']['pid'],[]).append((path,record))
    for pid,events in groups.items():
        # ASLR addresses from different processes are separate address spaces.
        resolver=Resolver(search_path);reader=resolver.dbghelp_path
        try:
            for path,record in events:
                data=record['data'];captured=data['native_callstack'];frames=[resolver.resolve(f) for f in captured['frames']];names=[f['symbol'] for f in frames if f['symbol']]
                inputs.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                records.append(dict(file=path.name,kind=record['kind'],actor=data.get('actor'),peer=path.name.split('-early-readiness-',1)[0],pid=pid,
                    resolved_frames=len(names),frame_count=len(frames),provenance=provenance(names),frames=frames))
            modules.extend(dict(m,pid=pid,**resolver.module_info(base)) for base,m in resolver.loaded.items())
        finally:resolver.close()
    if not records:raise ValueError('No actual captured native lifecycle stacks found')
    return dict(schema_version=1,status='resolved_local_capture',symbol_reader=reader,records=records,modules=modules,input_hashes=inputs,
        debugger_attached=False,target_dll_executed=False,symbols_downloaded=False,unreal_state_written=False,original_readiness_race_fixed=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',required=True);parser.add_argument('--search-path',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    result=resolve_directory(args.directory,args.search_path);Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],lifecycle_stacks=len(result['records']),modules=len(result['modules']),records_with_unreal_symbols=sum(any('UnrealEditor' in (f.get('module') or {}).get('path','') and f['symbol'] for f in r['frames']) for r in result['records']),original_readiness_race_fixed=False)))
