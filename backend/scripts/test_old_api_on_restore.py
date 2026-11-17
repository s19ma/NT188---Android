"""Test backed-up production API code on the local migrated restore only."""
import io
import os
from pathlib import Path, PurePosixPath
import struct
import subprocess
import sys
import tarfile
import tempfile
from cryptography.fernet import Fernet
from scripts.production_backup_readonly import MAGIC
from scripts.verify_production_backup_local import unprotect_key


def main():
    folder = Path(os.environ["LOCALAPPDATA"]) / "EnglishThroughVideo" / "production-backups"
    files = list(folder.glob("azure-code-config-*.tar.gz.fernet"))
    if len(files) != 1:
        raise RuntimeError("Expected one encrypted code/config backup")
    encrypted = files[0].read_bytes()
    if not encrypted.startswith(MAGIC):
        raise RuntimeError("Invalid archive")
    size = struct.unpack(">I", encrypted[len(MAGIC):len(MAGIC)+4])[0]
    start = len(MAGIC) + 4
    data = Fernet(unprotect_key(encrypted[start:start+size])).decrypt(encrypted[start+size:])
    prefix = PurePosixPath("home/azureuser/english-video/backend/app")
    with tempfile.TemporaryDirectory(prefix="etv-old-api-") as temporary:
        target = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                parts = PurePosixPath(member.name)
                if member.isfile() and prefix in parts.parents and ".." not in parts.parts:
                    destination = target / "app" / Path(*parts.relative_to(prefix).parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.extractfile(member).read())
        env = os.environ.copy()
        local = "postgresql://postgres:local_restore_only@127.0.0.1:55432/otp_restore"
        env.update(DATABASE_URL=local, DIRECT_DATABASE_URL=local, JWT_SECRET_KEY="local-restore-only",
                   AZURE_STORAGE_ACCOUNT_NAME="local-restore", AZURE_STORAGE_ACCOUNT_KEY="local-restore",
                   PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE="1")
        program = r'''
import uuid
from fastapi.testclient import TestClient
from app.main import app
email = 'old_api_' + uuid.uuid4().hex + '@example.com'
password = 'localtestpassword123'
with TestClient(app) as client:
    assert client.get('/health').status_code == 200
    assert client.get('/health/models').status_code == 200
    assert client.post('/api/v1/users/register', json={'email': email, 'password': password}).status_code == 201
    login = client.post('/api/v1/users/login', data={'username': email, 'password': password})
    assert login.status_code == 200
    token = login.json()['access_token']
    assert client.get('/api/v1/users/me', headers={'Authorization': 'Bearer ' + token}).status_code == 200
'''
        result = subprocess.run([sys.executable, "-c", program], cwd=target, env=env,
                                capture_output=True, timeout=60)
        if result.returncode:
            raise RuntimeError("Old production API compatibility check failed")
    print("Backed-up old API: health, models, synthetic registration/login/me pass on migrated local restore")
    print("Warning: old API registration bypasses new OTP until it is replaced")


if __name__ == "__main__":
    main()
