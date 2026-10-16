"""Atomic harness messages, with bounded Windows sharing-violation retries."""

import json
import os
import time

if os.name == 'nt':
    import ctypes
    from ctypes import wintypes
    import msvcrt
    _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _create_file = _kernel32.CreateFileW
    _create_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    _create_file.restype = wintypes.HANDLE
    _close_handle = _kernel32.CloseHandle
    _close_handle.argtypes = (wintypes.HANDLE,)
    _close_handle.restype = wintypes.BOOL
    _replace_file = _kernel32.ReplaceFileW
    _replace_file.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                             wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID)
    _replace_file.restype = wintypes.BOOL


def open_shared_text(path):
    """A reader must permit atomic replacement, not hold a Windows delete lock."""
    if os.name != 'nt':
        return open(path, 'r', encoding='utf-8-sig')
    # GENERIC_READ, FILE_SHARE_READ|WRITE|DELETE, OPEN_EXISTING. No ACL changes.
    handle = _create_file(os.fspath(path), 0x80000000, 7, None, 3, 0x08000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
    except BaseException:
        _close_handle(handle)
        raise
    try:
        return os.fdopen(descriptor, 'r', encoding='utf-8-sig')  # File owns handle.
    except BaseException:
        os.close(descriptor)
        raise


def read_text(path):
    with open_shared_text(path) as reader:
        return reader.read()


def replace_atomic(temporary, path):
    if os.name == 'nt':
        # ReplaceFile supports an existing destination with shared readers;
        # MoveFileEx (os.replace) rejects that case on this Windows filesystem.
        if _replace_file(os.fspath(path), os.fspath(temporary), None, 0, None, None):
            return
        error = ctypes.get_last_error()
        if error not in (2, 3):
            raise ctypes.WinError(error)
    os.replace(temporary, path)  # First creation, or the POSIX implementation.


def sharing_retry(operation):
    for attempt in range(10):
        try:
            return operation()
        except OSError as error:
            # ReplaceFileW can report ERROR_UNABLE_TO_REMOVE_REPLACED (1175)
            # while a reader briefly holds the destination. Unlike 1176/1177,
            # this failure has not moved either file; retry the same atomic
            # operation, never delete the destination or publish partial JSON.
            if not isinstance(error, PermissionError) and getattr(error, 'winerror', None) != 1175:
                raise
            if attempt == 9:
                raise
            time.sleep(min(0.005 * (2 ** attempt), 0.1))


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')
    sharing_retry(lambda: replace_atomic(temporary, path))


def read_json(path):
    try:
        text = sharing_retry(lambda: read_text(path))
    except FileNotFoundError:
        return None
    # Malformed JSON and permanent access errors must not masquerade as missing ACKs.
    return json.loads(text)
