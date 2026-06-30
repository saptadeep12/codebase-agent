import os
import uuid
import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage

from agent.graph import agent
from fastapi.staticfiles import StaticFiles

# ── Config ───────────────────────────────────────────────────────────────────
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
EMBED_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL     = "openai/gpt-oss-120b"
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50
UPLOAD_DIR    = "/tmp/doc_uploads"
BASE_DIR      = Path(__file__).parent

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Shared state ──────────────────\───────────────────────────────────────────
sessions: dict = {}
embeddings = HuggingFaceInferenceAPIEmbeddings(
    api_key=os.getenv("HF_API_KEY"),
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)
app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ── Request / Response models ─────────────────────────────────────────────────
class Query(BaseModel):
    repo: str
    question: str

class ChatRequest(BaseModel):
    session_id: str
    question: str

class UploadResponse(BaseModel):
    session_id: str
    message: str
    num_chunks: int


# ── Helpers ───────────────────────────────────────────────────────────────────
def build_chain(vectorstore: FAISS) -> ConversationalRetrievalChain:
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=LLM_MODEL,
        streaming=True,
        temperature=0.2,
    )
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
    )
    return ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
        memory=memory,
        return_source_documents=False,
        output_key="answer",
    )


async def stream_answer(chain: ConversationalRetrievalChain, question: str) -> AsyncGenerator[str, None]:
    from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler

    handler = AsyncIteratorCallbackHandler()

    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=LLM_MODEL,
        streaming=True,
        temperature=0.2,
        callbacks=[handler],
    )
    chain.combine_docs_chain.llm_chain.llm = llm

    async def run_chain():
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chain({"question": question})
            )
        except Exception as e:
            handler.done.set()
            raise e
        finally:
            handler.done.set()

    task = asyncio.create_task(run_chain())

    async for token in handler.aiter():
        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    await task
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Routes: General ───────────────────────────────────────────────────────────
@app.get("/")
def root():
    return FileResponse(BASE_DIR / "frontend" / "index.html")

@app.get("/doc")
def doc_page():
    return FileResponse(BASE_DIR / "frontend" / "doc.html")


# ── Routes: Agent ─────────────────────────────────────────────────────────────
@app.post("/ask")
async def ask(query: Query):
    async def event_stream():
        try:
            inputs = {
                "messages": [
                    HumanMessage(content=f"Repo: {query.repo}\n\nQuestion: {query.question}")
                ]
            }
            async for event in agent.astream_events(inputs, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name'], 'input': str(event['data'].get('input', {}))})}\n\n"
                elif kind == "on_tool_end":
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name']})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Routes: Document RAG ──────────────────────────────────────────────────────
@app.post("/doc/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    session_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")

    contents = await file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    loader = PyPDFLoader(save_path)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(pages)

    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract text from the PDF.")

    vectorstore = FAISS.from_documents(chunks, embeddings)
    sessions[session_id] = build_chain(vectorstore)

    return UploadResponse(
        session_id=session_id,
        message=f"PDF '{file.filename}' processed successfully.",
        num_chunks=len(chunks),
    )


@app.post("/doc/chat")
async def chat_with_doc(req: ChatRequest):
    chain = sessions.get(req.session_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a PDF first.")

    return StreamingResponse(
        stream_answer(chain, req.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/doc/session/{session_id}")
async def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    sessions.pop(session_id, None)

    pdf_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    return {"message": "Session deleted."}