"""Allowlisted update downloads using Windows verified TLS (including frozen apps)."""
import ctypes
from ctypes import wintypes as w
import re
import time
from contextlib import nullcontext
from urllib.parse import urlsplit, urljoin

def fetch(url, limit=2_000_000, destination=None, redirects=0):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in {'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'} or parsed.port not in (None,443) or parsed.username or parsed.password:
        raise ValueError('Update download address is not trusted.')
    if redirects>5:raise ValueError('Too many update redirects.')
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
        session=checked(api.WinHttpOpen('League-Start-Companion-Updater',4,None,None,0));handles.append(session)
        checked(api.WinHttpSetTimeouts(session,12000,12000,12000,12000))
        connection=checked(api.WinHttpConnect(session,parsed.hostname,443,0));handles.append(connection)
        request=checked(api.WinHttpOpenRequest(connection,'GET',parsed.path+('?' + parsed.query if parsed.query else ''),None,None,None,0x800000));handles.append(request)
        disabled=dword(2);checked(api.WinHttpSetOption(request,63,ctypes.byref(disabled),ctypes.sizeof(disabled)))
        checked(api.WinHttpSendRequest(request,'Accept: application/vnd.github+json\r\n',0xffffffff,None,0,0,0));checked(api.WinHttpReceiveResponse(request,None))
        status=dword();size=dword(ctypes.sizeof(status))
        checked(api.WinHttpQueryHeaders(request,19|0x20000000,None,ctypes.byref(status),ctypes.byref(size),None))
        if status.value in (301,302,303,307,308):
            location=ctypes.create_unicode_buffer(16384);size=dword(ctypes.sizeof(location))
            checked(api.WinHttpQueryHeaders(request,33,None,location,ctypes.byref(size),None))
            return fetch(urljoin(url,location.value),limit,destination,redirects+1)
        if status.value!=200:raise ValueError(f'Update server returned HTTP {status.value}. Please try again later.')
        result=bytearray();buffer=ctypes.create_string_buffer(65536);read=dword();total=0;deadline=time.monotonic()+180
        with destination.open('wb') if destination is not None else nullcontext() as output:
            while True:
                if time.monotonic()>deadline:raise TimeoutError('Update download timed out.')
                checked(api.WinHttpReadData(request,buffer,len(buffer),ctypes.byref(read)))
                if not read.value:break
                total+=read.value
                if total>limit:raise ValueError('Update response exceeds the size limit.')
                if output:output.write(buffer.raw[:read.value])
                else:result.extend(buffer.raw[:read.value])
        if destination is not None:return None
        return bytes(result)
    finally:
        for item in reversed(handles):api.WinHttpCloseHandle(item)
