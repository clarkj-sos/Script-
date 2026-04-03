(function () {
    const termContainer = document.getElementById("terminal");
    const statusEl = document.getElementById("term-status");

    const term = new Terminal({
        cursorBlink: true,
        fontSize: 14,
        fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
        theme: {
            background: "#1a1a2e",
            foreground: "#e0e0e0",
            cursor: "#e94560",
        },
    });

    const fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(termContainer);
    fitAddon.fit();

    const socket = io({ transports: ["websocket", "polling"] });

    socket.on("connect", function () {
        statusEl.textContent = "Connected";
        statusEl.className = "status connected";
        socket.emit("term_open", {
            cols: term.cols,
            rows: term.rows,
        });
    });

    socket.on("disconnect", function () {
        statusEl.textContent = "Disconnected";
        statusEl.className = "status disconnected";
    });

    socket.on("term_output", function (data) {
        term.write(data.data);
    });

    socket.on("term_closed", function () {
        term.write("\r\n\x1b[31m[Session ended]\x1b[0m\r\n");
        // Reopen after a brief pause
        setTimeout(function () {
            socket.emit("term_open", { cols: term.cols, rows: term.rows });
        }, 1000);
    });

    // Send keystrokes to the server
    term.onData(function (data) {
        socket.emit("term_input", { data: data });
    });

    // Handle resize
    term.onResize(function (size) {
        socket.emit("term_resize", { cols: size.cols, rows: size.rows });
    });

    window.addEventListener("resize", function () {
        fitAddon.fit();
    });
})();
