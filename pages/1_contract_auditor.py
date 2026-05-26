import os
import io
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from analyzer import extract_text, analyze_contract

TIER_COLORS = {
    "Low Risk":    {"border": "#27ae60", "bg": "#eafaf1", "badge": "#27ae60", "emoji": "🟢"},
    "Medium Risk": {"border": "#f39c12", "bg": "#fef9e7", "badge": "#f39c12", "emoji": "🟡"},
    "High Risk":   {"border": "#e74c3c", "bg": "#fdecea", "badge": "#e74c3c", "emoji": "🔴"},
}

SEVERITY_COLORS = {
    "high":   ("🔴", "#e74c3c"),
    "medium": ("🟡", "#f39c12"),
    "low":    ("🟢", "#27ae60"),
}

SAMPLE_DIR = Path(__file__).parent.parent / "tests" / "sample_contracts"

CSS = """
<style>
.header-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.header-banner h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.header-banner p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 1.05rem; }
.doc-card { border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; border-left: 5px solid #ccc; }
.badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px;
         font-size: 0.85rem; font-weight: 600; color: white; margin-left: 0.5rem; }
.verdict-chip { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px;
                font-size: 0.8rem; font-weight: 700; background: #f0f0f0; color: #333; }
.flag-card { border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.6rem;
             border-left: 4px solid #ccc; background: #fafafa; }
.quote-box { font-family: monospace; font-size: 0.82rem; background: #f4f4f4;
             border-radius: 4px; padding: 0.4rem 0.6rem; margin: 0.3rem 0;
             color: #555; word-break: break-word; }
</style>
"""


def render_header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="header-banner">
            <h1>🔍 Zement Contract Auditor</h1>
            <p>AI-powered risk analysis for vendor contracts — upload a PDF, DOCX, or TXT to get started</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_stats(results: list):
    total = len(results)
    high_risk = sum(1 for r in results if r["tier"] == "High Risk")
    safe = sum(1 for r in results if r["tier"] == "Low Risk")
    c1, c2, c3 = st.columns(3)
    c1.metric("Documents Analyzed", total)
    c2.metric("High Risk", high_risk)
    c3.metric("Safe to Sign", safe)


def render_flag(flag: dict):
    sev = flag.get("severity", "low").lower()
    emoji, color = SEVERITY_COLORS.get(sev, ("🟢", "#27ae60"))
    impact = flag.get("estimated_dollar_impact")
    impact_str = f"  — **${impact:,} estimated impact**" if impact else ""

    st.markdown(
        f"""
        <div class="flag-card" style="border-left-color:{color}">
            <strong>{emoji} {flag.get('title', 'Issue')}</strong>
            <span style="font-size:0.8rem;color:{color};margin-left:6px;">{sev.upper()}{impact_str}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    quote = flag.get("quote", "")
    if quote:
        st.markdown(f'<div class="quote-box">"{quote}"</div>', unsafe_allow_html=True)
    explanation = flag.get("explanation", "")
    if explanation:
        st.caption(explanation)


def render_doc_card(result: dict):
    tier = result["tier"]
    colors = TIER_COLORS.get(tier, TIER_COLORS["Medium Risk"])
    score = result["score"]
    verdict = result["verdict"]
    flags = result.get("red_flags", [])
    summary = result.get("summary", "")

    st.markdown(
        f"""
        <div class="doc-card" style="background:{colors['bg']};border-left-color:{colors['border']}">
            <strong style="font-size:1.05rem;">{result['filename']}</strong>
            <span class="badge" style="background:{colors['badge']};">{colors['emoji']} {tier}</span>
            <span class="verdict-chip" style="margin-left:0.5rem;">{verdict}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_score, col_bar = st.columns([1, 4])
    col_score.metric("Risk Score", f"{score}/100", help="Higher = safer to sign")
    col_bar.progress(score / 100)

    if summary:
        st.info(summary)

    if flags:
        with st.expander(f"View {len(flags)} red flag(s)"):
            for flag in flags:
                render_flag(flag)
    else:
        st.success("No red flags detected.")

    st.divider()


def run_analysis(uploaded_files):
    results = []
    progress = st.progress(0, text="Starting analysis...")
    total = len(uploaded_files)

    for i, f in enumerate(uploaded_files):
        progress.progress(i / total, text=f"Analyzing {f.name}...")
        try:
            text = extract_text(f)
        except ValueError as e:
            results.append({
                "filename": f.name,
                "score": 50,
                "tier": "Medium Risk",
                "verdict": "SIGN WITH REVISIONS",
                "red_flags": [],
                "summary": str(e),
            })
            continue

        result = analyze_contract(text)
        result["filename"] = f.name
        results.append(result)

    progress.progress(1.0, text="Done!")
    progress.empty()
    return results


def load_sample_contracts():
    samples = []
    for name in ["contract_a_clean.pdf", "contract_b_medium.pdf", "contract_c_toxic.pdf"]:
        path = SAMPLE_DIR / name
        if path.exists():
            content = path.read_bytes()
            fake_file = io.BytesIO(content)
            fake_file.name = name
            samples.append(fake_file)
    return samples


def main():
    render_header()

    with st.sidebar:
        st.markdown("### Demo")
        st.caption("No contracts on hand? Load sample contracts to see the analyzer in action.")
        if st.button("Load Demo Contracts", use_container_width=True):
            samples = load_sample_contracts()
            if samples:
                with st.spinner("Analyzing 3 sample contracts..."):
                    st.session_state["analyzed_files"] = run_analysis(samples)
                st.rerun()
            else:
                st.warning("Sample contracts not found.")

        st.divider()
        st.markdown("**About**")
        st.caption(
            "Zement Contract Auditor uses Claude AI to scan vendor contracts for hidden fees, "
            "unfavorable clauses, and financial risks — before you sign."
        )

    uploaded = st.file_uploader(
        "Upload vendor contracts (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="Files are processed in-session and never stored.",
    )

    if uploaded:
        if st.button("Analyze Contracts", type="primary", use_container_width=True):
            with st.spinner("Analyzing contracts with Claude AI..."):
                st.session_state["analyzed_files"] = run_analysis(uploaded)
            st.rerun()

    results = st.session_state.get("analyzed_files", [])

    if results:
        st.markdown("## Analysis Results")
        render_summary_stats(results)
        st.markdown("---")
        for result in results:
            render_doc_card(result)
    elif not uploaded:
        st.markdown(
            """
            <div style="text-align:center;padding:3rem;color:#888;">
                <div style="font-size:3rem;">📄</div>
                <p style="font-size:1.1rem;">Upload a contract above or load demo contracts from the sidebar.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


main()
