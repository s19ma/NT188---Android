"""Wrap a backup key for an independent RSA recovery identity.

The public key or certificate must be provided by the operator. No private key
or unencrypted backup key is written; keep the recovery capsule with its backup.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from scripts.production_backup_readonly import MAGIC
from scripts.verify_production_backup_local import unprotect_key


def wrap(public_key, secret, backup_digest):
    if not isinstance(public_key, rsa.RSAPublicKey) or public_key.key_size < 2048:
        raise ValueError("An RSA public key of at least 2048 bits is required")
    return public_key.encrypt(secret, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                                  algorithm=hashes.SHA256(), label=backup_digest))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", help="encrypted backup in the protected backup directory")
    parser.add_argument("public_key", help="PEM RSA public key or PEM certificate")
    args = parser.parse_args()
    folder = (Path(os.environ["LOCALAPPDATA"]) / "EnglishThroughVideo" / "production-backups").resolve()
    backup = Path(args.backup).resolve(strict=True)
    if backup.parent != folder or not backup.name.endswith(".fernet"):
        raise RuntimeError("Backup must be in the protected backup directory")
    public_bytes = Path(args.public_key).read_bytes()
    try:
        public_key = serialization.load_pem_public_key(public_bytes)
    except ValueError:
        public_key = x509.load_pem_x509_certificate(public_bytes).public_key()
    encrypted = backup.read_bytes()
    if not encrypted.startswith(MAGIC):
        raise RuntimeError("Unexpected backup format")
    n = struct.unpack(">I", encrypted[len(MAGIC):len(MAGIC)+4])[0]
    start = len(MAGIC) + 4
    wrapped_dpapi = encrypted[start:start+n]
    if not wrapped_dpapi or n > 65536:
        raise RuntimeError("Invalid backup key wrapper")
    key = unprotect_key(wrapped_dpapi)
    digest = hashlib.sha256(encrypted).digest()
    ciphertext = wrap(public_key, key, digest)
    public_der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    capsule = {"version": 1, "algorithm": "RSA-OAEP-SHA256", "backup_sha256": digest.hex(),
               "public_key_sha256": hashlib.sha256(public_der).hexdigest(),
               "wrapped_key_base64": base64.b64encode(ciphertext).decode("ascii")}
    destination = folder / (backup.name + ".recovery.json")
    with destination.open("x", encoding="utf-8") as f:
        json.dump(capsule, f, sort_keys=True, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    print("Recovery capsule created:", destination)
    print("Backup SHA-256:", digest.hex().upper())
    print("Public key SHA-256:", capsule["public_key_sha256"].upper())


if __name__ == "__main__":
    main()
