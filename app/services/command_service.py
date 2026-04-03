import os
import pty
import select
import struct
import fcntl
import termios


class PtySession:
    """Manages a PTY-based shell session."""

    def __init__(self):
        self.master_fd = None
        self.pid = None

    @property
    def alive(self):
        if self.pid is None:
            return False
        try:
            pid, _ = os.waitpid(self.pid, os.WNOHANG)
            return pid == 0
        except ChildProcessError:
            return False

    def start(self, cols=80, rows=24):
        """Start a new shell session using pty.fork()."""
        if self.alive:
            return

        self.close()
        self.pid, self.master_fd = pty.fork()

        if self.pid == 0:
            # Child: exec shell
            shell = os.environ.get("SHELL", "/bin/bash")
            os.execvp(shell, [shell])
        else:
            # Parent: set terminal size
            self.resize(cols, rows)

    def resize(self, cols, rows):
        """Resize the PTY."""
        if self.master_fd is not None:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)

    def write(self, data):
        """Write data to the PTY (keystrokes from client)."""
        if self.master_fd is not None:
            os.write(self.master_fd, data.encode() if isinstance(data, str) else data)

    def read(self, timeout=0.05):
        """Read available output from the PTY."""
        if self.master_fd is None:
            return b""
        try:
            ready, _, _ = select.select([self.master_fd], [], [], timeout)
            if ready:
                return os.read(self.master_fd, 4096)
        except OSError:
            return b""
        return b""

    def close(self):
        """Close the PTY session."""
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        if self.pid is not None and self.pid > 0:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass
            self.pid = None
