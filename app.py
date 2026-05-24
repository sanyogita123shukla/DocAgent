import os
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from st_copy import copy_button

from src.agent.graph import build_graph
from src.utils.history import get_sessions, create_session, update_session_title
from src.utils.doc_stats import compute_stats

# Load environment variables
load_dotenv()

# Initialize the Streamlit app
st.set_page_config(page_title="DocAgent Pro", page_icon="📄", layout="wide")

# Inject Premium UI Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* Beige/Cream Premium background */
.stApp {
    background: linear-gradient(135deg, #fdfbf7 0%, #f4f1ea 100%);
    color: #4a4a4a !important;
    font-family: 'Inter', sans-serif;
}
/* Title Gradient - Warm tones */
h1 {
    font-family: 'Inter', sans-serif;
    color: #8c7b68 !important;
    font-weight: 800;
}
/* Chat text colors */
[data-testid="stChatMessage"] p, [data-testid="stMarkdownContainer"] p {
    color: #4a4a4a !important;
}
/* Better chat container */
[data-testid="stChatMessage"] {
    background: #ffffff !important;
    border: 1px solid #e8e4d9 !important;
    border-radius: 12px;
    padding: 1.25rem !important;
    margin-bottom: 1rem;
    box-shadow: 0 4px 15px -3px rgba(115, 107, 94, 0.08);
}
/* Main Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #faf8f5 !important;
    border-right: 1px solid #e8e4d9 !important;
}
/* Smooth hover effects */
button {
    transition: all 0.2s ease-in-out !important;
}
/* Stats card styling */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e8e4d9;
    border-radius: 10px;
    padding: 0.75rem 1rem;
    box-shadow: 0 2px 8px rgba(115, 107, 94, 0.06);
}
[data-testid="stMetric"] label {
    color: #8c7b68 !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #4a4a4a !important;
    font-weight: 800 !important;
}
/* Stats banner container */
.stats-banner {
    background: linear-gradient(135deg, #fffdf8 0%, #f9f5ee 100%);
    border: 1px solid #e8e4d9;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 12px rgba(115, 107, 94, 0.07);
}
/* Content preview box */
.doc-preview {
    background: #faf8f5;
    border: 1px solid #e8e4d9;
    border-radius: 8px;
    padding: 1rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #6b6b6b;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.title("📄 DocAgent Pro")
st.markdown("*Advanced Persistent Memory & Document Analysis Engine*")

# Initialize graph if not exists
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

# Initialize per-session stats storage
if "session_stats" not in st.session_state:
    st.session_state.session_stats = {}

# Session / Chat History Management
sessions = get_sessions()

with st.sidebar:
    st.header("💬 Chat History")
    
    if st.button("✨ New Conversation", use_container_width=True):
        new_id = create_session("New Chat")
        st.session_state.current_session_id = new_id
        st.rerun()
        
    st.divider()
    
    # Defaults to new chat if no sessions exist
    if not sessions:
        new_id = create_session("New Chat")
        st.session_state.current_session_id = new_id
        st.rerun()
        
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = sessions[0]["id"]
        
    for s in sessions:
        btn_label = f"📝 {s['title']}"
        is_active = (s["id"] == st.session_state.current_session_id)
        if st.button(btn_label, key=s["id"], type="primary" if is_active else "secondary", use_container_width=True):
            st.session_state.current_session_id = s["id"]
            st.rerun()

thread_config = {"configurable": {"thread_id": st.session_state.current_session_id}}
current_session_id = st.session_state.current_session_id

# Fetch messages natively from LangGraph memory
state_obj = st.session_state.graph.get_state(thread_config)
messages = state_obj.values.get("messages", [])

# =====================================================================
# PERSISTENT STATS BANNER
# Rendered on EVERY rerun from session_state — never disappears
# =====================================================================
def render_stats_banner(stats: dict, file_path: str):
    """Render the persistent document stats banner from cached stats dict."""
    fname = os.path.basename(file_path)
    intent = stats.get("intent", "")
    intent_color = {
        "Form / Questionnaire": "🟣",
        "Report / Briefing": "🔵",
        "Dataset / Spreadsheet": "🟢",
        "Contract / Agreement": "🔴",
    }.get(intent, "⚪")

    st.markdown(
        f'<div class="stats-banner">'
        f'<span style="font-size:0.8rem;font-weight:700;color:#8c7b68;text-transform:uppercase;letter-spacing:0.05em">Document Analysis</span><br>'
        f'<span style="font-size:1.05rem;font-weight:700;color:#4a4a4a">📄 {fname}</span>'
        f'&nbsp;&nbsp;<span style="background:#f0ece3;border:1px solid #ddd;border-radius:20px;padding:2px 10px;font-size:0.78rem;color:#7a6a58">'
        f'{intent_color} {intent}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    if stats["file_type"] == "PDF":
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Pages", stats["pages"])
        c2.metric("Words", f"{stats['words']:,}")
        c3.metric("Lines", f"{stats['lines']:,}")
        c4.metric("Tables", stats.get("tables", 0))
        c5.metric("Images", stats.get("images", 0))
        c6.metric("Questions", stats.get("questions_detected", 0))

        # Metadata strip
        meta_parts = []
        if stats.get("meta_author") and stats["meta_author"] != "Unknown":
            meta_parts.append(f"**Author:** {stats['meta_author']}")
        if stats.get("meta_title") and stats["meta_title"] != "Untitled":
            meta_parts.append(f"**Title:** {stats['meta_title']}")
        if stats.get("meta_created") and stats["meta_created"] != "Unknown":
            meta_parts.append(f"**Created:** {stats['meta_created']}")
        if stats.get("hyperlinks", 0) > 0:
            meta_parts.append(f"**Hyperlinks:** {stats['hyperlinks']}")
        if meta_parts:
            st.caption("  ·  ".join(meta_parts))

    elif stats["file_type"] in ("Excel", "CSV"):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Sheets", stats["sheets"])
        c2.metric("Total Rows", f"{stats['rows']:,}")
        c3.metric("Filled Cells", f"{stats['cells_filled']:,}")
        c4.metric("Fill Rate", f"{stats.get('fill_rate', 0)}%")
        dup = stats.get("duplicate_rows", 0)
        c5.metric("Duplicate Rows", dup, delta=f"⚠️ {dup}" if dup else None, delta_color="inverse")

        # Column schema per sheet
        col_types = stats.get("column_types", {})
        if col_types:
            with st.expander("🧬 Column Schema", expanded=False):
                for sheet, cols in col_types.items():
                    st.markdown(f"**Sheet: {sheet}**")
                    rows_md = "\n".join(
                        f"- `{col}`: **{typ}**" for col, typ in cols.items()
                    )
                    st.markdown(rows_md)

    # Content preview expander
    with st.expander("📖 Content Preview", expanded=False):
        try:
            if stats["file_type"] == "PDF":
                import fitz as _fitz
                doc = _fitz.open(file_path)
                preview_text = "\n".join(p.get_text(sort=True).strip() for p in doc)[:1500]
            else:
                preview_text = f"Excel file — use the Column Schema expander above for structure details."
            st.markdown(f'<div class="doc-preview">{preview_text}</div>', unsafe_allow_html=True)
        except Exception:
            st.caption("Preview not available.")


# If we have cached stats for this session, render the banner now (persistent)
cached = st.session_state.session_stats.get(current_session_id)
if cached:
    render_stats_banner(cached["stats"], cached["file_path"])
    st.markdown("---")

# =====================================================================
# CHAT MESSAGES
# =====================================================================
for msg in messages:
    if not isinstance(msg, (HumanMessage, AIMessage)):
        continue
    if not msg.content:
        continue
    # Skip internal document context messages injected by router
    if isinstance(msg, HumanMessage) and isinstance(msg.content, str) and msg.content.startswith("[DOCUMENT CONTEXT]"):
        continue
        
    with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
        if isinstance(msg.content, list):
            text_parts = [block.get("text", "") for block in msg.content if isinstance(block, dict) and block.get("type") == "text"]
            display_content = "\n".join(text_parts)
        else:
            display_content = str(msg.content)
            
        st.markdown(display_content)
        if isinstance(msg, AIMessage):
            st.markdown("<br>", unsafe_allow_html=True)
            copy_button(display_content)

# =====================================================================
# CHAT INPUT
# =====================================================================
prompt_obj = st.chat_input("Ask a question or upload a document...", accept_file=True, file_type=["pdf", "xlsx", "csv", "xls"])

if prompt_obj:
    if isinstance(prompt_obj, str):
        prompt_text = prompt_obj
        uploaded_files = []
    else:
        prompt_text = getattr(prompt_obj, "text", "")
        if not prompt_text and hasattr(prompt_obj, "get"):
            prompt_text = prompt_obj.get("text", "")
            
        uploaded_files = getattr(prompt_obj, "files", [])
        if not uploaded_files and hasattr(prompt_obj, "get"):
            uploaded_files = prompt_obj.get("files", [])
    
    if not prompt_text and not uploaded_files:
        st.stop()
        
    # Show user message immediately
    with st.chat_message("user"):
        st.markdown(prompt_text)
        for f in uploaded_files:
            st.caption(f"📎 Attached: {f.name}")
            
    # Save file to temp dir
    file_path = None
    if uploaded_files:
        _temp_dir = "temp_uploads"
        os.makedirs(_temp_dir, exist_ok=True)
        file_path = os.path.join(_temp_dir, uploaded_files[0].name)
        with open(file_path, "wb") as f:
            f.write(uploaded_files[0].getbuffer())
        
        # Compute stats and CACHE them in session_state so they persist across reruns
        stats = compute_stats(file_path)
        if stats:
            st.session_state.session_stats[current_session_id] = {
                "stats": stats,
                "file_path": file_path,
            }
    else:
        # Fallback: use prior file from LangGraph state
        file_path = state_obj.values.get("file_path", None)

    # Invoke LLM
    with st.chat_message("assistant"):
        with st.spinner("Thinking & Analyzing..."):
            initial_state = {
                "messages": [HumanMessage(content=prompt_text)]
            }
            if file_path:
                initial_state["file_path"] = file_path
                
            final_state = st.session_state.graph.invoke(initial_state, config=thread_config)
            
            final_message_content = final_state["messages"][-1].content
            if isinstance(final_message_content, list):
                text_parts = [block.get("text", "") for block in final_message_content if block.get("type") == "text"]
                final_message_content = "\n".join(text_parts)
                
            st.markdown(final_message_content)
            st.markdown("<br>", unsafe_allow_html=True)
            copy_button(final_message_content)
            
    # Auto-update session title on first message
    if len(messages) == 0 and prompt_text:
        title_snippet = prompt_text[:20] + "..." if len(prompt_text) > 20 else prompt_text
        if uploaded_files:
            title_snippet = f"{uploaded_files[0].name}"
        update_session_title(current_session_id, title_snippet)
        st.rerun()
