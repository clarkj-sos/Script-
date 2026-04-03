(function () {
    const canvas = document.getElementById("screen");
    const ctx = canvas.getContext("2d");
    const status = document.getElementById("status");
    const fpsSlider = document.getElementById("fps");
    const qualitySlider = document.getElementById("quality");
    const wrapper = document.getElementById("canvasWrapper");

    let socket = null;
    let screenWidth = 1920;
    let screenHeight = 1080;
    let img = new Image();
    let lastMoveTime = 0;
    const MOVE_THROTTLE = 50; // ms

    // Key mapping from browser key names to pyautogui names
    const KEY_MAP = {
        "Control": "ctrl", "Shift": "shift", "Alt": "alt", "Meta": "win",
        "Enter": "enter", "Backspace": "backspace", "Tab": "tab",
        "Escape": "escape", "Delete": "delete", "Insert": "insert",
        "Home": "home", "End": "end", "PageUp": "pageup", "PageDown": "pagedown",
        "ArrowUp": "up", "ArrowDown": "down", "ArrowLeft": "left", "ArrowRight": "right",
        "CapsLock": "capslock", " ": "space",
        "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4",
        "F5": "f5", "F6": "f6", "F7": "f7", "F8": "f8",
        "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
    };

    function mapKey(key) {
        if (KEY_MAP[key]) return KEY_MAP[key];
        if (key.length === 1) return key.toLowerCase();
        return key.toLowerCase();
    }

    function translateCoords(e) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = screenWidth / rect.width;
        const scaleY = screenHeight / rect.height;
        return {
            x: Math.round((e.clientX - rect.left) * scaleX),
            y: Math.round((e.clientY - rect.top) * scaleY),
        };
    }

    function buttonName(btn) {
        switch (btn) {
            case 0: return "left";
            case 1: return "middle";
            case 2: return "right";
            default: return "left";
        }
    }

    function fitCanvas() {
        const ww = wrapper.clientWidth;
        const wh = wrapper.clientHeight;
        const ratio = screenWidth / screenHeight;
        let cw, ch;
        if (ww / wh > ratio) {
            ch = wh;
            cw = ch * ratio;
        } else {
            cw = ww;
            ch = cw / ratio;
        }
        canvas.style.width = cw + "px";
        canvas.style.height = ch + "px";
    }

    function connect() {
        socket = io({ transports: ["websocket", "polling"] });

        socket.on("connect", function () {
            status.textContent = "Connected";
            status.className = "status connected";
            socket.emit("start_stream", {
                fps: parseInt(fpsSlider.value),
                quality: parseInt(qualitySlider.value),
            });
        });

        socket.on("disconnect", function () {
            status.textContent = "Disconnected";
            status.className = "status disconnected";
        });

        socket.on("frame", function (data) {
            screenWidth = data.width;
            screenHeight = data.height;
            canvas.width = data.width;
            canvas.height = data.height;
            fitCanvas();

            img.onload = function () {
                ctx.drawImage(img, 0, 0);
            };
            img.src = "data:image/jpeg;base64," + data.data;
        });
    }

    // Mouse events
    canvas.addEventListener("mousemove", function (e) {
        if (!socket) return;
        const now = Date.now();
        if (now - lastMoveTime < MOVE_THROTTLE) return;
        lastMoveTime = now;
        const coords = translateCoords(e);
        socket.emit("mouse_move", coords);
    });

    canvas.addEventListener("mousedown", function (e) {
        e.preventDefault();
        if (!socket) return;
        const coords = translateCoords(e);
        coords.button = buttonName(e.button);
        socket.emit("mouse_down", coords);
    });

    canvas.addEventListener("mouseup", function (e) {
        e.preventDefault();
        if (!socket) return;
        const coords = translateCoords(e);
        coords.button = buttonName(e.button);
        socket.emit("mouse_up", coords);
    });

    canvas.addEventListener("click", function (e) {
        e.preventDefault();
        if (!socket) return;
        const coords = translateCoords(e);
        coords.button = buttonName(e.button);
        socket.emit("mouse_click", coords);
    });

    canvas.addEventListener("dblclick", function (e) {
        e.preventDefault();
        if (!socket) return;
        const coords = translateCoords(e);
        coords.button = buttonName(e.button);
        socket.emit("mouse_dblclick", coords);
    });

    canvas.addEventListener("wheel", function (e) {
        e.preventDefault();
        if (!socket) return;
        const coords = translateCoords(e);
        coords.delta = e.deltaY > 0 ? -3 : 3;
        socket.emit("mouse_scroll", coords);
    }, { passive: false });

    canvas.addEventListener("contextmenu", function (e) {
        e.preventDefault();
    });

    // Keyboard events
    document.addEventListener("keydown", function (e) {
        if (!socket || document.activeElement.tagName === "INPUT") return;
        e.preventDefault();
        socket.emit("key_down", { key: mapKey(e.key) });
    });

    document.addEventListener("keyup", function (e) {
        if (!socket || document.activeElement.tagName === "INPUT") return;
        e.preventDefault();
        socket.emit("key_up", { key: mapKey(e.key) });
    });

    // Slider changes
    function updateStream() {
        if (socket && socket.connected) {
            socket.emit("update_stream", {
                fps: parseInt(fpsSlider.value),
                quality: parseInt(qualitySlider.value),
            });
        }
    }

    fpsSlider.addEventListener("change", updateStream);
    qualitySlider.addEventListener("change", updateStream);

    window.addEventListener("resize", fitCanvas);

    connect();
})();
