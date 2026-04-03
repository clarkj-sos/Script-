import os
import secrets


class Config:
    HOST = os.environ.get("RDC_HOST", "0.0.0.0")
    PORT = int(os.environ.get("RDC_PORT", 5000))
    PASSWORD = os.environ.get("RDC_PASSWORD", "")
    SECRET_KEY = os.environ.get("RDC_SECRET_KEY", secrets.token_hex(32))
    SCREEN_FPS = int(os.environ.get("RDC_FPS", 10))
    JPEG_QUALITY = int(os.environ.get("RDC_JPEG_QUALITY", 50))
    UPLOAD_DIR = os.environ.get("RDC_UPLOAD_DIR", "/tmp/rdc_uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("RDC_MAX_UPLOAD_MB", 100)) * 1024 * 1024
    CERT_FILE = os.environ.get("RDC_CERT_FILE", "cert.pem")
    KEY_FILE = os.environ.get("RDC_KEY_FILE", "key.pem")
    SESSION_TIMEOUT_MINUTES = int(os.environ.get("RDC_SESSION_TIMEOUT", 30))
    LOGIN_RATE_LIMIT = int(os.environ.get("RDC_LOGIN_RATE_LIMIT", 5))
