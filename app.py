"""
AI Assisted Scope Management Tool — Streamlit UI (layout only).
"""

import os

import fitz
import streamlit as st
from dotenv import load_dotenv


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
    st.button("Generate Scope Summary", use_container_width=True)
with col2:
    st.button("Generate Appendix B", use_container_width=True)
with col3:
    st.button("Populate CAR", use_container_width=True)
with col4:
    st.button("Generate Recommendation", use_container_width=True)
