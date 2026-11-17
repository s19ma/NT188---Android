"""Finish the authorized production password-reset smoke test."""
import os
from pathlib import Path
import secrets
import sys
import requests
from scripts.production_backup_readonly import protect_key
from scripts.verify_production_backup_local import unprotect_key


def main():
    code = sys.stdin.readline().strip()
    if len(code) != 6 or not code.isdigit():
        raise SystemExit('Expected a six-digit reset code')
    folder = Path(os.environ['LOCALAPPDATA']) / 'EnglishThroughVideo/production-backups'
    old_password = unprotect_key((folder / 'production-smoketest-password-initial.dpapi').read_bytes()).decode()
    new_password = secrets.token_urlsafe(24)
    with (folder / 'production-smoketest-password-reset.dpapi').open('xb') as f:
        f.write(protect_key(new_password.encode()))
        f.flush()
        os.fsync(f.fileno())
    base = 'https://englishvideoapi20261114.eastasia.cloudapp.azure.com/api/v1'
    email = 'vietbactqd@gmail.com'
    r = requests.post(base + '/auth/password-reset/confirm',
                      json={'email': email, 'code': code, 'password': new_password}, timeout=20)
    print('Password reset HTTP status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Reset failed or outcome needs review; protected password files were retained')
    r = requests.post(base + '/users/login', data={'username': email, 'password': old_password}, timeout=20)
    print('Old-password login status:', r.status_code)
    if r.status_code != 401:
        raise SystemExit('Old-password login was not rejected as expected')
    r = requests.post(base + '/users/login', data={'username': email, 'password': new_password}, timeout=20)
    print('New-password login status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Login with new password failed')
    token = r.json()['access_token']
    r = requests.get(base + '/users/me', headers={'Authorization': 'Bearer ' + token}, timeout=20)
    print('Authenticated profile status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Authenticated profile check failed')
    print('New test password is protected by current-user DPAPI; not printed.')


if __name__ == '__main__':
    main()
