import os
import stat
from datetime import datetime


class FileService:
    """Handles file system operations with path safety."""

    def validate_path(self, path):
        """Validate that a path is safe to access. Raises ValueError if not."""
        real = os.path.realpath(path)
        # Block access to sensitive files
        blocked = ["/proc/kcore", "/dev/mem"]
        for b in blocked:
            if real.startswith(b):
                raise ValueError(f"Access denied: {path}")
        return real

    def list_directory(self, path):
        """List contents of a directory."""
        real = self.validate_path(path)
        if not os.path.isdir(real):
            raise FileNotFoundError(f"Not a directory: {path}")

        entries = []
        try:
            for name in sorted(os.listdir(real)):
                full_path = os.path.join(real, name)
                try:
                    st = os.stat(full_path)
                    entries.append({
                        "name": name,
                        "path": full_path,
                        "is_dir": stat.S_ISDIR(st.st_mode),
                        "size": st.st_size if not stat.S_ISDIR(st.st_mode) else None,
                        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
                    })
                except (PermissionError, OSError):
                    entries.append({
                        "name": name,
                        "path": full_path,
                        "is_dir": False,
                        "size": None,
                        "modified": None,
                        "error": "Permission denied",
                    })
        except PermissionError:
            raise PermissionError(f"Cannot read directory: {path}")

        # Sort: directories first, then files
        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
        return entries

    @staticmethod
    def format_size(size):
        """Format file size in human-readable form."""
        if size is None:
            return "-"
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
