"""Handles Win32 sem compartilhamento de exclusão e sem seguir reparse points."""
from __future__ import annotations

import ctypes
import hashlib
try:
    import msvcrt
except ImportError:
    msvcrt = None
import os
from ctypes import wintypes as w
from pathlib import Path

WinDLL = getattr(ctypes, "WinDLL", ctypes.CDLL)
try:
    k32 = WinDLL("kernel32", use_last_error=True)
except Exception:
    class _DummyK32:
        def __getattr__(self, name: str):
            return lambda *args, **kwargs: 0
    k32 = _DummyK32()
k32.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE]
k32.CreateFileW.restype = w.HANDLE
k32.CloseHandle.argtypes = [w.HANDLE]
k32.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD]
k32.GetFinalPathNameByHandleW.restype = w.DWORD


class FileInfo(ctypes.Structure):
    _fields_ = [("attributes", w.DWORD), ("created", w.FILETIME),
                ("accessed", w.FILETIME), ("written", w.FILETIME),
                ("volume", w.DWORD), ("size_high", w.DWORD), ("size_low", w.DWORD),
                ("links", w.DWORD), ("index_high", w.DWORD), ("index_low", w.DWORD)]


k32.GetFileInformationByHandle.argtypes = [w.HANDLE, ctypes.POINTER(FileInfo)]
k32.GetFileInformationByHandle.restype = w.BOOL
MAX_FILE_BYTES = 1024 * 1024


class LockedHandle:
    """Diretórios negam rename/delete; arquivos também negam escritores paralelos."""
    def __init__(self, path: Path, *, directory=False, write=False, create=False):
        self.path, self.fd, self.writable = path, None, write
        access = 0x80000000 if directory else (0xC0000000 if write else 0x80000000)
        share = 3 if directory else 1  # READ|WRITE para diretórios; READ para arquivos.
        flags = 0x00200000 | (0x02000000 if directory else 0x80)
        self.handle = k32.CreateFileW(str(path), access, share, None, 1 if create else 3, flags, None)
        if self.handle == ctypes.c_void_p(-1).value:
            code = ctypes.get_last_error()
            raise ValueError(f"FILE_CONFLICT: não foi possível abrir o destino ({code})")
        try:
            info = self.info()
            if info.attributes & 0x400:
                raise ValueError("FOLDER_REPARSE_DENIED")
            if not directory and info.links > 1:
                raise ValueError("FOLDER_HARDLINK_DENIED")
            if bool(info.attributes & 0x10) != directory:
                raise ValueError("FOLDER_TYPE_MISMATCH")
            final = ctypes.create_unicode_buffer(32768)
            length = k32.GetFinalPathNameByHandleW(self.handle, final, len(final), 0)
            if not length or length >= len(final):
                raise ValueError("FOLDER_IDENTITY_UNAVAILABLE")
            resolved = final.value.removeprefix("\\\\?\\")
            if os.path.normcase(resolved) != os.path.normcase(str(path)):
                raise ValueError("FOLDER_ESCAPE_DENIED")
        except BaseException:
            self.close()
            raise

    def info(self):
        result = FileInfo()
        if not k32.GetFileInformationByHandle(self.handle, ctypes.byref(result)):
            raise ValueError("FOLDER_IDENTITY_UNAVAILABLE")
        return result

    def identity(self):
        info = self.info()
        return info.volume, info.index_high, info.index_low

    def descriptor(self):
        if self.fd is None:
            self.fd = msvcrt.open_osfhandle(self.handle, os.O_BINARY | (os.O_RDWR if self.writable else os.O_RDONLY))
        return self.fd

    def read(self):
        info = self.info()
        if info.size_high or info.size_low > MAX_FILE_BYTES:
            raise ValueError("FILE_TOO_LARGE: limite de 1 MiB")
        fd = self.descriptor()
        os.lseek(fd, 0, os.SEEK_SET)
        data = os.read(fd, MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("FILE_TOO_LARGE")
        return data

    def version(self, data):
        return f"{self.identity()}:{len(data)}:{hashlib.sha256(data).hexdigest()}"

    def write(self, data):
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("FILE_TOO_LARGE: limite de 1 MiB")
        fd = self.descriptor()
        os.lseek(fd, 0, os.SEEK_SET)
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("FILE_WRITE_FAILED")
            offset += written
        os.ftruncate(fd, len(data))
        os.fsync(fd)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd, self.handle = None, None
        elif self.handle is not None:
            k32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
