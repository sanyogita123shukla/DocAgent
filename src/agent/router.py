import magic

# Mapping of MIME types to supported document types.
# Used for routing and validation only — extraction is handled in graph.py.
SUPPORTED_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
    "application/vnd.ms-excel": "excel",
    "text/csv": "csv",
}

def route_file(file_path: str) -> dict:
    """
    Deterministic routing. Runs BEFORE the LLM sees anything.
    Uses libmagic to determine the file type robustly.
    """
    mime = magic.from_file(file_path, mime=True)
    doc_type = SUPPORTED_TYPES.get(mime)
    if not doc_type:
        raise ValueError(f"Unsupported file type: {mime}")
    return {"file_type": mime, "doc_type": doc_type}
