"""Give Windows the same stable app identity for processes and shortcuts."""
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import uuid

from app_version import VERSION

APP_ID='LeagueStartCompanion.Desktop'

class GUID(ctypes.Structure):
    _fields_=[('a',ctypes.c_uint32),('b',ctypes.c_uint16),('c',ctypes.c_uint16),('d',ctypes.c_ubyte*8)]
    @classmethod
    def parse(cls,value):return cls.from_buffer_copy(uuid.UUID(value).bytes_le)

class PROPERTYKEY(ctypes.Structure):
    _fields_=[('fmtid',GUID),('pid',ctypes.c_uint32)]

class CountedPointer(ctypes.Structure):
    _fields_=[('count',ctypes.c_uint32),('pointer',ctypes.c_void_p)]

class VariantValue(ctypes.Union):
    _fields_=[('text',ctypes.c_wchar_p),('array',CountedPointer),('integer',ctypes.c_int64)]

class PROPVARIANT(ctypes.Structure):
    _fields_=[('vt',ctypes.c_uint16),('reserved',ctypes.c_uint16*3),('value',VariantValue)]

def check(result):
    if result<0:raise OSError(f'Windows app identity operation failed (0x{result & 0xffffffff:08X}).')

def method(pointer,index,result,*arguments):
    table=ctypes.cast(pointer,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(result,ctypes.c_void_p,*arguments)(table[index])

def set_process_identity(identifier=APP_ID):
    api=ctypes.WinDLL('shell32').SetCurrentProcessExplicitAppUserModelID
    api.argtypes=[w.LPCWSTR];api.restype=ctypes.c_long
    check(api(identifier))

def process_identity():
    shell=ctypes.WinDLL('shell32');ole=ctypes.WinDLL('ole32')
    shell.GetCurrentProcessExplicitAppUserModelID.argtypes=[ctypes.POINTER(w.LPWSTR)]
    shell.GetCurrentProcessExplicitAppUserModelID.restype=ctypes.c_long;ole.CoTaskMemFree.argtypes=[ctypes.c_void_p]
    value=w.LPWSTR();check(shell.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(value)))
    try:return value.value
    finally:ole.CoTaskMemFree(value)

def resource_icon(root):
    versioned=Path(root)/'assets'/f'app-icon-{VERSION}.ico'
    return versioned if versioned.is_file() else Path(root)/'assets/app-icon.ico'

def shortcut_identity(path,write=True):
    """Set/read System.AppUserModel.ID via Shell Link's native property store."""
    ole=ctypes.WinDLL('ole32');ole.CoInitialize.argtypes=[ctypes.c_void_p];ole.CoInitialize.restype=ctypes.c_long
    initialized=ole.CoInitialize(None)
    if initialized<0 and initialized!=-2147417850:check(initialized)
    ole.CoCreateInstance.argtypes=[ctypes.POINTER(GUID),ctypes.c_void_p,w.DWORD,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype=ctypes.c_long;ole.PropVariantClear.argtypes=[ctypes.POINTER(PROPVARIANT)]
    persist=ctypes.c_void_p();store=ctypes.c_void_p()
    clsid=GUID.parse('00021401-0000-0000-C000-000000000046')
    iid_persist=GUID.parse('0000010b-0000-0000-C000-000000000046')
    iid_store=GUID.parse('886d8eeb-8cf2-4446-8d02-cdba1dbdcf99')
    key=PROPERTYKEY(GUID.parse('9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3'),5)
    try:
        check(ole.CoCreateInstance(ctypes.byref(clsid),None,1,ctypes.byref(iid_persist),ctypes.byref(persist)))
        check(method(persist,5,ctypes.c_long,w.LPCWSTR,w.DWORD)(persist,str(path),2 if write else 0))
        check(method(persist,0,ctypes.c_long,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p))(persist,ctypes.byref(iid_store),ctypes.byref(store)))
        value=PROPVARIANT()
        if write:
            text=ctypes.create_unicode_buffer(APP_ID);value.vt=31;value.value.text=ctypes.cast(text,ctypes.c_wchar_p)
            check(method(store,6,ctypes.c_long,ctypes.POINTER(PROPERTYKEY),ctypes.POINTER(PROPVARIANT))(store,ctypes.byref(key),ctypes.byref(value)))
            check(method(store,7,ctypes.c_long)(store))
            check(method(persist,6,ctypes.c_long,w.LPCWSTR,w.BOOL)(persist,str(path),True))
            return APP_ID
        check(method(store,5,ctypes.c_long,ctypes.POINTER(PROPERTYKEY),ctypes.POINTER(PROPVARIANT))(store,ctypes.byref(key),ctypes.byref(value)))
        try:return value.value.text if value.vt==31 else None
        finally:ole.PropVariantClear(ctypes.byref(value))
    finally:
        if store:method(store,2,w.ULONG)(store)
        if persist:method(persist,2,w.ULONG)(persist)
        if initialized>=0:ole.CoUninitialize()

def refresh_shell_icon(path):
    notify=ctypes.WinDLL('shell32').SHChangeNotify
    notify.argtypes=[ctypes.c_long,w.UINT,ctypes.c_void_p,ctypes.c_void_p]
    text=ctypes.create_unicode_buffer(str(path))
    notify(0x2000,0x5,ctypes.cast(text,ctypes.c_void_p),None) # UPDATEITEM, PATHW
