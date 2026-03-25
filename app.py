"""
AI Assisted Scope Management Tool — Streamlit UI (layout only).
"""

import os

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
