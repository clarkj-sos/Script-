import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


def test_config_defaults():
    """Test that Config has sensible defaults."""
    assert Config.HOST == "0.0.0.0"
    assert Config.PORT == 5000
    assert Config.SCREEN_FPS == 10
    assert Config.JPEG_QUALITY == 50
    assert Config.MAX_CONTENT_LENGTH == 100 * 1024 * 1024


def test_config_secret_key():
    """Test that a secret key is generated."""
    assert Config.SECRET_KEY is not None
    assert len(Config.SECRET_KEY) > 0


def test_file_service_validate_path():
    """Test path validation in FileService."""
    from app.services.file_service import FileService
    svc = FileService()
    result = svc.validate_path("/tmp")
    assert result == "/tmp"


def test_file_service_list_directory():
    """Test directory listing."""
    from app.services.file_service import FileService
    svc = FileService()
    entries = svc.list_directory("/tmp")
    assert isinstance(entries, list)


def test_file_service_format_size():
    """Test file size formatting."""
    from app.services.file_service import FileService
    assert FileService.format_size(None) == "-"
    assert FileService.format_size(512) == "512.0 B"
    assert FileService.format_size(1024) == "1.0 KB"
    assert FileService.format_size(1048576) == "1.0 MB"


def test_app_creation():
    """Test that the Flask app can be created."""
    from app import create_app
    app = create_app()
    assert app is not None
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_login_page():
    """Test that the login page is accessible."""
    from app import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"password" in resp.data.lower()


def test_protected_routes_redirect():
    """Test that protected routes redirect to login."""
    from app import create_app
    app = create_app()
    client = app.test_client()
    for path in ["/", "/terminal", "/files"]:
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code == 302
