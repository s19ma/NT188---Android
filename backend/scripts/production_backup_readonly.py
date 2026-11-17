"""Create a DPAPI-wrapped, Fernet-encrypted custom dump of the named Neon DB.

Windows-only; dumps a single exported read-only snapshot. No plaintext archive is
written to disk. Run only after validating the source and destination.
"""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import struct
import subprocess
from urllib.parse import unquote, urlsplit

from cryptography.fernet import Fernet
from dotenv import dotenv_values
import psycopg
from psycopg import sql

MAGIC = b"ETVOTP1\n"
SOURCE_HOST = "ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech"
SOURCE_DB = "english_video_db"
SOURCE_REVISION = "f31a7c4d2e01"


class Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def protect_key(value):
    data = ctypes.create_string_buffer(value, len(value))
    incoming = Blob(len(value), ctypes.cast(data, ctypes.POINTER(ctypes.c_byte)))
    outgoing = Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR,
                                        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.POINTER(Blob)]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    if not crypt32.CryptProtectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        kernel32.LocalFree(outgoing.pbData)


def main():
    if os.name != "nt":
        raise RuntimeError("This backup requires Windows DPAPI")
    cfg = dotenv_values(".env")
    url = cfg["DIRECT_DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    parsed = urlsplit(url)
    if parsed.hostname != SOURCE_HOST or parsed.path != "/" + SOURCE_DB or not parsed.password:
        raise RuntimeError("Direct database endpoint does not match the approved source")
    password = unquote(parsed.password)
    if "\n" in password or "\r" in password:
        raise RuntimeError("Password cannot be sent via the protected stdin channel")
    target = Path(os.environ["LOCALAPPDATA"]) / "EnglishThroughVideo" / "production-backups"
    if not target.is_dir():
        raise RuntimeError("Create and restrict the backup directory before running")
    env = os.environ.copy()
    env.update(PGHOST=parsed.hostname, PGPORT=str(parsed.port or 5432),
               PGUSER=unquote(parsed.username or ""), PGDATABASE=SOURCE_DB,
               PGSSLMODE="require", PGCONNECT_TIMEOUT="10",
               PGOPTIONS="-c default_transaction_read_only=on")
    command = ["docker", "run", "--rm", "-i", "-e", "PGHOST", "-e", "PGPORT",
               "-e", "PGUSER", "-e", "PGDATABASE", "-e", "PGSSLMODE", "-e",
               "PGCONNECT_TIMEOUT", "-e", "PGOPTIONS", "postgres:18", "sh", "-c",
               'IFS= read -r PGPASSWORD; export PGPASSWORD; exec pg_dump -Fc --snapshot="$1"',
               "dump", "SNAPSHOT"]
    with psycopg.connect(url, connect_timeout=10, options="-c default_transaction_read_only=on") as conn:
        with conn.cursor() as cur:
            cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            cur.execute("SELECT current_database(), current_setting('server_version_num'), current_setting('transaction_read_only')")
            database, server_version, readonly = cur.fetchone()
            if database != SOURCE_DB or not server_version.startswith("18") or readonly != "on":
                raise RuntimeError("Unexpected source database or version")
            cur.execute("SELECT version_num FROM alembic_version")
            if cur.fetchone()[0] != SOURCE_REVISION:
                raise RuntimeError("Unexpected source migration revision")
            cur.execute("SELECT pg_export_snapshot()")
            command[-1] = cur.fetchone()[0]
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            tables = [row[0] for row in cur.fetchall()]
            counts = {}
            for table in tables:
                cur.execute(sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(table)))
                counts[table] = cur.fetchone()[0]
            result = subprocess.run(command, input=(password + "\n").encode(), env=env,
                                    capture_output=True, timeout=180, check=False)
            if result.returncode or not result.stdout.startswith(b"PGDMP"):
                raise RuntimeError("pg_dump failed; no backup written")
    key = Fernet.generate_key()
    wrapped = protect_key(key)
    encrypted = MAGIC + struct.pack(">I", len(wrapped)) + wrapped + Fernet(key).encrypt(result.stdout)
    path = target / ("english-video-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".pgdump.fernet")
    with path.open("xb") as f:
        f.write(encrypted)
        f.flush()
        os.fsync(f.fileno())
    print("Encrypted backup:", path)
    print("SHA256:", hashlib.sha256(encrypted).hexdigest().upper())
    print("Source snapshot counts:", counts)
    print("Archive bytes:", len(encrypted))


if __name__ == "__main__":
    main()
