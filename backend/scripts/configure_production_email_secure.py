"""Install the approved existing SMTP secret and prepared Fernet key over SSH stdin."""
import base64
import json
import os
from pathlib import Path
import subprocess
from dotenv import dotenv_values
from cryptography.fernet import Fernet
from scripts.verify_production_backup_local import unprotect_key


REMOTE = r'''
import json, os, stat, sys
from dotenv import dotenv_values, set_key
path='/home/azureuser/english-video/backend/.env'
allowed={'EMAIL_DELIVERY_MODE','EMAIL_OUTBOX_ENCRYPTION_KEY','SMTP_HOST','SMTP_PORT',
         'SMTP_USERNAME','SMTP_PASSWORD','SMTP_FROM_EMAIL','SMTP_FROM_NAME','SMTP_USE_TLS'}
tmp=None
try:
 data=json.load(sys.stdin)
 if set(data)!=allowed or not all(isinstance(x,str) and x for x in data.values()): raise ValueError('invalid input')
 old=dotenv_values(path)
 if any(old.get(k) for k in ('SMTP_PASSWORD','EMAIL_OUTBOX_ENCRYPTION_KEY')): raise ValueError('secret already configured')
 st=os.stat(path)
 if stat.S_IMODE(st.st_mode)!=0o600 or st.st_uid!=os.getuid(): raise ValueError('unsafe environment ownership or permissions')
 raw=open(path,'rb').read()
 tmp=path+'.otp-new-'+str(os.getpid())
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
 for key,value in data.items(): set_key(tmp,key,value,quote_mode='always')
 new=dotenv_values(tmp)
 if any(new.get(k)!=v for k,v in old.items() if k not in allowed): raise ValueError('unrelated configuration changed')
 if any(new.get(k)!=v for k,v in data.items()): raise ValueError('configuration validation failed')
 if stat.S_IMODE(os.stat(tmp).st_mode)!=0o600: raise ValueError('unsafe new file permissions')
 os.replace(tmp,path); tmp=None
 directory=os.open(os.path.dirname(path),os.O_RDONLY)
 try: os.fsync(directory)
 finally: os.close(directory)
 print('SMTP and Fernet environment configured; existing unrelated settings preserved.')
except Exception:
 print('Configuration failed or existing protected values require review.',file=sys.stderr)
 if tmp and os.path.exists(tmp): os.unlink(tmp)
 sys.exit(1)
'''


def main():
    local = dotenv_values('.env')
    folder = Path(os.environ['LOCALAPPDATA']) / 'EnglishThroughVideo' / 'production-backups'
    key = unprotect_key((folder / 'production-fernet.dpapi').read_bytes()).decode('ascii')
    Fernet(key.encode())
    if local.get('SMTP_HOST') != 'smtp-relay.brevo.com' or local.get('SMTP_USERNAME') != 'c37521001@smtp-brevo.com':
        raise RuntimeError('Unexpected SMTP account')
    if local.get('SMTP_FROM_EMAIL') != 'no-reply@englishthroughvideo.aclclouds.online' or not local.get('SMTP_PASSWORD'):
        raise RuntimeError('Expected sender or current SMTP key is missing')
    payload = {'EMAIL_DELIVERY_MODE':'smtp', 'EMAIL_OUTBOX_ENCRYPTION_KEY':key,
               'SMTP_HOST':local['SMTP_HOST'], 'SMTP_PORT':'587', 'SMTP_USERNAME':local['SMTP_USERNAME'],
               'SMTP_PASSWORD':local['SMTP_PASSWORD'], 'SMTP_FROM_EMAIL':local['SMTP_FROM_EMAIL'],
               'SMTP_FROM_NAME':local.get('SMTP_FROM_NAME') or 'English Through Video', 'SMTP_USE_TLS':'true'}
    source = base64.b64encode(REMOTE.encode()).decode()
    command = "/home/azureuser/english-video/backend/.venv/bin/python -c \"exec(__import__('base64').b64decode('" + source + "'))\""
    keyfile = Path.cwd().parent / 'englishapi_key.pem'
    result = subprocess.run(['ssh','-i',str(keyfile),'-o','BatchMode=yes','-o','ConnectTimeout=8',
                             '-o','StrictHostKeyChecking=yes','azureuser@20.205.11.25',command],
                            input=json.dumps(payload).encode(),capture_output=True,timeout=30)
    if result.returncode:
        raise RuntimeError('Remote secret configuration failed; review without printing secrets')
    print(result.stdout.decode().strip())


if __name__ == '__main__':
    main()
