"""
AI Assisted Scope Management Tool — Streamlit UI (layout only).
"""

import base64
import json
import os
import re
from pathlib import Path

import fitz
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

SPEC_PARSE_SYSTEM_PROMPT = (
    "You are an expert construction estimator working for a general "
    "contractor. You are reading a specification division and extracting "
    "scope items for a trade subcontractor scope document."
)

SPEC_PARSE_MODEL = "claude-sonnet-4-6"

INDEX_DRAWINGS_SYSTEM_PROMPT = (
    "You are an expert construction estimator reviewing project "
    "drawings. Extract structured information from each drawing sheet."
)

INDEX_DRAWINGS_USER_PROMPT = (
    "For each drawing sheet in this batch, identify and return in "
    "JSON format:\n"
    "- sheet_number\n"
    "- discipline\n"
    "- drawing_title\n"
    "- trades_referenced\n"
    "- scope_notes (key scope items visible on this sheet)\n"
    "- cross_references (any other documents or drawings referenced)\n"
    "Return a JSON array with one object per sheet."
)

DRAWING_INDEX_PATH = Path(__file__).resolve().parent / "drawing_index.json"

DRAWING_PAGE_RENDER_DPI = 150
INDEX_BATCH_SIZE = 3


def load_env_from_dotenv() -> str | None:
    """Load `.env` and return `ANTHROPIC_API_KEY` from the environment."""
    load_dotenv()
    return os.environ.get("ANTHROPIC_API_KEY")


ANTHROPIC_API_KEY = load_env_from_dotenv()


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF using PyMuPDF, page by page."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts)
    finally:
        doc.close()


def _page_to_png_highres(page: fitz.Page) -> bytes:
    """Render a PDF page to a high-resolution PNG using PyMuPDF."""
    zoom = DRAWING_PAGE_RENDER_DPI / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    w, h = pix.width, pix.height
    if w > 8000 or h > 8000:
        scale = min(7500 / w, 7500 / h)
        mat = fitz.Matrix(zoom * scale, zoom * scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def _parse_json_array_from_model_text(text: str) -> list:
    """Parse a JSON array from Claude output, tolerating markdown fences."""
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise
        data = json.loads(raw[start : end + 1])
    if not isinstance(data, list):
        raise ValueError("Model response was not a JSON array")
    return data


def _build_index_batch_content(png_pages: list[bytes]) -> list[dict]:
    """Anthropic Messages API content blocks: ordered images then the user prompt."""
    blocks: list[dict] = []
    for png in png_pages:
        b64 = base64.standard_b64encode(png).decode("utf-8")
        blocks.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64,
                },
            }
        )
    blocks.append({"type": "text", "text": INDEX_DRAWINGS_USER_PROMPT})
    return blocks


