import io
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent.parent))
from scoring import score_permit
from crm_utils import load_crm, add_to_crm, STATUS_ICON

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
.act-vhigh { background:#27ae60; color:white; padding:2px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }
.act-high  { background:#2980b9; color:white; padding:2px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }
.act-med   { background:#f39c12; color:white; padding:2px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }
.act-low   { background:#95a5a6; color:white; padding:2px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }
.act-unk   { background:#ddd;    color:#666;  padding:2px 8px; border-radius:10px; font-size:.78rem; }
.email-ok   { background:#e8f5e9; color:#2e7d32; padding:2px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }
.email-need { background:#fff3e0; color:#e65100; padding:2px 8px; border-radius:10px; font-size:.78rem; font-weight:600; }
.lead-card {
    background:white; border-radius:10px; padding:1rem 1.2rem; margin-bottom:.7rem;
    border-left:5px solid #ccc; box-shadow:0 1px 4px rgba(0,0,0,.06);
}
.score-bar-wrap { background:#f0f0f0; border-radius:6px; height:8px; width:100%; }
.score-bar { border-radius:6px; height:8px; }
</style>
"""

TIER_BORDER  = {"Hot": "#e74c3c", "Warm": "#f39c12", "Cold": "#bdc3c7"}
TIER_EMOJI   = {"Hot": "🔥",      "Warm": "🟡",      "Cold": "❄️"}
ACT_CLASS    = {"Very High": "act-vhigh", "High": "act-high", "Medium": "act-med", "Low": "act-low"}
ACT_LABEL    = {"Very High": "⚡ Very High", "High": "↑ High", "Medium": "~ Medium", "Low": "↓ Low"}
REQUIRED_COLS = {"address", "description", "estimated_value"}


def render_header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="header-banner">
            <h1>🏗 AI Lead Scoring — Building Permits</h1>
            <p>Curated leads from permit databases + ConstructionWire · Hot = Call today · Warm = Email this week</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stats(df: pd.DataFrame):
    hot  = (df["tier"] == "Hot").sum()
    warm = (df["tier"] == "Warm").sum()
    cold = (df["tier"] == "Cold").sum()
    has_email = df["email"].notna() & df["email"].astype(str).str.strip().ne("") if "email" in df.columns else pd.Series([False] * len(df))
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total",    len(df))
    c2.metric("🔥 Hot",   hot)
    c3.metric("🟡 Warm",  warm)
    c4.metric("❄️ Cold",  cold)
    c5.metric("✉️ Email ready", int(has_email.sum()))


_BADGE = "padding:2px 8px;border-radius:10px;font-size:.78rem;font-weight:600;"
ACT_STYLE = {
    "Very High": f"background:#27ae60;color:white;{_BADGE}",
    "High":      f"background:#2980b9;color:white;{_BADGE}",
    "Medium":    f"background:#f39c12;color:white;{_BADGE}",
    "Low":       f"background:#95a5a6;color:white;{_BADGE}",
}
TIER_STYLE = {
    "Hot":  "background:#e74c3c;color:white;padding:3px 10px;border-radius:12px;font-size:.82rem;font-weight:700;",
    "Warm": "background:#f39c12;color:white;padding:3px 10px;border-radius:12px;font-size:.82rem;font-weight:700;",
    "Cold": "background:#bdc3c7;color:white;padding:3px 10px;border-radius:12px;font-size:.82rem;font-weight:700;",
}


def actuality_html(act: str) -> str:
    style = ACT_STYLE.get(act, f"background:#ddd;color:#666;{_BADGE}")
    lbl = ACT_LABEL.get(act, act or "—")
    return f'<span style="{style}">{lbl}</span>'


def email_html(email: str) -> str:
    if email and str(email).strip() and str(email).strip() != "nan":
        return f'<span style="background:#e8f5e9;color:#2e7d32;{_BADGE}">✉ {email}</span>'
    return f'<span style="background:#fff3e0;color:#e65100;{_BADGE}">⚠️ Email нужен</span>'


def render_lead_card(row: pd.Series, key_prefix: str = "card", idx: int = 0):
    tier   = row.get("tier", "Cold")
    score  = int(row.get("score", 0))
    emoji  = TIER_EMOJI.get(tier, "")

    raw_address = str(row.get("address", "")).strip()
    address = raw_address if raw_address and raw_address.lower() not in ("nan", "", ", ,") else ""
    if not address:
        desc_full = str(row.get("description", ""))
        project_name = desc_full.split("—")[0].strip() if "—" in desc_full else desc_full[:60]
        address = project_name or "—"

    project  = str(row.get("contractor_name", "") or row.get("company", "") or "—")
    action   = str(row.get("action", ""))
    desc     = str(row.get("description", ""))[:140]
    stage    = str(row.get("stage", "")) if row.get("stage") else ""
    act      = str(row.get("актуальность", ""))
    email    = str(row.get("email", ""))
    city     = str(row.get("city", ""))

    value = row.get("estimated_value", 0)
    try:
        value_str = f"${float(value):,.0f}"
    except Exception:
        value_str = str(value)

    # CRM status check
    crm_data = st.session_state.get("crm_data", {})
    email_key_check = email.lower().strip() if email and email.strip() not in ("", "nan") else ""
    crm_entry = crm_data.get(email_key_check) if email_key_check else None
    crm_status = crm_entry.get("status", "") if crm_entry else ""

    # Plain text labels — no HTML, no escaping needed
    act_label  = ACT_LABEL.get(act, act or "")
    has_email  = email and email.strip() not in ("", "nan")
    email_disp = f"✉ {email}" if has_email else "⚠️ Email нужен"
    crm_disp   = f"{STATUS_ICON.get(crm_status, '🔵')} {crm_status}" if crm_status else ""
    tier_color = {"Hot": "red", "Warm": "orange", "Cold": "blue"}.get(tier, "grey")

    meta_parts = [f"💰 {value_str}", f"🏢 {project}"]
    if city:   meta_parts.append(f"📍 {city}")
    if stage:  meta_parts.append(f"📅 {stage}")
    if action: meta_parts.append(f"✅ {action}")

    with st.container(border=True):
        col_main, col_tier = st.columns([5, 1])
        with col_main:
            header = f"**{address}**"
            if crm_disp:
                header += f"  `{crm_disp}`"
            st.markdown(header)
            st.caption("  |  ".join(meta_parts))
            if desc and desc.strip() not in ("", "nan"):
                st.caption(desc)
        with col_tier:
            st.markdown(f":{tier_color}[{emoji} **{tier}**]")
            st.progress(score / 100)
            st.caption(f"**{score}/100**")
            if act_label:
                st.caption(act_label)
            st.caption(email_disp)

    with st.expander("View outreach email / Add to CRM", key=f"exp_{key_prefix}_{idx}"):
        st.text(row.get("outreach", "—"))
        st.markdown("---")

        email_val = str(row.get("email", "")).strip()
        crm = st.session_state.get("crm_data", {})

        if not email_val or email_val == "nan":
            st.warning("⚠️ Нет email — нельзя добавить в CRM")
        else:
            email_key = email_val.lower()
            if email_key in crm:
                status = crm[email_key].get("status", "В очереди")
                icon = STATUS_ICON.get(status, "🔵")
                st.success(f"{icon} Уже в CRM — статус: **{status}**")
            else:
                card_key = f"crm_{key_prefix}_{idx}_{email_key.replace('@','_').replace('.','_')}"
                if st.button("➕ В CRM (сгенерировать письмо)", key=card_key, type="primary"):
                    with st.spinner("Добавляю в CRM и генерирую письмо…"):
                        updated = add_to_crm(row.to_dict(), crm)
                    st.session_state["crm_data"] = updated
                    st.success(f"✅ {str(row.get('company') or row.get('contractor_name',''))[:40]} добавлена в CRM!")
                    st.rerun()


def show_leads(df: pd.DataFrame, key_prefix: str):
    render_stats(df)

    f1, f2, f3 = st.columns(3)
    with f1:
        tier_filter = st.radio(
            "Tier", ["All", "🔥 Hot", "🟡 Warm", "❄️ Cold"],
            horizontal=True, key=f"tier_{key_prefix}"
        )
    with f2:
        act_opts = ["All"] + [a for a in ["Very High", "High", "Medium", "Low"] if a in df.get("актуальность", pd.Series([])).values]
        act_filter = st.selectbox("Актуальность", act_opts, key=f"act_{key_prefix}")
    with f3:
        email_filter = st.selectbox("Email", ["All", "✉️ Есть email", "⚠️ Нужен email"], key=f"email_{key_prefix}")

    filtered = df.copy()
    if tier_filter != "All":
        tier_map = {"🔥 Hot": "Hot", "🟡 Warm": "Warm", "❄️ Cold": "Cold"}
        filtered = filtered[filtered["tier"] == tier_map[tier_filter]]
    if act_filter != "All":
        filtered = filtered[filtered["актуальность"] == act_filter]
    if email_filter == "✉️ Есть email":
        filtered = filtered[filtered["email"].notna() & filtered["email"].astype(str).str.strip().ne("") & filtered["email"].astype(str).str.strip().ne("nan")]
    elif email_filter == "⚠️ Нужен email":
        filtered = filtered[~(filtered["email"].notna() & filtered["email"].astype(str).str.strip().ne("") & filtered["email"].astype(str).str.strip().ne("nan"))]

    PAGE_SIZE = 15
    total = len(filtered)
    n_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    page_key = f"page_{key_prefix}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    page = min(st.session_state[page_key], n_pages - 1)

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_df = filtered.iloc[start:end]

    st.caption(f"Лидов: {total} · стр. {page + 1} из {n_pages} · показано {start + 1}–{end}")

    if n_pages > 1:
        pc = st.columns([1, 4, 1])
        with pc[0]:
            if st.button("◀ Назад", key=f"prev_{key_prefix}", disabled=(page == 0)):
                st.session_state[page_key] = page - 1
                st.rerun()
        with pc[2]:
            if st.button("Вперёд ▶", key=f"next_{key_prefix}", disabled=(page == n_pages - 1)):
                st.session_state[page_key] = page + 1
                st.rerun()

    for idx, (_, row) in enumerate(page_df.iterrows()):
        render_lead_card(row, key_prefix, start + idx)


def ensure_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["email", "contact_name", "stage", "актуальность", "needs_email"]:
        if col not in df.columns:
            df[col] = "" if col != "needs_email" else True
    df["email"] = df["email"].fillna("").astype(str)
    df["актуальность"] = df["актуальность"].fillna("Unknown").astype(str)
    return df


def load_curated() -> dict[str, pd.DataFrame]:
    sources = {}

    permits_path = DATA_DIR / "demo_scored.csv"
    if permits_path.exists():
        sources["permits"] = ensure_cols(pd.read_csv(permits_path))

    cw_co_path = DATA_DIR / "cw_colorado_scored.csv"
    if cw_co_path.exists():
        sources["cw_co"] = ensure_cols(pd.read_csv(cw_co_path))

    cw_other_path = DATA_DIR / "cw_other_scored.csv"
    if cw_other_path.exists():
        sources["cw_other"] = ensure_cols(pd.read_csv(cw_other_path))

    return sources


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
            "email":           row.get("email", ""),
            "contact_name":    row.get("contact_name", ""),
            "stage":           row.get("stage", ""),
            "актуальность":    row.get("актуальность", ""),
            "needs_email":     str(row.get("email", "")).strip() in ("", "nan"),
        })
        results.append(scored)
    return pd.DataFrame(results).sort_values("score", ascending=False)


def read_uploaded_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(data))
    if name.endswith(".txt"):
        try:
            return pd.read_csv(io.BytesIO(data), sep="\t")
        except Exception:
            return pd.read_csv(io.BytesIO(data))
    raise ValueError(f"Unsupported format: {uploaded.name}")


def main():
    render_header()
    st.markdown(CSS, unsafe_allow_html=True)

    # Load CRM state once per session
    if "crm_data" not in st.session_state:
        st.session_state["crm_data"] = load_crm()

    sources = load_curated()

    # ── Tabs ──────────────────────────────────────────────────
    tab_labels = [
        "🗂 Все лиды",
        "🏔 CW Colorado",
        "🌎 CW Другие штаты",
        "📋 Denver + Fort Collins",
        "⛷ Горные курорты",
        "📤 Загрузить файл",
    ]
    tabs = st.tabs(tab_labels)

    # ── Tab 0: All Combined ────────────────────────────────────
    with tabs[0]:
        all_dfs = [df for df in sources.values()]
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True).sort_values("score", ascending=False)
            st.markdown(f"**Все источники объединены** — {len(combined)} лидов")
            show_leads(combined, "all")
        else:
            st.info("Данные не найдены.")

    # ── Tab 1: CW Colorado ────────────────────────────────────
    with tabs[1]:
        if "cw_co" in sources:
            df = sources["cw_co"]
            st.markdown(f"**ConstructionWire — Colorado** · {len(df)} проектов · "
                        f"{df['email'].astype(str).str.strip().ne('').sum()} с прямым email")
            show_leads(df, "cw_co")
        else:
            st.warning("Файл cw_colorado_scored.csv не найден.")

    # ── Tab 2: CW Other States ────────────────────────────────
    with tabs[2]:
        if "cw_other" in sources:
            df = sources["cw_other"]
            has_email = df["email"].astype(str).str.strip().ne("") & df["email"].astype(str).str.strip().ne("nan")
            st.markdown(f"**ConstructionWire — Другие штаты** · {len(df)} проектов · "
                        f"{has_email.sum()} с прямым email")
            show_leads(df, "cw_other")
        else:
            st.warning("Файл cw_other_scored.csv не найден.")

    # ── Tab 3: Denver + Fort Collins ─────────────────────────
    with tabs[3]:
        if "permits" in sources:
            df = sources["permits"]
            st.markdown(f"**Denver + Fort Collins building permits** · {len(df)} записей")
            show_leads(df, "permits")
        else:
            st.warning("Файл demo_scored.csv не найден.")

    # ── Tab 4: Mountain Resorts ───────────────────────────────
    with tabs[4]:
        st.info("⛷ Данные по горным курортам в процессе сбора.")
        st.markdown("""
**Источники в работе:**

| Регион | Сайт | Статус |
|--------|------|--------|
| **Aspen / Pitkin County** | [aspen.gov/Public-Records](https://aspen.gov/1219/Public-Records) | ⬇️ Excel 2024–2026 доступен |
| **Eagle County** (Vail, Avon) | [css.eaglecounty.us](https://css.eaglecounty.us/EnerGov_Prod/SelfService) | 🔍 Ручной поиск / EnerGov |
| **Summit County** (Breckenridge, Frisco) | [summitcountyco.gov](https://commdev.summitcountyco.gov/eTRAKiT3/Search/permit.aspx) | 🔍 Ручной поиск / eTRAKiT |

Когда Excel от Aspen будет добавлен — данные появятся в этой вкладке автоматически.
        """)

    # ── Tab 5: Upload ─────────────────────────────────────────
    with tabs[5]:
        st.markdown("#### Загрузить свой файл с пермитами")

        col_ex, col_up = st.columns([1, 2])
        with col_ex:
            if st.button("🗺 View Example Report", use_container_width=True):
                st.session_state["show_html_demo"] = not st.session_state.get("show_html_demo", False)
                st.session_state.pop("uploaded_df", None)

        with col_up:
            uploaded = st.file_uploader(
                "Upload permits file (CSV, XLSX, TXT)",
                type=["csv", "xlsx", "xls", "txt"],
                label_visibility="collapsed",
            )

        if st.session_state.get("show_html_demo"):
            html_path = DATA_DIR / "denver_demo.html"
            if html_path.exists():
                html_content = html_path.read_text(encoding="utf-8")
                st.markdown("### Colorado + Fort Collins — Lead Scoring Report")
                components.html(html_content, height=900, scrolling=True)
            else:
                st.error("Demo HTML not found.")

        elif uploaded:
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
                            st.session_state["uploaded_df"] = scored
                            st.session_state["uploaded_title"] = f"{uploaded.name} — {len(scored)} leads"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error reading file: {e}")

            if "uploaded_df" in st.session_state:
                st.markdown(f"### {st.session_state.get('uploaded_title','Results')}")
                show_leads(st.session_state["uploaded_df"], "upload")

        else:
            st.markdown(
                """
                <div style="text-align:center;padding:2rem;color:#888;">
                    <div style="font-size:2.5rem;">📁</div>
                    <p>Upload a CSV/XLSX permits file to score leads</p>
                    <p style="font-size:.85rem;">Required columns: <code>address</code>, <code>description</code>, <code>estimated_value</code></p>
                </div>
                """,
                unsafe_allow_html=True,
            )


main()
