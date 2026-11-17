"""Check the backed-up production API on the migrated loopback restore only."""
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
    path=Path(os.environ['LOCALAPPDATA'])/'EnglishThroughVideo/production-backups/azure-code-config-20261116T121709Z.tar.gz.fernet'
    b=path.read_bytes()
    if not b.startswith(MAGIC): raise RuntimeError('Unexpected backup format')
    n=struct.unpack('>I',b[len(MAGIC):len(MAGIC)+4])[0]; i=len(MAGIC)+4
    archive=Fernet(unprotect_key(b[i:i+n])).decrypt(b[i+n:])
    prefix=PurePosixPath('home/azureuser/english-video/backend/app')
    with tempfile.TemporaryDirectory(prefix='flashcard-old-api-') as name:
        root=Path(name)
        with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as t:
            for entry in t:
                p=PurePosixPath(entry.name)
                if entry.isfile() and prefix in p.parents and '..' not in p.parts:
                    dest=root/'app'/Path(*p.relative_to(prefix).parts); dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(t.extractfile(entry).read())
        local='postgresql://postgres:local_restore_only@127.0.0.1:55432/otp_restore'
        env=os.environ.copy()
        env.update(DATABASE_URL=local,DIRECT_DATABASE_URL=local,JWT_SECRET_KEY='local-only-secret-at-least-32-characters',
                   APP_ENVIRONMENT='development',EMAIL_DELIVERY_MODE='disabled',AZURE_STORAGE_ACCOUNT_NAME='test-only',
                   AZURE_STORAGE_ACCOUNT_KEY='test-only',PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1')
        program=r'''
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import SessionLocal,engine
from app.models.user import User
from app.core.security import hash_password
assert engine.url.host=='127.0.0.1' and engine.url.port==55432 and engine.url.database=='otp_restore'
email='compat_'+uuid4().hex+'@example.com'
with SessionLocal() as db:
 db.add(User(id=uuid4(),email=email,password_hash=hash_password('fixturepassword123'),email_verified=True)); db.commit()
with TestClient(app) as client:
 assert client.get('/health').status_code==200
 assert client.get('/health/models').status_code==200
 login=client.post('/api/v1/users/login',data={'username':email,'password':'fixturepassword123'})
 assert login.status_code==200
 headers={'Authorization':'Bearer '+login.json()['access_token']}
 assert client.get('/api/v1/users/me',headers=headers).status_code==200
 assert client.get('/api/v1/users/me/flashcards',headers=headers).status_code==200
 assert client.get('/api/v1/users/me/flashcards/overview',headers=headers).status_code==200
'''
        result=subprocess.run([sys.executable,'-c',program],cwd=root,env=env,capture_output=True,timeout=60)
        if result.returncode: raise RuntimeError('Old production API check on migrated restore failed')
    print('Old production API on migrated local restore: health, model queries, login, me and flashcard GET passed.')


if __name__=='__main__': main()