def index_drawings(pdf_bytes: bytes) -> None:
    """
    Render each page as a high-res image, index in batches of three via Claude,
    merge into `drawing_index.json`, and show a summary in the main panel.
    """
    if not ANTHROPIC_API_KEY:
        st.error(
            "ANTHROPIC_API_KEY is not set. Add it to your `.env` file in the "
            "project folder."
        )
        return

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        n_pages = doc.page_count
        if n_pages == 0:
            st.warning("The PDF has no pages to index.")
            return

        with st.spinner("Rendering drawing pages at high resolution…"):
            page_pngs: list[bytes] = []
            for page in doc:
                page_pngs.append(_page_to_png_highres(page))
    finally:
        doc.close()

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    combined: list[dict] = []
    n_batches = (n_pages + INDEX_BATCH_SIZE - 1) // INDEX_BATCH_SIZE
    progress_slot = st.empty()
    progress_slot.progress(0, text="Indexing drawings…")

    try:
        for b in range(n_batches):
            start = b * INDEX_BATCH_SIZE
            batch_pngs = page_pngs[start : start + INDEX_BATCH_SIZE]
            content = _build_index_batch_content(batch_pngs)
            with st.spinner(
                f"Indexing batch {b + 1} of {n_batches} ({len(batch_pngs)} sheet(s))…"
            ):
                message = client.messages.create(
                    model=SPEC_PARSE_MODEL,
                    max_tokens=8192,
                    system=INDEX_DRAWINGS_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content}],
                )
            reply_parts: list[str] = []
            for block in message.content:
                if block.type == "text":
                    reply_parts.append(block.text)
            reply_text = "".join(reply_parts)
            batch_rows = _parse_json_array_from_model_text(reply_text)
            for row in batch_rows:
                if isinstance(row, dict):
                    combined.append(row)
            progress_slot.progress((b + 1) / n_batches, text="Indexing drawings…")
    except Exception as exc:
        progress_slot.empty()
        st.error(f"Drawing index failed: {exc}")
        return

    progress_slot.empty()

    try:
        with open(DRAWING_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        st.error(f"Could not write {DRAWING_INDEX_PATH}: {exc}")
        return

    st.success(f"Saved drawing index to `{DRAWING_INDEX_PATH.name}`.")

    st.subheader("Drawing index summary")
    st.write(
        f"**Sheets indexed:** {len(combined)} row(s) extracted from "
        f"{n_pages} drawing page(s), sent in {n_batches} batch(es) of up to "
        f"{INDEX_BATCH_SIZE} page(s) each."
    )
    table_rows = [
        {
            "Sheet number": r.get("sheet_number", ""),
            "Title": r.get("drawing_title", ""),
        }
        for r in combined
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)


def parse_spec_division(spec_text: str) -> None:
    """
    Send extracted specification text to Claude and show scope items in the
    main panel.
    """
    if not ANTHROPIC_API_KEY:
        st.error(
            "ANTHROPIC_API_KEY is not set. Add it to your `.env` file in the "
            "project folder."
        )
        return
    stripped = spec_text.strip()
    if not stripped:
        st.warning("No specification text to parse. Upload a PDF with text.")
        return

    user_prompt = (
        "Read this specification division and extract all scope items that "
        "would be required for a subcontractor performing this work. List "
        "each scope item on a separate line. Be specific and project-focused. "
        "Do not include administrative or submittal requirements. "
        f"Specification text: {stripped}"
    )

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        with st.spinner("Calling Claude to extract scope items…"):
            message = client.messages.create(
                model=SPEC_PARSE_MODEL,
                max_tokens=8192,
                system=SPEC_PARSE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
    except Exception as exc:
        st.error(f"Anthropic API request failed: {exc}")
        return

    reply_parts: list[str] = []
    for block in message.content:
        if block.type == "text":
            reply_parts.append(block.text)
    result = "".join(reply_parts)

    st.subheader("Extracted Scope Items")
    st.markdown(result)

ENTITY_OPTIONS = [
    "SCOTT Construction Ltd",
    "SCOTT Special Projects Ltd",
    "Scott DB Services Ltd",
    "SCOTT Construction Management Ltd",
    "SCOTT Construction Ontario Inc",
]

PROJECT_TYPE_OPTIONS = [
    "Commercial",
    "Residential",
    "Industrial",
    "Special Projects",
    "COV",
]


def _init_exclusive_group(prefix: str, options: list[str], default: str) -> None:
    if f"{prefix}_inited" not in st.session_state:
        st.session_state[f"{prefix}_value"] = default
        for o in options:
            st.session_state[f"{prefix}_{o}"] = o == default
        st.session_state[f"{prefix}_inited"] = True


def _exclusive_checkboxes(prefix: str, options: list[str]) -> str:
    _init_exclusive_group(prefix, options, options[0])
    for opt in options:
        checked = st.checkbox(
            opt,
            key=f"{prefix}_{opt}",
        )
        if checked and st.session_state[f"{prefix}_value"] != opt:
            st.session_state[f"{prefix}_value"] = opt
            for o in options:
                st.session_state[f"{prefix}_{o}"] = o == opt
            st.rerun()

    selected = [opt for opt in options if st.session_state.get(f"{prefix}_{opt}", False)]
    if len(selected) == 0:
        st.session_state[f"{prefix}_value"] = options[0]
        for o in options:
            st.session_state[f"{prefix}_{o}"] = o == options[0]
        st.rerun()
    if len(selected) >= 1:
        st.session_state[f"{prefix}_value"] = selected[0]
    return st.session_state[f"{prefix}_value"]


st.set_page_config(
    page_title="Scope Management Tool",
    page_icon="📐",
    layout="wide",
)

st.title("AI Assisted Scope Management")

with st.sidebar:
    st.header("Project setup")

    project_number = st.text_input("Project Number", placeholder="e.g. 5246")
    project_name = st.text_input("Project Name", placeholder="e.g. Marpole Library Expansion")

    st.subheader("Entity name")
    selected_entity = _exclusive_checkboxes("entity", ENTITY_OPTIONS)

    st.subheader("Project type")
    selected_project_type = _exclusive_checkboxes("ptype", PROJECT_TYPE_OPTIONS)

    st.subheader("Estimator notes (project level)")
    estimator_notes = st.text_area(
        "Notes that apply to all trades for this project",
        height=160,
        placeholder="High-level instructions for scope generation (Phase 1, exclusions, owner-supplied items, etc.)",
        label_visibility="collapsed",
    )

st.subheader("Documents")
uploaded_pdfs = st.file_uploader(
    "Upload project PDFs (drawings, specifications, quotes)",
    type=["pdf"],
    accept_multiple_files=True,
)

if uploaded_pdfs:
    try:
        first_pdf = uploaded_pdfs[0]
        extracted = extract_pdf_text(first_pdf.getvalue())
        preview = extracted[:500]
        st.caption(
            f"Extracted text preview (first 500 characters) — **{first_pdf.name}**"
        )
        st.text(preview)
    except Exception as exc:
        st.error(f"Could not extract text from PDF: {exc}")

st.divider()
st.subheader("Actions")

col1, col2, col3, col4 = st.columns(4)
with col1:
    scope_summary_clicked = st.button(
        "Generate Scope Summary",
        use_container_width=True,
    )
with col2:
    st.button("Generate Appendix B", use_container_width=True)
with col3:
    st.button("Populate CAR", use_container_width=True)
with col4:
    st.button("Generate Recommendation", use_container_width=True)

st.markdown("")
index_drawings_clicked = st.button(
    "Index Drawings",
    key="btn_index_drawings",
)

if scope_summary_clicked:
    if not uploaded_pdfs:
        st.warning("Upload at least one PDF.")
    else:
        try:
            combined_chunks: list[str] = []
            for f in uploaded_pdfs:
                combined_chunks.append(f"--- {f.name} ---\n")
                combined_chunks.append(extract_pdf_text(f.getvalue()))
                combined_chunks.append("\n\n")
            parse_spec_division("".join(combined_chunks))
        except Exception as exc:
            st.error(f"Could not read or process PDFs: {exc}")

if index_drawings_clicked:
    if not uploaded_pdfs:
        st.warning("Upload at least one PDF.")
    else:
        try:
            index_drawings(uploaded_pdfs[0].getvalue())
        except Exception as exc:
            st.error(f"Could not index drawings: {exc}")
