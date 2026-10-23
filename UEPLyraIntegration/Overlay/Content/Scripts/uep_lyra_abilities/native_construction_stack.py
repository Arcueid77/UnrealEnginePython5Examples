"""Bounded Windows current-thread stack addresses;no Unreal/debugger mutation.

Symbol loading is deliberately left to a separate process after Unreal exits.
Addresses and module offsets stay hexadecimal strings,never JSON floats.
"""
import ctypes,os
from pathlib import Path

_api=None
_modules={}

def api():
    global _api
    if _api is None:
        if os.name!='nt':raise OSError('Native construction stacks require Windows')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.RtlCaptureStackBackTrace.argtypes=(ctypes.c_ulong,ctypes.c_ulong,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_ulong))
        kernel.RtlCaptureStackBackTrace.restype=ctypes.c_ushort
        kernel.GetModuleHandleExW.argtypes=(ctypes.c_ulong,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p));kernel.GetModuleHandleExW.restype=ctypes.c_int
        kernel.GetModuleFileNameW.argtypes=(ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_ulong);kernel.GetModuleFileNameW.restype=ctypes.c_ulong
        _api=kernel
    return _api

def frame(address,kernel):
    base=ctypes.c_void_p()
    if not kernel.GetModuleHandleExW(4|2,ctypes.c_void_p(address),ctypes.byref(base)):
        return dict(address=hex(address),module=None,base=None,rva=None)
    value=int(base.value)
    if value not in _modules:
        name=ctypes.create_unicode_buffer(32768);count=kernel.GetModuleFileNameW(base,name,len(name))
        if not count or count>=len(name):raise OSError('Cannot identify captured native module')
        stat=Path(name.value).stat()
        _modules[value]=dict(path=name.value,file_size=stat.st_size,mtime_ns=str(stat.st_mtime_ns))
    return dict(address=hex(address),module=dict(_modules[value]),base=hex(value),rva=hex(address-value))

def capture(limit=96):
    if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=96:raise ValueError('Native stack frame bound must be1..96')
    kernel=api();values=(ctypes.c_void_p*limit)();count=int(kernel.RtlCaptureStackBackTrace(0,limit,values,None))
    if not 0<count<=limit:raise OSError('No bounded native stack was captured')
    return dict(schema_version=1,pid=os.getpid(),frame_limit=limit,frames=[frame(int(values[i]),kernel) for i in range(count)],
        symbols_resolved_in_unreal=False,debugger_attached=False,unreal_state_written=False)
