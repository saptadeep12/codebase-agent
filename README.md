# 🔍 Codebase Agent

An AI-powered assistant that lets you query any GitHub repository or chat with your PDF documents using natural language. Built with FastAPI and LangGraph, with real-time streaming responses.

---

## ✨ Features

- **Codebase Q&A** — Point it at any public GitHub repo and ask questions about the code, architecture, or logic. Powered by a LangGraph ReAct agent with GitHub API tools.
- **Document Chat** — Upload a PDF and have a conversation with it. Uses FAISS vector search and HuggingFace embeddings for accurate retrieval.
- **Real-time Streaming** — Both agents stream responses token by token via SSE (Server-Sent Events).
- **Conversation Memory** — Document chat sessions retain context across multiple questions.

---

## 🛠 Tech Stack

| Layer | Tools |
|---|---|
| Backend | FastAPI, Python 3.11 |
| Agent | LangGraph, LangChain, Groq LLM |
| RAG | FAISS, HuggingFace Sentence Transformers, PyPDF |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla HTML/CSS/JS, Marked.js |

---

## 📁 Project Structure

```
codebase-agent/
├── agent/
│   ├── __init__.py
│   ├── graph.py        # LangGraph ReAct agent
│   ├── state.py        # Agent state definition
│   └── tools.py        # GitHub API tools
├── frontend/
│   ├── index.html      # Codebase agent UI
│   └── doc.html        # Document chat UI
├── main.py             # Unified FastAPI app
├── requirements.txt
└── .env                # API keys (never commit this)
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

```
GROQ_API_KEY=your_groq_api_key
```

### 5. Run the server

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000` in your browser.

---

## 🌐 API Routes

| Method | Route | Description |
|---|---|---|
| GET | `/` | Codebase agent UI |
| GET | `/doc` | Document chat UI |
| POST | `/ask` | Query a GitHub repo (SSE stream) |
| POST | `/doc/upload` | Upload a PDF |
| POST | `/doc/chat` | Chat with uploaded PDF (SSE stream) |
| DELETE | `/doc/session/{id}` | Delete a PDF session |

---

## 🔑 Getting API Keys

- **Groq** — [console.groq.com](https://console.groq.com)

---

## 📦 Deploying to Render

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo and set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add `GROQ_API_KEY` in the Environment tab
5. Deploy