#!/usr/bin/env python3
"""Remote Desktop Control - Web-based remote control server."""

import os
import secrets
import ssl
import sys

from config import Config
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import datetime


def generate_self_signed_cert(cert_path, key_path):
    """Generate a self-signed TLS certificate if one doesn't exist."""
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return

    print("[*] Generating self-signed TLS certificate...")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Remote Desktop Control"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"[+] Certificate saved to {cert_path}")
    print(f"[+] Key saved to {key_path}")


def main():
    # Ensure password is set
    if not Config.PASSWORD:
        Config.PASSWORD = secrets.token_urlsafe(16)
        print(f"[*] No RDC_PASSWORD set. Generated password: {Config.PASSWORD}")
    else:
        print("[*] Using password from RDC_PASSWORD environment variable.")

    # Generate TLS cert
    generate_self_signed_cert(Config.CERT_FILE, Config.KEY_FILE)

    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    # Import app after config is ready
    from app import create_app, socketio

    app = create_app()

    print(f"\n[+] Remote Desktop Control Server")
    print(f"[+] URL: https://{Config.HOST}:{Config.PORT}")
    print(f"[+] Password: {Config.PASSWORD}")
    print(f"[+] Screen FPS: {Config.SCREEN_FPS}")
    print(f"[+] JPEG Quality: {Config.JPEG_QUALITY}")
    print()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(Config.CERT_FILE, Config.KEY_FILE)

    socketio.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        ssl_context=ssl_context,
        log_output=True,
    )


if __name__ == "__main__":
    main()
