"""Restore the encrypted backup only into the dedicated local tmpfs container."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import struct
import subprocess

from cryptography.fernet import Fernet
from scripts.production_backup_readonly import Blob, MAGIC

CONTAINER = "english-video-otp-restore-20261116"


def unprotect_key(value):
    data = ctypes.create_string_buffer(value, len(value))
    incoming = Blob(len(value), ctypes.cast(data, ctypes.POINTER(ctypes.c_byte)))
    outgoing = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                          wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    if not crypt32.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(outgoing.pbData)


def run(command, data=None):
    result = subprocess.run(command, input=data, capture_output=True, timeout=180, check=False)
    if result.returncode:
        # Do not print restore output: it can contain user data.
        raise RuntimeError("Local backup validation or restore failed")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("backup")
    args = parser.parse_args()
    folder = (Path(os.environ["LOCALAPPDATA"]) / "EnglishThroughVideo" / "production-backups").resolve()
    path = Path(args.backup).resolve(strict=True)
    if path.parent != folder or not path.name.endswith(".pgdump.fernet"):
        raise RuntimeError("Backup path is outside the protected folder")
    ident = run(["docker", "inspect", "--format", '{{index .Config.Labels "english-video-purpose"}}', CONTAINER])
    if ident.stdout.strip() != b"otp-restore":
        raise RuntimeError("Unexpected restore container")
    encrypted = path.read_bytes()
    if not encrypted.startswith(MAGIC):
        raise RuntimeError("Unexpected encrypted backup format")
    pos = len(MAGIC)
    size = struct.unpack(">I", encrypted[pos:pos+4])[0]
    wrapped = encrypted[pos+4:pos+4+size]
    archive = Fernet(unprotect_key(wrapped)).decrypt(encrypted[pos+4+size:])
    if not archive.startswith(b"PGDMP"):
        raise RuntimeError("Unexpected pg_dump archive format")
    run(["docker", "exec", "-i", CONTAINER, "pg_restore", "--list"], archive)
    run(["docker", "exec", CONTAINER, "createdb", "-U", "postgres", "otp_restore"])
    run(["docker", "exec", "-i", CONTAINER, "pg_restore", "--exit-on-error", "--no-owner",
         "--no-privileges", "-U", "postgres", "-d", "otp_restore"], archive)
    print("Encrypted SHA256:", hashlib.sha256(encrypted).hexdigest().upper())
    print("Archive integrity and local restore: OK")


if __name__ == "__main__":
    main()
