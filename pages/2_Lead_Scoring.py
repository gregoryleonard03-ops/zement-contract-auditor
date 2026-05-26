import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))
from scoring import score_permit

DATA_DIR = Path(__file__).parent.parent / "data"

CSS = """
<style>
.header-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px; padding: 2rem 2.5rem; margin-bottom: 1.5rem; color: white;
}
.header-banner h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.header-banner p  { margin: 0.3rem 0 0; opacity: .85; font-size: 1.05rem; }
.tier-hot  { background:#e74c3c; color:white; padding:3px 10px; border-radius:12px; font-size:.82rem; font-weight:700; }
.tier-warm { background:#f39c12; color:white; padding:3px 10px; border-radius:12px; font-size:.82rem; font-weight:700; }
.tier-cold { background:#bdc3c7; color:white; padding:3px 10px; border-radius:12px; font-size:.82rem; font-weight:700; }
.lead-card {
    background:white; border-radius:10px; padding:1rem 1.2rem; margin-bottom:.7rem;
    border-left:5px solid #ccc; box-shadow:0 1px 4px rgba(0,0,0,.06);
}
.score-bar-wrap { background:#f0f0f0; border-radius:6px; height:8px; width:100%; }
.score-bar { border-radius:6px; height:8px; }
</style>
"""

TIER_BORDER = {"Hot": "#e74c3c", "Warm": "#f39c12", "Cold": "#bdc3c7"}
TIER_EMOJI  = {"Hot": "🔥", "Warm": "🟡", "Cold": "❄️"}
REQUIRED_COLS = {"address", "description", "estimated_value"}


def render_header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="header-banner">
            <h1>🏗 AI Lead Scoring — Building Permits</h1>
            <p>Upload a CSV/XLSX with permit data to score leads · Hot = Call today · Warm = Email this week</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stats(df: pd.DataFrame):
    hot  = (df["tier"] == "Hot").sum()
    warm = (df["tier"] == "Warm").sum()
    cold = (df["tier"] == "Cold").sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Leads", len(df))
    c2.metric("🔥 Hot",  hot)
    c3.metric("🟡 Warm", warm)
    c4.metric("❄️ Cold", cold)


