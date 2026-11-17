"""Verify an encrypted archive using a private key without DPAPI or a DB connection."""
import argparse
import base64
import getpass
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

MAGIC = b"ETVOTP1\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup")
    parser.add_argument("capsule")
    parser.add_argument("private_key", help="password-protected PEM RSA private key")
    args = parser.parse_args()
    encrypted = Path(args.backup).read_bytes()
    capsule = json.loads(Path(args.capsule).read_text(encoding="utf-8"))
    digest = hashlib.sha256(encrypted).digest()
    if (not encrypted.startswith(MAGIC) or capsule.get("version") != 1
            or capsule.get("algorithm") != "RSA-OAEP-SHA256"
            or capsule.get("backup_sha256") != digest.hex()):
        raise RuntimeError("Backup and recovery capsule do not match")
    password = getpass.getpass("Private key passphrase: ").encode()
    private_key = serialization.load_pem_private_key(Path(args.private_key).read_bytes(), password=password)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise RuntimeError("Expected an RSA private key")
    public_der = private_key.public_key().public_bytes(serialization.Encoding.DER,
                                                         serialization.PublicFormat.SubjectPublicKeyInfo)
    if hashlib.sha256(public_der).hexdigest() != capsule["public_key_sha256"]:
        raise RuntimeError("Private key does not match the recovery identity")
    key = private_key.decrypt(base64.b64decode(capsule["wrapped_key_base64"], validate=True),
                              padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                           algorithm=hashes.SHA256(), label=digest))
    size = struct.unpack(">I", encrypted[len(MAGIC):len(MAGIC)+4])[0]
    archive = Fernet(key).decrypt(encrypted[len(MAGIC)+4+size:])
    result = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "postgres:18",
                             "pg_restore", "--list"], input=archive, capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Decryption succeeded, but pg_restore could not read the archive")
    print("Portable recovery identity decrypts backup; PostgreSQL archive is readable.")
    print("No production database connection was made.")


if __name__ == "__main__":
    main()
