"""Verify the authorized smoke-test code, check login, and enqueue reset email."""
import os
from pathlib import Path
import sys
import requests
from scripts.verify_production_backup_local import unprotect_key


def main():
    code = sys.stdin.readline().strip()
    if len(code) != 6 or not code.isdigit():
        raise SystemExit('Expected a six-digit verification code')
    path = Path(os.environ['LOCALAPPDATA']) / 'EnglishThroughVideo/production-backups/production-smoketest-password-initial.dpapi'
    password = unprotect_key(path.read_bytes()).decode()
    base = 'https://englishvideoapi20261114.eastasia.cloudapp.azure.com/api/v1'
    email = 'vietbactqd@gmail.com'
    r = requests.post(base + '/auth/email-verification/confirm', json={'email': email, 'code': code}, timeout=20)
    print('Verification HTTP status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Verification failed; reset email was not requested')
    r = requests.post(base + '/users/login', data={'username': email, 'password': password}, timeout=20)
    print('Login HTTP status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Login failed; reset email was not requested')
    token = r.json()['access_token']
    r = requests.get(base + '/users/me', headers={'Authorization': 'Bearer ' + token}, timeout=20)
    print('Authenticated /users/me HTTP status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Profile check failed; reset email was not requested')
    r = requests.post(base + '/auth/password-reset/request', json={'email': email}, timeout=20)
    print('Password reset request HTTP status:', r.status_code)
    if r.status_code != 200:
        raise SystemExit('Reset request failed')


if __name__ == '__main__':
    main()
