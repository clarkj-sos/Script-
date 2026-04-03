import functools
import time

from flask import Blueprint, render_template, request, session, redirect, url_for

from config import Config

auth_bp = Blueprint("auth", __name__)

# Rate limiting: {ip: [timestamps]}
_login_attempts = {}


def _check_rate_limit(ip):
    """Return True if the IP has exceeded the login rate limit."""
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    # Keep only attempts from the last 60 seconds
    attempts = [t for t in attempts if now - t < 60]
    _login_attempts[ip] = attempts
    return len(attempts) >= Config.LOGIN_RATE_LIMIT


def _record_attempt(ip):
    _login_attempts.setdefault(ip, []).append(time.time())


def login_required(f):
    """Decorator to require authentication for a route."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapped


def socket_login_required(f):
    """Decorator to require authentication for a SocketIO event."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        from flask import request as flask_request
        from flask_socketio import disconnect
        if not session.get("logged_in"):
            disconnect()
            return
        return f(*args, **kwargs)
    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        ip = request.remote_addr
        if _check_rate_limit(ip):
            error = "Too many login attempts. Try again later."
        else:
            _record_attempt(ip)
            password = request.form.get("password", "")
            if password == Config.PASSWORD:
                session["logged_in"] = True
                session.permanent = True
                return redirect(url_for("desktop.index"))
            error = "Invalid password."
    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
