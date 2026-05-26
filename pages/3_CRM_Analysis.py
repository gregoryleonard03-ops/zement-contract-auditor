from pathlib import Path
import streamlit as st

st.set_page_config(page_title="CRM Analysis — Zement", page_icon="📊", layout="wide")

AUDIT_FILE = Path(__file__).parent.parent / "data" / "smartsheet_audit.md"

CSS = """
<style>
.header-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.header-banner h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.header-banner p  { margin: 0.3rem 0 0; opacity: .85; font-size: 1.05rem; }

/* Override Streamlit markdown styles for audit */
.audit-body h2 { color: #1a1a2e; border-bottom: 2px solid #667eea;
                  padding-bottom: 6px; margin-top: 2rem; }
.audit-body h3 { color: #333; margin-top: 1.5rem; }
.audit-body table { width: 100%; border-collapse: collapse; }
.audit-body th { background: #667eea; color: white; padding: 8px 12px; text-align: left; }
.audit-body td { padding: 7px 12px; border-bottom: 1px solid #eee; }
.audit-body tr:nth-child(even) td { background: #f8f9fa; }
.audit-body code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size:.9em; }
.audit-body pre { background: #f4f4f4; padding: 1rem; border-radius: 8px;
                   overflow-x: auto; font-size:.85rem; }
.audit-body blockquote { border-left: 4px solid #667eea; padding-left: 1rem;
                          color: #666; background: #f8f9fa; border-radius: 0 8px 8px 0; }

/* KPI cards */
.kpi-row { display: flex; gap: 12px; margin: 1.5rem 0; flex-wrap: wrap; }
.kpi { background: white; border-radius: 10px; padding: 1.2rem 1.5rem; flex: 1;
        box-shadow: 0 1px 6px rgba(0,0,0,.07); text-align: center; min-width: 140px; }
.kpi .n { font-size: 2.2rem; font-weight: 800; line-height: 1; }
.kpi .l { font-size: .75rem; text-transform: uppercase; letter-spacing: .06em;
           color: #aaa; margin-top: 4px; }
.kpi.red .n   { color: #e74c3c; }
.kpi.orange .n { color: #f39c12; }
.kpi.green .n { color: #27ae60; }
.kpi.purple .n { color: #667eea; }
</style>
"""


def render_header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="header-banner">
            <h1>📊 CRM Audit — Smartsheet Analysis</h1>
            <p>Zement Stone Customer Database · 350 records · Analyzed May 26, 2026</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row():
    st.markdown(
        """
        <div class="kpi-row">
            <div class="kpi red">
                <div class="n">$1.64M</div>
                <div class="l">Potential losses / year</div>
            </div>
            <div class="kpi orange">
                <div class="n">281</div>
                <div class="l">Potential status (no movement)</div>
            </div>
            <div class="kpi orange">
                <div class="n">73</div>
                <div class="l">Records without any contact</div>
            </div>
            <div class="kpi green">
                <div class="n">100%</div>
                <div class="l">Records updated in last 30 days</div>
            </div>
            <div class="kpi purple">
                <div class="n">20</div>
                <div class="l">Hot leads to call this week</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    render_header()
    render_kpi_row()

    if not AUDIT_FILE.exists():
        st.error("Audit file not found. Expected: data/smartsheet_audit.md")
        return

    content = AUDIT_FILE.read_text(encoding="utf-8")

    # Download button
    col1, col2 = st.columns([5, 1])
    with col2:
        st.download_button(
            "⬇ Download Report",
            data=content.encode("utf-8"),
            file_name="zement-crm-audit-2026-05-26.md",
            mime="text/markdown",
        )

    st.divider()
    st.markdown(content)


if __name__ == "__main__":
    main()
