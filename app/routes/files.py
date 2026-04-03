import os

from flask import Blueprint, jsonify, request, send_file
from app.auth import login_required
from app.services.file_service import FileService
from config import Config
from flask import render_template

files_bp = Blueprint("files", __name__)
file_service = FileService()


@files_bp.route("/files")
@login_required
def index():
    return render_template("files.html")


@files_bp.route("/api/files/list")
@login_required
def list_files():
    path = request.args.get("path", os.path.expanduser("~"))
    try:
        entries = file_service.list_directory(path)
        return jsonify({"path": path, "entries": entries})
    except (PermissionError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400


@files_bp.route("/api/files/download")
@login_required
def download():
    path = request.args.get("path", "")
    if not path or not os.path.isfile(path):
        return jsonify({"error": "File not found"}), 404
    try:
        file_service.validate_path(path)
        return send_file(path, as_attachment=True)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403


@files_bp.route("/api/files/upload", methods=["POST"])
@login_required
def upload():
    dest = request.form.get("dest", Config.UPLOAD_DIR)
    try:
        file_service.validate_path(dest)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    uploaded = request.files.getlist("file")
    saved = []
    for f in uploaded:
        if f.filename:
            safe_name = os.path.basename(f.filename)
            save_path = os.path.join(dest, safe_name)
            os.makedirs(dest, exist_ok=True)
            f.save(save_path)
            saved.append(safe_name)

    return jsonify({"uploaded": saved})


@files_bp.route("/api/files/delete", methods=["POST"])
@login_required
def delete():
    data = request.get_json()
    if not data or "path" not in data:
        return jsonify({"error": "No path provided"}), 400

    path = data["path"]
    try:
        file_service.validate_path(path)
        if os.path.isfile(path):
            os.remove(path)
            return jsonify({"deleted": path})
        else:
            return jsonify({"error": "Not a file"}), 400
    except (ValueError, PermissionError) as e:
        return jsonify({"error": str(e)}), 403
