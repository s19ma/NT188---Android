"""Verify portable recovery on the existing synthetic local Docker fixture."""
import base64
import hashlib
import json
import struct
import subprocess
from unittest.mock import patch

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from scripts.prepare_backup_recovery_capsule import wrap
from scripts.production_backup_readonly import MAGIC
from scripts import verify_portable_backup


def test_portable_recovery_without_dpapi(tmp_path):
    result = subprocess.run(["docker", "exec", "english-video-test-db", "pg_dump", "-Fc", "-U",
                             "test_user", "-d", "english_video_migration_test"],
                            capture_output=True, check=True, timeout=60)
    assert result.stdout.startswith(b"PGDMP")
    fernet_key = Fernet.generate_key()
    fake_dpapi = b"fixture-only"
    encrypted = MAGIC + struct.pack(">I", len(fake_dpapi)) + fake_dpapi + Fernet(fernet_key).encrypt(result.stdout)
    digest = hashlib.sha256(encrypted).digest()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    capsule = {"version": 1, "algorithm": "RSA-OAEP-SHA256", "backup_sha256": digest.hex(),
               "public_key_sha256": hashlib.sha256(der).hexdigest(),
               "wrapped_key_base64": base64.b64encode(wrap(public_key, fernet_key, digest)).decode()}
    archive_path = tmp_path / "test.pgdump.fernet"
    capsule_path = tmp_path / "test.recovery.json"
    key_path = tmp_path / "private.pem"
    archive_path.write_bytes(encrypted)
    capsule_path.write_text(json.dumps(capsule))
    key_path.write_bytes(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                   serialization.BestAvailableEncryption(b"fixture-passphrase")))
    with patch("sys.argv", ["verify_portable_backup", str(archive_path), str(capsule_path), str(key_path)]), \
         patch("getpass.getpass", return_value="fixture-passphrase"):
        verify_portable_backup.main()
