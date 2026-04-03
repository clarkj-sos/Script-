from flask import Blueprint, render_template
from app.auth import login_required

terminal_bp = Blueprint("terminal", __name__)


@terminal_bp.route("/terminal")
@login_required
def index():
    return render_template("terminal.html")
