"""Compare encrypted code/config backup with current Azure files without printing contents."""
import hashlib
import io
import os
from pathlib import Path
import struct
import subprocess
import tarfile
from cryptography.fernet import Fernet
from scripts.production_backup_readonly import MAGIC
from scripts.verify_production_backup_local import unprotect_key


def files(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        return {member.name: hashlib.sha256(archive.extractfile(member).read()).digest()
                for member in archive if member.isfile()}


def main():
    path = (Path(os.environ["LOCALAPPDATA"]) / "EnglishThroughVideo" / "production-backups" /
            "azure-code-config-20261116T072419Z.tar.gz.fernet")
    encoded = path.read_bytes()
    if not encoded.startswith(MAGIC):
        raise RuntimeError("Unexpected backup format")
    size = struct.unpack(">I", encoded[len(MAGIC):len(MAGIC)+4])[0]
    start = len(MAGIC)+4
    old = Fernet(unprotect_key(encoded[start:start+size])).decrypt(encoded[start+size:])
    root = "home/azureuser/english-video/backend/"
    paths = [root + name for name in ("app", "migrations", "scripts", ".env", "alembic.ini", "requirements.txt")]
    paths += ["etc/systemd/system/english-video-api.service", "etc/caddy/Caddyfile"]
    remote = "tar -C / --exclude=__pycache__ --exclude='*.pyc' -czf - " + " ".join(paths)
    keyfile = Path.cwd().parent / "englishapi_key.pem"
    result = subprocess.run(["ssh", "-i", str(keyfile), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                             "-o", "StrictHostKeyChecking=yes", "azureuser@20.205.11.25", remote],
                            capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Could not read Azure code/config")
    prior, current = files(old), files(result.stdout)
    changed = sorted(name for name in set(prior) | set(current) if prior.get(name) != current.get(name))
    print("Azure code/config files compared:", len(current), "changed:", len(changed))
    if changed:
        print("Changed paths:", *changed, sep="\n")
        raise RuntimeError("Code/config backup is stale")


if __name__ == "__main__":
    main()
