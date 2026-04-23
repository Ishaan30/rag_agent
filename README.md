# RAG Chatbot

A conversational AI chatbot with Retrieval-Augmented Generation (RAG) and agent capabilities, built with FastAPI, LangChain, and Google Gemini.

## Features

- **Streaming chat** with conversation memory per session
- **Document Q&A** — upload a PDF or text file and ask questions about it
- **Agent with tools** — the chatbot decides when to use:
  - 🔍 **Web Search** (Tavily) — for current events and real-time information
  - 🌤️ **Weather** (Open-Meteo, no API key needed) — for weather queries
- **RAG pipeline** — chunks, embeds, and retrieves document context automatically

## Technology Stack

| Component | Choice | Reason |
|---|---|---|
| LLM | Google Gemini 2.5 Flash | Fast, capable, generous free tier |
| Embeddings | Gemini REST API (`gemini-embedding-001`) | Used REST directly to avoid gRPC timeout issues on restricted networks |
| Vector DB | FAISS | Zero setup, no persistence config, ideal for dev/demo |
| Framework | FastAPI | Async support, easy SSE streaming |
| Agent | LangChain AgentExecutor | Tool-calling agent with conversation history |

## Project Structure

```
rag-chatbot/
├── backend/
│   ├── main.py              # FastAPI app, CORS, routing
│   ├── state.py             # Shared session history + vector store
│   ├── requirements.txt
│   ├── routers/
│   │   ├── chat.py          # Streaming chat endpoint
│   │   └── documents.py     # File upload endpoint
│   ├── services/
│   │   ├── agent.py         # AgentExecutor, RAG retrieval, streaming
│   │   └── rag.py           # Document ingestion pipeline
│   └── tools/
│       ├── web_search.py    # Tavily web search tool
│       └── weather.py       # Open-Meteo weather tool
├── frontend/
│   └── index.html           # Single-file frontend (HTML/CSS/JS)
└── .env.example
```

## Required Environment Variables

| Variable | Description | Get it from |
|---|---|---|
| `GOOGLE_API_KEY` | Gemini LLM + embeddings | [aistudio.google.com](https://aistudio.google.com) |
| `TAVILY_API_KEY` | Web search tool | [tavily.com](https://tavily.com) |

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/Ishaan30/rag_agent.git
cd rag_agent
```

**2. Create and activate a virtual environment**
```bash
python -m venv myenv

# Windows
myenv\Scripts\activate

# Mac/Linux
source myenv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r backend/requirements.txt
```

**4. Set up environment variables**
```bash
cp .env.example .env
# Open .env and fill in your real API keys
```

## How to Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open your browser at `http://localhost:8000`

## Example Requests

**Upload a document:**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@your_document.pdf"
```

**Send a chat message:**
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "Summarise the document"}'
```

**Ask a weather question (triggers weather tool):**
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "What is the weather in London?"}'
```

**Ask a web search question (triggers search tool):**
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "What are the latest AI news?"}'
```

**Clear conversation:**
```bash
curl -X DELETE http://localhost:8000/api/chat/abc123
```

**Check document status:**
```bash
curl http://localhost:8000/api/documents/status
```

## Design Decisions & Trade-offs

- **FAISS over Chroma** — FAISS is in-memory, zero setup, no persistence config needed. Trade-off: vector store resets on server restart. Production would use Pinecone or Chroma with disk persistence.
- **Gemini REST embeddings** — Used `google-generativeai` directly instead of `langchain-google-genai` to bypass gRPC which caused timeout issues on restricted networks. Pure HTTPS calls are more firewall-friendly.
- **In-memory session history** — Conversation history lives in a Python dict keyed by session ID. Simple and fast for demo purposes. Trade-off: history is lost on restart. Production would use Redis.
- **Single active document** — Only one document can be active at a time. Uploading a new file replaces the previous vector store. Simple but not multi-user friendly.
- **Single-file frontend** — The entire UI is one `index.html` with no build step, making it trivial to serve via FastAPI's `FileResponse`.
- **Open-Meteo for weather** — No API key required, completely free, no rate limits for development use.