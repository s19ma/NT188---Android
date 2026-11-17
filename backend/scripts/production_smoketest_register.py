"""Create the authorized smoke-test account without printing its password or OTP."""
import os
from pathlib import Path
import secrets
import requests
from scripts.production_backup_readonly import protect_key


def main():
    folder = Path(os.environ['LOCALAPPDATA']) / 'EnglishThroughVideo' / 'production-backups'
    password_path = folder / 'production-smoketest-password-initial.dpapi'
    password = secrets.token_urlsafe(24)
    with password_path.open('xb') as file:
        file.write(protect_key(password.encode()))
        file.flush()
        os.fsync(file.fileno())
    try:
        response = requests.post('https://englishvideoapi20261114.eastasia.cloudapp.azure.com/api/v1/users/register',
                                 json={'email':'vietbactqd@gmail.com','password':password},timeout=25)
    except requests.RequestException:
        print('Registration outcome unknown; preserve the protected password and inspect the account before retrying.')
        raise SystemExit(1)
    print('Registration HTTP status:', response.status_code)
    if response.status_code != 201:
        print('Account creation not confirmed; preserve the protected password and inspect before retrying.')
        raise SystemExit(1)
    print('Initial test password is protected by current-user DPAPI; not printed.')


if __name__ == '__main__':
    main()
