async function fetchFiles() {
  const res = await fetch("/files");
  const files = await res.json();
  const select = document.getElementById("fileSelect");
  select.innerHTML = "";
  files.forEach((f) => {
    const opt = document.createElement("option");
    opt.value = f;
    opt.textContent = f;
    select.appendChild(opt);
  });
}

function appendLog(text) {
  const logBox = document.getElementById("logBox");
  logBox.textContent += text + "\n";
  logBox.scrollTop = logBox.scrollHeight;
}

async function runCleaner() {
  const filePath = document.getElementById("fileSelect").value;
  const lines = document.getElementById("linesInput").value || 3;

  if (!filePath) {
    alert("Please select an input file.");
    return;
  }

  appendLog("Starting…\n");

  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => {
    ws.send(JSON.stringify({ file_path: filePath, lines: lines }));
  };
  ws.onmessage = (ev) => {
    appendLog(ev.data);
  };
  ws.onclose = () => {
    appendLog("\n[connection closed]");
  };
  ws.onerror = (err) => {
    console.error("ws error", err);
  };
}

document.getElementById("runBtn").addEventListener("click", runCleaner);

fetchFiles();
