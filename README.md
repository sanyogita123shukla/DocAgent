# DocAgent Pro

**AI-Powered Document Intelligence Engine**

> An enterprise-grade AI agent that ingests PDFs and Excel/CSV files, produces structured summaries, detects forms & questionnaires, and supports persistent multi-turn conversations all while making **exactly 1 LLM API call per query**.

**Stack:** Python 3.11+ · Streamlit · LangGraph · Google Gemini Flash · PyMuPDF · openpyxl

---

## Table of Contents

- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [How It Works](#-how-it-works)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Skills Layer](#-skills-layer)
- [Context Engineering](#-context-engineering)
- [UI Features](#-ui-features)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Roadmap](#-roadmap)

---

## ✨ Key Features

**Smart Document Analysis** — Upload any PDF or Excel file and receive a structured, multi-section analysis: classification, executive summary, key details table, and actionable insights.

**Form & Questionnaire Detection** — Two-pass detection engine. Pass 1: fast regex heuristics (8 patterns) for obvious forms. Pass 2: LLM fallback for ambiguous cases. Extracts questions, checkboxes, and fill-in fields automatically.

**Data Quality Scoring (Excel)** — Automatic column-type inference (`int`, `float`, `date`, `text`, `mixed`), fill-rate calculation, duplicate-row detection, and empty-column flagging.

**Persistent Multi-Turn Chat** — Ask follow-up questions about uploaded documents without re-uploading. Full conversation memory via LangGraph's `MemorySaver` checkpointer, scoped per thread.

**Single API Call Guarantee** — All document parsing happens locally. The LLM is invoked exactly once per interaction. No ReAct tool loops, no retry chains. Cost reduction of 80%+ versus tool-loop agents.

**Zero-API Local Extraction** — Documents are never sent to external APIs for parsing. `PyMuPDF`, `pdfplumber`, and `openpyxl` handle all extraction locally preserving privacy and eliminating parsing latency.

**Real-Time Stats Dashboard** — Instant document statistics banner (pages, words, tables, images, column schemas, fill rate) computed locally in milliseconds and rendered persistently across chat reruns.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- A Google Gemini API key get one free at [Google AI Studio](https://aistudio.google.com/apikey)
- (Optional) [uv](https://docs.astral.sh/uv/) for faster dependency management

### One-Command Setup

**macOS / Linux:**

```bash
chmod +x start_app.sh
./start_app.sh
```

**Windows:**

```powershell
start_app.bat
```

The script creates a virtual environment, installs all dependencies, validates the API key, and launches the app.

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/your-username/DocAgent.git
cd DocAgent

# Install dependencies with uv (recommended 10x faster than pip)
uv sync

# Configure your API key
cp .env.example .env
# Edit .env and set GOOGLE_API_KEY=your_key_here

# Launch
uv run streamlit run app.py
```

**Using pip instead of uv:**

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e .
streamlit run app.py
```

The app opens at **http://localhost:8501**.

---

## 🏗️ Architecture

DocAgent Pro uses a **Deterministic Single-Pass Architecture**. This is a deliberate design choice that separates deterministic file parsing from LLM reasoning to minimize cost, latency, and hallucinations.

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER (prompt + file)                            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  STREAMLIT UI  (app.py)                                                  │
│  • Chat interface with file upload (.pdf, .xlsx, .csv, .xls)             │
│  • Session management (sidebar, auto-titling)                            │
│  • Instant stats banner via compute_stats() ZERO API calls             │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ file saved to temp_uploads/
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ROUTER NODE  (src/agent/graph.py :: router_node)                        │
│                                                                          │
│  1. MIME detection via python-magic (libmagic) deterministic, O(1)     │
│  2. Local extraction:                                                    │
│     • PDF  → _extract_pdf()  using PyMuPDF + pdfplumber                  │
│     • Excel → _extract_excel() using openpyxl                            │
│  3. Injects [DOCUMENT CONTEXT] HumanMessage into state                   │
│  4. Follow-up guard: if context already exists, SKIPS re-extraction      │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  AGENT NODE  (src/agent/graph.py :: agent_node)                          │
│                                                                          │
│  • Prepends SYSTEM_PROMPT (structured output format)                     │
│  • Invokes LLM exactly ONCE: llm.invoke(messages)                        │
│  • Returns structured analysis (7 sections)                              │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  LANGGRAPH MEMORYSAVER                                                   │
│  • Per-thread checkpointing (thread_id = session_id)                     │
│  • Full conversation history preserved across reruns                     │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
                        Response rendered in UI
```

### Why This Design?

| Decision | Rationale |
|---|---|
| **Pre-LLM local extraction** | Documents are parsed by PyMuPDF / openpyxl before the LLM sees them. The LLM never touches raw binary only clean, structured text. This eliminates an entire class of parsing hallucinations. |
| **Single LLM call** | No ReAct tool loops. The router handles all deterministic work; the agent handles reasoning. This guarantees exactly 1 API call per interaction regardless of document complexity. |
| **Context injection with dedup guard** | Extracted content is injected as a `[DOCUMENT CONTEXT]` message. On follow-up questions, a state guard scans existing history and **skips re-extraction** preventing duplicate tokens and context bloat. |
| **MIME-type routing** | `python-magic` (libmagic) detects file types deterministically. Zero LLM tokens spent on file-type guessing a common failure mode in naive agent implementations. |
| **Separated stats pipeline** | `compute_stats()` runs independently of the agent graph, producing instant UI feedback while the LLM processes in the background. |

---

## 🧠 How It Works

### Step 1 — File Upload & Local Stats (Zero API Calls)

When a user uploads a file, `compute_stats()` in `src/utils/doc_stats.py` runs immediately:

**For PDFs:**
- Page count, word count, line count, character count
- Table count (pdfplumber), image count, hyperlink count
- Metadata: author, title, creator, creation date (parsed from PDF `D:YYYYMMDD` format)
- Form/question detection via 8 regex patterns (numbered questions, checkboxes, fill-in blanks, Yes/No fields)
- Intent classification via keyword heuristics

**For Excel/CSV:**
- Sheet count, row count, cell count
- Column-type inference per column (`int`, `float`, `date`, `text`, `mixed`)
- Fill rate (% of non-empty cells)
- Duplicate row detection (stringified row comparison)
- Empty column flagging

These stats render instantly in the **Stats Banner** before the LLM even starts.

### Step 2 — Deterministic Routing & Extraction

The `router_node` in the LangGraph `StateGraph`:

1. Checks if `file_path` exists on state. If not → pure chat flow, pass through.
2. Scans thread history for an existing `[DOCUMENT CONTEXT]` message. If found → skip extraction (multi-turn optimization).
3. Detects MIME type via `python-magic`.
4. Calls `_extract_pdf()` or `_extract_excel()` as appropriate.
5. Wraps extracted content in a `HumanMessage` with `[DOCUMENT CONTEXT]` prefix and returns it.

### Step 3 — LLM Reasoning (Single Call)

The `agent_node` prepends a structured `SYSTEM_PROMPT` and invokes the LLM once. The prompt enforces this output structure:

1. **Document Classification** — one-line classification (Form / Report / Dataset / Contract / General)
2. **Executive Summary** — 2–4 sentences on purpose, audience, and scope
3. **Key Details** — named entities and facts as a Markdown table
4. **Content Breakdown** — adaptive format: bullets for reports, checkboxes for forms, schema descriptions for datasets, clause extraction for contracts
5. **Data Quality & Observations** — Excel only: completeness %, suspicious patterns, quality score /10
6. **Key Insights** — 3–5 actionable bullet points
7. **Suggested Follow-up Questions** — 3 context-specific questions to guide the user

### Step 4 — Persistent Memory

LangGraph's `MemorySaver` checkpointer stores state per `thread_id` (mapped to session ID). Users can:
- Ask follow-up questions without re-uploading
- Reference previous answers ("What's the difference between the top two items you listed?")
- Switch between sessions via the sidebar

---

## 🛠️ Tech Stack

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| **Agent Framework** | LangGraph | 0.2+ | Graph-based orchestration with first-class checkpointing, conditional edges, and state management. Superior to raw LangChain for agentic workflows. |
| **LLM** | Google Gemini Flash | latest | 1M token context window, free tier available, fast inference. Handles entire documents without chunking/RAG overhead. |
| **PDF Parsing** | PyMuPDF (fitz) | 1.25+ | High-speed text extraction. `sort=True` fixes multi-column reading order (left→right, top→bottom). |
| **PDF Tables** | pdfplumber | 0.11+ | Precision table extraction when structure detection identifies tabular content. |
| **Excel Parsing** | openpyxl | 3.1+ | Handles merged cells, multiple sheets, formula resolution (`data_only=True`), and deep cell introspection. |
| **Data Analysis** | pandas | 2.2+ | Summary statistics and analytics for spreadsheet data. |
| **File Detection** | python-magic | 0.4+ | Deterministic MIME-type detection via libmagic. No heuristics, no guessing. |
| **Frontend** | Streamlit | 1.40+ | Chat UI with file upload, reactive session state, and `st.chat_input(accept_file=True)`. |
| **Validation** | Pydantic | 2.7+ | Structured I/O schemas for skills and LLM structured output. |
| **Dependency Mgmt** | uv | latest | 10–100× faster than pip. Single `pyproject.toml` manifest. |

---

## 📁 Project Structure

```
DocAgent/
│
├── app.py                        # Streamlit entry point
│                                 #   - Chat loop, file handling, stats banner
│                                 #   - Session management via sidebar
│                                 #   - Premium UI with custom CSS (Inter font, warm palette)
│
├── pyproject.toml                # Project metadata & dependency manifest
├── .env.example                  # API key template (GOOGLE_API_KEY)
├── start_app.sh                  # One-command setup script (macOS/Linux)
├── start_app.bat                 # One-command setup script (Windows)
│
├── src/
│   ├── __init__.py
│   │
│   ├── agent/                    # ── Agent Orchestration Layer ──
│   │   ├── graph.py              # LangGraph StateGraph definition
│   │   │                         #   - router_node: MIME routing + local extraction
│   │   │                         #   - agent_node: single LLM reasoning call
│   │   │                         #   - _extract_pdf(): PyMuPDF + pdfplumber
│   │   │                         #   - _extract_excel(): openpyxl
│   │   ├── router.py             # MIME-type routing via python-magic (libmagic)
│   │   ├── prompts.py            # SYSTEM_PROMPT structured 7-section output format
│   │   └── state.py              # AgentState TypedDict (messages, file_path, file_type)
│   │
│   ├── skills/                   # ── Reusable Skill Abstractions ──
│   │   ├── base.py               # AbstractSkill ABC + SkillInput base schema
│   │   ├── pdf_reader.py         # PDFReaderSkill: per-page text + table extraction
│   │   ├── excel_reader.py       # ExcelReaderSkill: multi-sheet, merged cells
│   │   ├── form_detector.py      # FormDetectorSkill: regex heuristics + LLM fallback
│   │   └── summarizer.py         # SummarizationSkill: LLM chain for summaries
│   │
│   └── utils/                    # ── Utilities ──
│       ├── doc_stats.py          # Zero-API document statistics engine
│       │                         #   - compute_pdf_stats(): pages, words, tables, metadata
│       │                         #   - compute_excel_stats(): column types, fill rate, dupes
│       │                         #   - _classify_intent(): keyword-based heuristic
│       └── history.py            # Session registry (data/sessions.json)
│
├── data/
│   └── sessions.json             # Chat session registry (auto-created at runtime)
│
└── temp_uploads/                 # Temporary file storage (auto-created at runtime)
```

---

## 🧩 Skills Layer

Every document capability is implemented as an `AbstractSkill` subclass a plug-and-play abstraction inspired by production AI agent systems.

### The Abstraction

Each skill defines:
- `name` — identifier for tool registration
- `description` — the LLM reads this to understand tool capabilities
- `args_schema` — a Pydantic model that validates inputs at the boundary
- `_execute(**kwargs) → dict` — core logic, returns structured JSON

The base class wraps execution with JSON serialization and error handling:

```python
# src/skills/base.py
class AbstractSkill(BaseTool, ABC):

    @abstractmethod
    def _execute(self, **kwargs) -> dict[str, Any]:
        """Core logic. Returns structured JSON."""
        ...

    def _run(self, **kwargs) -> str:
        """LangGraph calls this. Wraps _execute with error handling."""
        try:
            result = self._execute(**kwargs)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "skill": self.name})
```

### Implemented Skills

**PDFReaderSkill** (`src/skills/pdf_reader.py`)
Extracts per-page text via PyMuPDF. Optionally extracts tables via pdfplumber when `extract_tables=True`.

**ExcelReaderSkill** (`src/skills/excel_reader.py`)
Loads workbooks with `openpyxl.load_workbook(data_only=True)`. Provides sheet-by-sheet headers, data rows, shape metadata, and merged cell resolution.

**FormDetectorSkill** (`src/skills/form_detector.py`)
Two-pass form detection:
- **Pass 1 (Free):** 8 regex patterns scan for numbered questions, `Q1:` syntax, checkboxes `[ ]`, fill-in blanks `___`, and Yes/No toggles. If ≥3 patterns match → returns `is_form: True, confidence: high`. If 0 → `is_form: False`.
- **Pass 2 (LLM Fallback):** For ambiguous cases (1–2 matches), sends content to the LLM with `with_structured_output(ExtractedForm)` for Pydantic-validated classification.

**SummarizationSkill** (`src/skills/summarizer.py`)
Builds a structured prompt and invokes the LLM for a detailed, formatted summary.

---

## 🔬 Context Engineering

### PDF Intelligence

- **Reading Order Fix:** `page.get_text(sort=True)` reads left→right, top→bottom. This eliminates the merged-text hallucinations that plague naive PDF parsers on academic papers and multi-column layouts.
- **Metadata Extraction:** Title, author, creator, creation date with date parsing from the PDF `D:YYYYMMDDHHMMSS` format into human-readable form.
- **Structure Detection:** Table count via pdfplumber, embedded image count via `page.get_images()`, hyperlink count via `page.get_links()`.
- **Form Heuristics:** 8 regex patterns in `QUESTION_PATTERNS`:

```python
QUESTION_PATTERNS = [
    r'\d+[\.\\)]\s+.+\?',                    # "1. What is...?"
    r'(?:Q|Question)\s*\d*[:\.\)]\s*.+',      # "Q1: ..."
    r'^[A-Z][\.\\)]\s+.+\?',                  # "A. What...?"
    r'_{3,}',                                  # "___________" (fill-in blanks)
    r'\[\s*\]',                                # "[ ]" checkboxes
    r'\[X\]',                                  # "[X]" checked boxes
    r'(?:Yes|No)\s*/\s*(?:Yes|No)',            # "Yes / No"
    r'(?:Please|Kindly)\s+(?:describe|explain|list|provide)',
]
```

### Excel Intelligence

- **Column Type Inference:** For each column, tallies occurrences of `int`, `float`, `date`, `text`. A type is declared dominant only if it accounts for ≥60% of non-null samples; otherwise the column is tagged `mixed`.
- **Fill Rate:** `(non_empty_cells / total_cells) × 100`, computed across all sheets.
- **Duplicate Detection:** Rows are stringified and compared via a set. Only rows with at least one non-null value are considered.
- **Token Safety:** Only the column schema + first 30 data rows are injected into LLM context. Larger datasets get a truncation note.

### Intent Classification (Zero-API)

A keyword-scoring heuristic classifies documents before the LLM runs:

| Category | Keywords | Bonus |
|---|---|---|
| Form / Questionnaire | questionnaire, form, registration, survey, consent | +2 if regex detects ≥3 questions |
| Report / Briefing | summary, report, briefing, analysis, findings, conclusion | — |
| Contract / Agreement | agreement, contract, terms, clause, whereas, obligations | — |
| Dataset / Spreadsheet | Auto-classified for all Excel files | — |

The highest-scoring category wins. If all scores are 0, the document is classified as "General Document".

---

## 🖥️ UI Features

- **Premium Design** — warm beige/cream palette, Inter typography (Google Fonts), glassmorphism-inspired cards, smooth hover transitions
- **File Upload** — `st.chat_input(accept_file=True, file_type=["pdf", "xlsx", "csv", "xls"])` for combined text + file input
- **Persistent Stats Banner** — document metrics (pages, words, tables, fill rate, column schemas) computed instantly and cached in `st.session_state.session_stats` survives Streamlit reruns
- **Session Management** — sidebar with chat history list, "New Conversation" button, active session highlighting, auto-titling based on first message or uploaded filename
- **Copy Button** — one-click copy of AI responses via `st-copy`
- **Content Preview** — expandable raw text preview for uploaded documents
- **Intent Badge** — color-coded document classification chip in the stats banner

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key get one at [AI Studio](https://aistudio.google.com/apikey) |

### Switching the LLM Provider

The LLM is initialized in `src/agent/graph.py`:

```python
# Default: Google Gemini Flash
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
```

To switch to OpenAI:

```python
# Requires: pip install langchain-openai
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini")
```

Pass the custom LLM to `build_graph(llm=your_llm)`.

---

## 🧪 Testing

### Run Tests

```bash
# Unit tests
uv run pytest tests/ -v

# Launch for manual testing
uv run streamlit run app.py
```

### Verification Matrix

| Scenario | What to Verify |
|---|---|
| Multi-page PDF upload | Summary accuracy, metadata extraction, section structure |
| Excel with merged cells | Multi-sheet handling, column-type inference, fill rate, duplicate detection |
| Form/questionnaire PDF | Question extraction, checkbox detection, `is_form: True` classification |
| Follow-up questions (Turn 2+) | Context retention, no re-extraction, coherent multi-turn answers |
| Unsupported file type (.mp3) | Graceful `ValueError` with descriptive message |
| Empty Excel sheet | No crash, empty-column flagging, fill rate = 0% |
| Large PDF (100+ pages) | Token truncation working, response within timeout |

---

## 🔮 Roadmap

- **OCR Pipeline** — pytesseract or Google Vision for scanned/image-based PDFs
- **Persistent Storage** — replace `data/sessions.json` with SQLite or Postgres for concurrency
- **RAG Integration** — embeddings-based retrieval for documents exceeding the context window
- **Streaming Responses** — token-by-token streaming for perceived latency reduction
- **Additional Skills** — table extractor, named-entity extractor, sensitive-data redactor
- **Authentication** — role-based access for multi-user deployments
- **File Caching** — hash-based deduplication to skip re-extraction of identical files across sessions

---

## License

This project is open-source under the [MIT License](LICENSE).

---

*Built with LangGraph, Streamlit, and Google Gemini.*
