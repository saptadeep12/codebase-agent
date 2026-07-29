🔗 **Live Demo:** [https://codebase-agent-black.vercel.app/](https://codebase-agent-black.vercel.app/)

---

# 🔍 Codebase Agent

An AI-powered assistant that lets you query any GitHub repository or chat with your PDF documents using natural language. Built with FastAPI and LangGraph, with real-time streaming responses.

---

## ✨ Features

- **Codebase Q&A** — Point it at any public GitHub repo and ask questions about the code, architecture, or logic. Powered by a LangGraph ReAct agent with GitHub API tools.
- **Document Chat** — Upload a PDF and have a conversation with it. Uses FAISS vector search and hosted HuggingFace embeddings for accurate retrieval.
- **Real-time Streaming** — Both agents stream responses token by token via SSE (Server-Sent Events).
- **Conversation Memory** — Document chat sessions retain context across multiple questions.
- **Rate Limiting** — Built-in request throttling to protect against abuse.
- **File Size Limits** — PDF uploads capped at 10MB to prevent resource exhaustion.

---

## 🛠 Tech Stack

| Layer | Tools |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Agent | LangGraph, LangChain, Groq LLM |
| RAG | FAISS, HuggingFace Inference API (hosted embeddings), PyPDF |
| Streaming | Server-Sent Events (SSE) |
| Rate Limiting | SlowAPI |
| Frontend | Vanilla HTML/CSS/JS, Marked.js |

---

## 📁 Project Structure

```
codebase-agent/
├── agent/
│   ├── __init__.py
│   ├── graph.py        # LangGraph ReAct agent
│   ├── state.py         # Agent state definition
│   └── tools.py         # GitHub API tools
├── frontend/
│   ├── index.html       # Codebase agent UI
│   ├── index.js         # Codebase agent frontend logic
│   ├── doc.html          # Document chat UI
│   └── doc.js            # Document chat frontend logic
├── main.py              # Unified FastAPI app
├── requirements.txt
└── .env                 # API keys (never commit this)
```
---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/specter2028/codebase-agent.git
cd codebase-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root:

GROQ_API_KEY=your_groq_api_key
HF_API_KEY=your_huggingface_api_key

- **Groq** — used for the LLM (chat completions)
- **HuggingFace** — used for hosted embeddings (Document Chat / RAG)

### 5. Run the server

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000` in your browser.

---

## 🌐 API Routes

| Method | Route | Description | Rate Limit |
|---|---|---|---|
| GET | `/` | Codebase agent UI | — |
| GET | `/doc` | Document chat UI | — |
| POST | `/ask` | Query a GitHub repo (SSE stream) | 10/min |
| POST | `/doc/upload` | Upload a PDF (max 10MB) | 5/min |
| POST | `/doc/chat` | Chat with uploaded PDF (SSE stream) | 15/min |
| DELETE | `/doc/session/{id}` | Delete a PDF session | — |

---

## 🔑 Getting API Keys

- **Groq** — [console.groq.com](https://console.groq.com)
- **HuggingFace** — [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (enable "Make calls to Inference Providers" permission)

---

## 📦 Deploying to Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo and set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in the **Environment** tab:
GROQ_API_KEY = your_groq_key
HF_API_KEY = your_huggingface_key
5. Deploy

> **Note:** The free Render tier spins down after 15 minutes of inactivity. The first request after idle time may take 30-50 seconds to respond as the instance wakes up.

---

## ⚠️ Limitations

- PDF sessions are stored in-memory and are lost on server restart or redeploy.
- Free-tier Render instances have 512MB RAM — be mindful of dependency size if extending the project.
