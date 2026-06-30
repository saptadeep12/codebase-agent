let sessionId = null;
let isStreaming = false;

const output     = document.getElementById("output");
const askBtn     = document.getElementById("askBtn");
const questionEl = document.getElementById("question");
const statusBar  = document.getElementById("status-bar");
const statusDot  = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const uploadZone = document.getElementById("upload-zone");
const fileLabel  = document.getElementById("file-label");
const uploadHint = document.getElementById("upload-hint");

// ── Drag & drop ──────────────────────────────────────────────────────────────
function onDragOver(e) { e.preventDefault(); uploadZone.classList.add("drag-over"); }
function onDragLeave()  { uploadZone.classList.remove("drag-over"); }
function onDrop(e) {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
}
function onFileSelected(e) {
  const file = e.target.files[0];
  if (file) uploadFile(file);
}

// ── Upload ────────────────────────────────────────────────────────────────────
async function uploadFile(file) {
  if (!file.name.endsWith(".pdf")) {
    setStatus("Only PDF files are supported.", false, true);
    return;
  }

  uploadZone.classList.add("has-file");
  fileLabel.textContent = file.name;
  uploadHint.textContent = "Processing...";
  setStatus("Embedding document...", true);

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/doc/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Upload failed");

    sessionId = data.session_id;
    uploadHint.textContent = `${data.num_chunks} chunks indexed`;
    setStatus(`Ready — ${file.name}`, false);
    enableChat();
    output.innerHTML = "";
  } catch (e) {
    uploadHint.textContent = "Upload failed — try again";
    setStatus(`Error: ${e.message}`, false, true);
    uploadZone.classList.remove("has-file");
    fileLabel.textContent = "";
  }
}

// ── Chat ──────────────────────────────────────────────────────────────────────
async function ask() {
  if (isStreaming || !sessionId) return;

  const question = questionEl.value.trim();
  if (!question) return;

  questionEl.value = "";
  isStreaming = true;
  askBtn.disabled = true;
  questionEl.disabled = true;

  output.innerHTML += `<div class="divider"></div><div class="question-line">▶ ${escapeHtml(question)}</div>`;

  const answerDiv = document.createElement("div");
  answerDiv.className = "answer";
  output.appendChild(answerDiv);

  let rawTokens = "";

  try {
    const res = await fetch("/doc/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Request failed");
    }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer    = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === "token") {
            rawTokens += data.content;
            answerDiv.innerHTML = marked.parse(rawTokens);
          } else if (data.type === "done") {
            answerDiv.innerHTML = marked.parse(rawTokens);
            answerDiv.innerHTML += `<span class="done-line">─── done ───</span>`;
          } else if (data.type === "error") {
            answerDiv.innerHTML += `<span class="error">Error: ${escapeHtml(data.content)}</span>`;
          }
        } catch (e) {}
      }
    }
  } catch (e) {
    answerDiv.innerHTML += `<span class="error">Error: ${escapeHtml(e.message)}</span>`;
  } finally {
    isStreaming = false;
    askBtn.disabled = false;
    questionEl.disabled = false;
    questionEl.focus();
    output.scrollTop = output.scrollHeight;
  }
}

// ── Clear session ─────────────────────────────────────────────────────────────
async function clearSession() {
  if (sessionId) {
    await fetch(`/doc/session/${sessionId}`, { method: "DELETE" }).catch(() => {});
    sessionId = null;
  }
  output.innerHTML = "";
  uploadZone.classList.remove("has-file");
  fileLabel.textContent = "";
  uploadHint.textContent = "Supports PDF files";
  document.getElementById("file-input").value = "";
  statusBar.classList.remove("visible");
  disableChat();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function enableChat() {
  questionEl.disabled = false;
  askBtn.disabled = false;
  questionEl.placeholder = "Ask anything about the document...";
  questionEl.focus();
}

function disableChat() {
  questionEl.disabled = true;
  askBtn.disabled = true;
  questionEl.placeholder = "Upload a PDF to start asking questions...";
}

function setStatus(msg, loading = false, error = false) {
  statusBar.classList.add("visible");
  statusDot.className = "status-dot" + (loading ? " loading" : "");
  statusDot.style.background = error ? "#f48771" : loading ? "#f7a26a" : "#98c379";
  statusText.textContent = msg;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

questionEl.addEventListener("keydown", e => {
  if (e.key === "Enter" && !isStreaming && sessionId) ask();
});