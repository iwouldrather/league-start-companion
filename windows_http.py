"""Bounded, redirect-free pobb.in downloads using Windows' verified TLS stack."""
import ctypes
from ctypes import wintypes as w
import re

def fetch_shared_code(code,limit=2_000_000):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',code):raise ValueError('Invalid share identifier.')
    api=ctypes.WinDLL('winhttp',use_last_error=True)
    handle=w.HANDLE;pointer=ctypes.c_void_p;dword=w.DWORD
    signatures={
        'WinHttpOpen':([w.LPCWSTR,dword,w.LPCWSTR,w.LPCWSTR,dword],handle),
        'WinHttpConnect':([handle,w.LPCWSTR,w.WORD,dword],handle),
        'WinHttpOpenRequest':([handle,w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,pointer,dword],handle),
        'WinHttpSetOption':([handle,dword,pointer,dword],w.BOOL),
        'WinHttpSetTimeouts':([handle,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int],w.BOOL),
        'WinHttpSendRequest':([handle,w.LPCWSTR,dword,pointer,dword,dword,ctypes.c_size_t],w.BOOL),
        'WinHttpReceiveResponse':([handle,pointer],w.BOOL),
        'WinHttpQueryHeaders':([handle,dword,w.LPCWSTR,pointer,pointer,pointer],w.BOOL),
        'WinHttpReadData':([handle,pointer,dword,pointer],w.BOOL),
        'WinHttpCloseHandle':([handle],w.BOOL)}
    for name,(arguments,result) in signatures.items():getattr(api,name).argtypes=arguments;getattr(api,name).restype=result
    handles=[]
    def checked(value):
        if not value:raise ctypes.WinError(ctypes.get_last_error())
        return value
    try:
        session=checked(api.WinHttpOpen('League-Start-Companion/0.2',4,None,None,0));handles.append(session)
        checked(api.WinHttpSetTimeouts(session,12000,12000,12000,12000))
        connection=checked(api.WinHttpConnect(session,'pobb.in',443,0));handles.append(connection)
        request=checked(api.WinHttpOpenRequest(connection,'GET','/pob/'+code,None,None,None,0x800000));handles.append(request)
        disabled=dword(2);checked(api.WinHttpSetOption(request,63,ctypes.byref(disabled),ctypes.sizeof(disabled)))
        checked(api.WinHttpSendRequest(request,None,0,None,0,0,0));checked(api.WinHttpReceiveResponse(request,None))
        status=dword();size=dword(ctypes.sizeof(status))
        checked(api.WinHttpQueryHeaders(request,19|0x20000000,None,ctypes.byref(status),ctypes.byref(size),None))
        if status.value!=200:raise ValueError(f'Build download returned HTTP {status.value}; redirects are not followed.')
        result=bytearray();buffer=ctypes.create_string_buffer(65536);read=dword()
        while True:
            checked(api.WinHttpReadData(request,buffer,len(buffer),ctypes.byref(read)))
            if not read.value:break
            result.extend(buffer.raw[:read.value])
            if len(result)>limit:raise ValueError('This build is too large to import.')
        return bytes(result)
    finally:
        for item in reversed(handles):api.WinHttpCloseHandle(item)
