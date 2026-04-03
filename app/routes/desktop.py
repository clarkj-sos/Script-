from flask import Blueprint, render_template
from app.auth import login_required

desktop_bp = Blueprint("desktop", __name__)


@desktop_bp.route("/")
@login_required
def index():
    return render_template("desktop.html")