def render_lead_card(row: pd.Series):
    tier   = row.get("tier", "Cold")
    score  = int(row.get("score", 0))
    border = TIER_BORDER.get(tier, "#ccc")
    emoji  = TIER_EMOJI.get(tier, "")
    pct    = min(100, score)

    address    = row.get("address", "—")
    value      = row.get("estimated_value", 0)
    try:
        value_str = f"${float(value):,.0f}"
    except Exception:
        value_str = str(value)

    desc       = str(row.get("description", ""))[:120]
    contractor = row.get("contractor_name", "")
    action     = row.get("action", "")

    st.markdown(
        f"""
        <div class="lead-card" style="border-left-color:{border}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <strong style="font-size:1rem;">{address}</strong>
                <span class="tier-{tier.lower()}">{emoji} {tier} · {score}/100</span>
            </div>
            <div style="margin:6px 0 4px;">
                <div class="score-bar-wrap">
                    <div class="score-bar" style="width:{pct}%;background:{border};"></div>
                </div>
            </div>
            <div style="font-size:.85rem;color:#555;margin-top:4px;">
                💰 {value_str} &nbsp;|&nbsp; 🏢 {contractor or '—'} &nbsp;|&nbsp; ✅ <em>{action}</em>
            </div>
            {"<div style='font-size:.8rem;color:#888;margin-top:3px;'>"+desc+"</div>" if desc else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("View outreach email"):
        st.text(row.get("outreach", "—"))


def read_uploaded_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    if name.endswith(".txt"):
        # try tab-separated, then comma
        try:
            return pd.read_csv(io.BytesIO(data), sep="\t")
        except Exception:
            return pd.read_csv(io.BytesIO(data))
    raise ValueError(f"Unsupported format: {uploaded.name}")


def score_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.lower().strip() for c in df.columns]
    results = []
    for _, row in df.iterrows():
        scored = score_permit(row)
        scored.update({
            "address":         row.get("address", ""),
            "estimated_value": row.get("estimated_value", 0),
            "description":     str(row.get("description", ""))[:150],
            "contractor_name": row.get("contractor_name", ""),
            "project_type":    row.get("project_type", ""),
            "work_type":       row.get("work_type", ""),
            "category":        row.get("category", "commercial"),
            "issue_date":      row.get("issue_date", ""),
            "permit_id":       row.get("permit_id", ""),
            "source":          row.get("source", ""),
            "city":            row.get("city", ""),
        })
        results.append(scored)
    return pd.DataFrame(results).sort_values("score", ascending=False)


def show_leads(df: pd.DataFrame, title: str):
    st.subheader(title)
    render_stats(df)

    tier_filter = st.radio(
        "Filter", ["All", "🔥 Hot", "🟡 Warm", "❄️ Cold"],
        horizontal=True, key=f"filter_{hash(title) % 9999}"
    )
    if tier_filter != "All":
        tier_map = {"🔥 Hot": "Hot", "🟡 Warm": "Warm", "❄️ Cold": "Cold"}
        df = df[df["tier"] == tier_map[tier_filter]]

    st.caption(f"Showing {len(df)} leads")
    for _, row in df.iterrows():
        render_lead_card(row)


def main():
    render_header()

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### Load Data")

        if st.button("📊 Load Demo (Colorado 5K+)", use_container_width=True):
            demo_path = DATA_DIR / "demo_scored.csv"
            if demo_path.exists():
                st.session_state["leads_df"] = pd.read_csv(demo_path)
                st.session_state["leads_title"] = "Colorado Building Permits — Demo (5,186 leads)"
                st.session_state["show_html_demo"] = False
                st.rerun()
            else:
                st.warning("Demo CSV not found.")

        st.divider()
        st.markdown("**Expected CSV columns:**")
        st.caption("`address`, `description`, `estimated_value` *(required)*")
        st.caption("`project_type`, `work_type`, `category`, `contractor_name`, `city` *(optional)*")

    # ── Example button + upload ──────────────────────────────
    col_ex, col_up = st.columns([1, 2])

    with col_ex:
        if st.button(
            "🗺 View Example Report",
            use_container_width=True,
            help="Opens the full Colorado + Fort Collins scored leads report",
        ):
            st.session_state["show_html_demo"] = not st.session_state.get("show_html_demo", False)
            st.session_state.pop("leads_df", None)

    with col_up:
        uploaded = st.file_uploader(
            "Upload permits file (CSV, XLSX, TXT)",
            type=["csv", "xlsx", "xls", "txt"],
            help="Upload your own permits data to score leads",
            label_visibility="collapsed",
        )

    # ── HTML demo view ───────────────────────────────────────
    if st.session_state.get("show_html_demo"):
        html_path = DATA_DIR / "denver_demo.html"
        if html_path.exists():
            html_content = html_path.read_text(encoding="utf-8")
            st.markdown("### Colorado + Fort Collins — Lead Scoring Report")
            components.html(html_content, height=900, scrolling=True)
        else:
            st.error("Demo HTML not found: data/denver_demo.html")
        return

    # ── Score uploaded file ───────────────────────────────────
    if uploaded:
        if st.button("Score Leads", type="primary", use_container_width=True):
            with st.spinner(f"Scoring {uploaded.name}..."):
                try:
                    df_raw = read_uploaded_file(uploaded)
                    df_raw.columns = [c.lower().strip() for c in df_raw.columns]
                    missing = REQUIRED_COLS - set(df_raw.columns)
                    if missing:
                        st.error(f"Missing required columns: {', '.join(missing)}")
                    else:
                        scored = score_dataframe(df_raw)
                        st.session_state["leads_df"] = scored
                        st.session_state["leads_title"] = f"{uploaded.name} — {len(scored)} leads scored"
                        st.rerun()
                except Exception as e:
                    st.error(f"Error reading file: {e}")

    # ── Results ───────────────────────────────────────────────
    leads_df = st.session_state.get("leads_df")
    if leads_df is not None:
        show_leads(leads_df, st.session_state.get("leads_title", "Results"))
    elif not uploaded:
        st.markdown(
            """
            <div style="text-align:center;padding:3rem;color:#888;">
                <div style="font-size:3rem;">🏗</div>
                <p style="font-size:1.1rem;">Upload a permits file or click "View Example Report" to see a live demo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


main()
