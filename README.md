# Voilet: Intelligent Document Analysis & Chat

**Voilet** is a full-stack AI application that transforms static PDF documents into interactive knowledge bases. 

Unlike standard "Chat with PDF" tools, Voilet **proactively analyzes** documents upon upload, extracting structured data from tables, generating summaries, and suggesting key questions *before* you even type a prompt.

Built with **FastAPI**, **React**, and **LangChain**, it leverages state-of-the-art Large Language Models (Gemini Pro & GPT-4) to provide accurate, context-aware answers from multiple documents simultaneously.

---

## 🚀 Key Features

* **📂 Multi-Document RAG:** Upload and chat with entire folders of PDFs. The system synthesizes answers across multiple documents.
* **🧠 Proactive Insights:** Automatically generates a concise summary, key concepts, and suggested follow-up questions immediately after upload.
* **📊 Table Talk (Smart Extraction):** A specialized processing pipeline using `tabula-py` to detect, extract, and query structured data trapped in PDF tables.
* **🔌 Model Agnostic:** "Hot-swap" support for different LLM providers. Choose **Google Gemini** (cost-effective) or **OpenAI GPT** (high precision) for each collection.
* **🔐 Secure Authentication:** Full user management system with hashed passwords (bcrypt), JWT session tokens, and isolated document collections per user.
* **⚡ Hybrid Search:** Uses FAISS vector search combined with metadata filtering for high-precision retrieval.

---

## 🛠️ Tech Stack

### Backend (The Brain)
| Component | Technology |
| :--- | :--- |
| **Framework** | Python, FastAPI |
| **AI Orchestration** | LangChain |
| **Vector Database** | FAISS (Facebook AI Similarity Search) |
| **LLMs** | Google Gemini Pro, OpenAI GPT-3.5/4 |
| **Embeddings** | HuggingFace (`all-MiniLM-L6-v2`) |
| **PDF Processing** | PyMuPDF (Fitz), Tabula-py (Java-based) |
| **Database** | SQLite (via SQLAlchemy) |
| **Auth** | OAuth2 with JWT & Bcrypt |

### Frontend (The Face)
| Component | Technology |
| :--- | :--- |
| **Library** | React.js |
| **Styling** | Tailwind CSS |
| **State Mgmt** | React Context API |
| **HTTP Client** | Axios |

---

## 🏗️ Architecture

The application follows a modular **Service-Oriented Architecture**:

1.  **Ingestion Layer:** PDFs are parsed; text is cleaned; tables are extracted via OCR-like heuristics.
2.  **Embedding Layer:** Text chunks are converted into dense vectors using sentence-transformers.
3.  **Storage Layer:** Vectors are stored in a local FAISS index; user metadata is stored in SQLite.
4.  **Retrieval Layer:** When a user asks a question, the system performs a semantic search to find the top 4 most relevant text chunks.
5.  **Generation Layer:** The chunks + user question are sent to the selected LLM to generate a grounded response.

----------

## ⚙️ Installation & Setup

### Prerequisites
* **Python 3.9+**
* **Node.js & npm**
* **Java 8+** (Required for `tabula-py` to extract tables—ensure it is in your system PATH)

### 1. Clone the Repository
```bash
git clone [https://github.com/Nikhil-Porwal/voilet.git](https://github.com/yourusername/voilet.git)
cd voilet

---

## 🧭 Quick start — Run frontend + backend locally

These steps will get the app running on your machine (developer flow):

### 1) Start the backend (FastAPI)

```powershell
# From repo root (AskVoilet)
python -m venv .venv        # optional but recommended
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Start Uvicorn / FastAPI on port 8000
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --app-dir "${PWD}"
```

Notes:
- The backend reads `.env` (there's a sample at `app/.env` and one at the repo root). The server requires `SECRET_KEY` in `.env` — it will raise an error if missing.
- Add `OPENAI_API_KEY` or `GEMINI_API_KEY` to `.env` if you plan to use LLM features.

### 2) Start the frontend (Vite + React)

```powershell
cd frontend
npm install    # only first time
npm run dev
```

By default the frontend expects the backend API at:
 - http://localhost:8000/api

### 3) Open the app in your browser

 - Frontend UI: http://localhost:5173
 - Backend docs (OpenAPI): http://127.0.0.1:8000/docs

Test credentials (dev):
- username: devtester
- password: pass1234

### Troubleshooting
- ERR_CONNECTION_REFUSED on :8000 → ensure uvicorn is running and listening on 127.0.0.1:8000.
- Server startup error about SECRET_KEY → create a `.env` at project root with SECRET_KEY and restart.
- Frontend can't reach backend → verify `API_BASE_URL` in `frontend/src/App.jsx` or switch port accordingly.

If you'd like, I can update the frontend so `API_BASE_URL` is read from an environment variable instead of a hard-coded string.
