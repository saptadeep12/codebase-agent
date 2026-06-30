const output = document.getElementById("output");
const askBtn = document.getElementById("askBtn");
let isStreaming = false;
let rawTokens = "";
let answerDiv = null;

// ── Ask ───────────────────────────────────────────────────────────────────────
async function ask() {
  if (isStreaming) return;

  const repo = document.getElementById("repo").value.trim();
  const questionEl = document.getElementById("question");
  const question = questionEl.value.trim();
  if (!repo || !question) return;

  questionEl.value = "";
  isStreaming = true;
  askBtn.disabled = true;
  rawTokens = "";

  output.innerHTML += `<div class="divider"></div><div class="question-line">▶ ${question}</div>`;

  const toolsDiv = document.createElement("div");
  output.appendChild(toolsDiv);

  answerDiv = document.createElement("div");
  answerDiv.className = "answer";
  output.appendChild(answerDiv);

  const loaderDiv = document.createElement("div");
  loaderDiv.className = "thinking-loader";
  loaderDiv.innerHTML = `<span class="dot"></span><span class="dot"></span><span class="dot"></span>`;
  output.appendChild(loaderDiv);
  output.scrollTop = output.scrollHeight;

  let firstTokenReceived = false;

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo, question })
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

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
            if (!firstTokenReceived) {
              firstTokenReceived = true;
              loaderDiv.remove();
            }
            rawTokens += data.content;
            answerDiv.innerHTML = marked.parse(rawTokens);
          } else if (data.type === "tool_start") {
            if (!firstTokenReceived) {
              firstTokenReceived = true;
              loaderDiv.remove();
            }
            toolsDiv.innerHTML += `<span class="tool-badge">⚙ ${data.tool}</span><span class="tool-input">${data.input}</span> `;
          } else if (data.type === "tool_end") {
            toolsDiv.innerHTML += `<span class="tool-badge tool-done">✓ ${data.tool}</span> `;
          } else if (data.type === "error") {
            loaderDiv.remove();
            answerDiv.innerHTML += `<span class="error">Error: ${data.content}</span>`;
          } else if (data.type === "done") {
            answerDiv.innerHTML += `<span class="done-line">─── done ───</span>`;
          }
        } catch (e) {}
      }
      output.scrollTop = output.scrollHeight;
    }
  } catch (e) {
    loaderDiv.remove();
    answerDiv.innerHTML += `<span class="error">Connection error: ${e.message}</span>`;
  } finally {
    isStreaming = false;
    askBtn.disabled = false;
    document.getElementById("question").focus();
  }
}

// ── Keyboard shortcut ─────────────────────────────────────────────────────────
document.getElementById("question").addEventListener("keydown", e => {
  if (e.key === "Enter" && !isStreaming) ask();
});