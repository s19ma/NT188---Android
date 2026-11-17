"""Read production code/config over SSH and encrypt before writing locally."""
from datetime import datetime, timezone
import hashlib
import io
import os
from pathlib import Path
import struct
import subprocess
import tarfile

from cryptography.fernet import Fernet
from scripts.production_backup_readonly import MAGIC, protect_key


def main():
    folder = Path(os.environ["LOCALAPPDATA"]) / "EnglishThroughVideo" / "production-backups"
    if not folder.is_dir():
        raise RuntimeError("Protected backup directory is missing")
    keyfile = Path.cwd().parent / "englishapi_key.pem"
    root = "home/azureuser/english-video/backend/"
    paths = [root + name for name in ("app", "migrations", "scripts", ".env", "alembic.ini", "requirements.txt")]
    paths += ["etc/systemd/system/english-video-api.service", "etc/caddy/Caddyfile"]
    remote = "tar -C / --exclude=__pycache__ --exclude='*.pyc' -czf - " + " ".join(paths)
    result = subprocess.run(["ssh", "-i", str(keyfile), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                             "-o", "StrictHostKeyChecking=yes", "azureuser@20.205.11.25", remote],
                            capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError("Read-only SSH code/config backup failed")
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:gz") as archive:
        names = archive.getnames()
        if not all(name in names for name in (root + ".env", root + "alembic.ini",
                                                "etc/systemd/system/english-video-api.service")):
            raise RuntimeError("Code/config backup is incomplete")
    key = Fernet.generate_key()
    wrapped = protect_key(key)
    encrypted = MAGIC + struct.pack(">I", len(wrapped)) + wrapped + Fernet(key).encrypt(result.stdout)
    path = folder / ("azure-code-config-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".tar.gz.fernet")
    with path.open("xb") as file:
        file.write(encrypted)
        file.flush()
        os.fsync(file.fileno())
    print("Encrypted code/config backup:", path)
    print("SHA256:", hashlib.sha256(encrypted).hexdigest().upper())
    print("Archive entries:", len(names))


if __name__ == "__main__":
    main()
