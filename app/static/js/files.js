(function () {
    const fileList = document.getElementById("file-list");
    const pathInput = document.getElementById("path-input");
    const btnGo = document.getElementById("btn-go");
    const btnUp = document.getElementById("btn-up");
    const btnUpload = document.getElementById("btn-upload");
    const fileInput = document.getElementById("file-input");
    const dropZone = document.getElementById("drop-zone");

    let currentPath = "";

    function formatSize(bytes) {
        if (bytes === null || bytes === undefined) return "-";
        const units = ["B", "KB", "MB", "GB", "TB"];
        let i = 0;
        let size = bytes;
        while (size >= 1024 && i < units.length - 1) {
            size /= 1024;
            i++;
        }
        return size.toFixed(1) + " " + units[i];
    }

    function formatDate(iso) {
        if (!iso) return "-";
        const d = new Date(iso);
        return d.toLocaleString();
    }

    function loadPath(path) {
        currentPath = path;
        pathInput.value = path;

        fetch("/api/files/list?path=" + encodeURIComponent(path))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    fileList.innerHTML = '<tr><td colspan="4" style="color:#ff6b6b">' + data.error + "</td></tr>";
                    return;
                }
                currentPath = data.path;
                pathInput.value = data.path;
                renderFiles(data.entries);
            })
            .catch(function (err) {
                fileList.innerHTML = '<tr><td colspan="4" style="color:#ff6b6b">Error: ' + err.message + "</td></tr>";
            });
    }

    function renderFiles(entries) {
        fileList.innerHTML = "";
        entries.forEach(function (entry) {
            const tr = document.createElement("tr");

            const tdName = document.createElement("td");
            if (entry.is_dir) {
                tdName.className = "dir";
                tdName.textContent = "\uD83D\uDCC1 " + entry.name;
                tdName.addEventListener("click", function () {
                    loadPath(entry.path);
                });
            } else {
                tdName.textContent = "\uD83D\uDCC4 " + entry.name;
            }

            const tdSize = document.createElement("td");
            tdSize.textContent = entry.is_dir ? "-" : formatSize(entry.size);

            const tdMod = document.createElement("td");
            tdMod.textContent = formatDate(entry.modified);

            const tdActions = document.createElement("td");
            tdActions.className = "file-actions";

            if (!entry.is_dir) {
                const dlBtn = document.createElement("button");
                dlBtn.textContent = "Download";
                dlBtn.addEventListener("click", function () {
                    window.location.href = "/api/files/download?path=" + encodeURIComponent(entry.path);
                });
                tdActions.appendChild(dlBtn);
            }

            const delBtn = document.createElement("button");
            delBtn.textContent = "Delete";
            delBtn.className = "delete";
            delBtn.addEventListener("click", function () {
                if (!confirm("Delete " + entry.name + "?")) return;
                fetch("/api/files/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ path: entry.path }),
                })
                    .then(function (r) { return r.json(); })
                    .then(function () { loadPath(currentPath); });
            });
            if (!entry.is_dir) {
                tdActions.appendChild(delBtn);
            }

            tr.appendChild(tdName);
            tr.appendChild(tdSize);
            tr.appendChild(tdMod);
            tr.appendChild(tdActions);
            fileList.appendChild(tr);
        });
    }

    function uploadFiles(files) {
        const formData = new FormData();
        formData.append("dest", currentPath);
        for (let i = 0; i < files.length; i++) {
            formData.append("file", files[i]);
        }
        fetch("/api/files/upload", {
            method: "POST",
            body: formData,
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    alert("Upload error: " + data.error);
                } else {
                    loadPath(currentPath);
                }
            })
            .catch(function (err) {
                alert("Upload failed: " + err.message);
            });
    }

    btnGo.addEventListener("click", function () {
        loadPath(pathInput.value);
    });

    pathInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") loadPath(pathInput.value);
    });

    btnUp.addEventListener("click", function () {
        const parts = currentPath.replace(/\/+$/, "").split("/");
        parts.pop();
        const parent = parts.join("/") || "/";
        loadPath(parent);
    });

    btnUpload.addEventListener("click", function () {
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        if (fileInput.files.length > 0) {
            uploadFiles(fileInput.files);
            fileInput.value = "";
        }
    });

    // Drag and drop
    dropZone.addEventListener("dragover", function (e) {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });

    dropZone.addEventListener("dragleave", function () {
        dropZone.classList.remove("dragover");
    });

    dropZone.addEventListener("drop", function (e) {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });

    // Initial load - home directory
    loadPath("");
})();
