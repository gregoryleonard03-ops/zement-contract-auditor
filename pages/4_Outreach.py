import sys
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from crm_utils import (
    STATUSES, STATUS_ICON,
    load_crm, save_crm, mark_sent, count_sent_today,
    generate_email_for_lead,
)

DAILY_LIMIT = 5  # manual sending limit while SMTP is not set up

st.set_page_config(page_title="CRM — Zement Stone", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.crm-card { background:white; border-radius:10px; padding:.9rem 1.1rem;
            margin-bottom:.5rem; border-left:5px solid #ccc;
            box-shadow:0 1px 4px rgba(0,0,0,.07); }
.crm-card.queue  { border-color:#3498db; }
.crm-card.sent   { border-color:#e67e22; }
.crm-card.reply  { border-color:#27ae60; }
.crm-card.deal   { border-color:#2ecc71; }
.crm-card.lost   { border-color:#e74c3c; }
.status-badge { display:inline-block; padding:2px 10px; border-radius:10px;
                font-size:.78rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
if "crm" not in st.session_state:
    st.session_state.crm = load_crm()

crm = st.session_state.crm

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📨 CRM — Outreach")
st.caption("Лиды из Lead Scoring · отслеживание писем, ответов и сделок")

if not crm:
    st.info("CRM пуста. Перейди в **Lead Scoring** и нажми **➕ В CRM** на нужных лидах.")
    st.stop()

# ── Metrics ───────────────────────────────────────────────────────────────────
counts = {}
for entry in crm.values():
    s = entry.get("status", "В очереди")
    counts[s] = counts.get(s, 0) + 1

sent_today = count_sent_today(crm)
can_send = max(0, DAILY_LIMIT - sent_today)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("В CRM", len(crm))
c2.metric("🔵 В очереди", counts.get("В очереди", 0))
c3.metric("📨 Отправлено", counts.get("Отправлено", 0))
c4.metric("💬 Ответили", counts.get("Ответил", 0))
c5.metric("📅 Митингов", counts.get("Митинг назначен", 0))
c6.metric("✅ Сделок", counts.get("Сделка", 0))

# Daily limit banner
if can_send > 0:
    st.success(f"Сегодня отправлено вручную: **{sent_today}** / {DAILY_LIMIT} — можно ещё **{can_send}**")
else:
    st.warning(f"Дневной лимит {DAILY_LIMIT} писем достигнут. Продолжим завтра (или включим SMTP).")

st.divider()

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)
filter_status = col_f1.multiselect(
    "Статус", STATUSES,
    default=["В очереди", "Отправлено", "Ответил", "Митинг назначен"],
)
all_cities = sorted({e.get("city", "") for e in crm.values() if e.get("city")})
filter_city = col_f2.multiselect("Город", all_cities)
all_tiers = sorted({e.get("tier", "") for e in crm.values() if e.get("tier")})
filter_tier = col_f3.multiselect("Tier", all_tiers)

# ── Lead cards ────────────────────────────────────────────────────────────────
shown = 0
for email_key, entry in sorted(crm.items(), key=lambda x: x[1].get("added_date", ""), reverse=True):
    status = entry.get("status", "В очереди")
    city   = entry.get("city", "")
    tier   = entry.get("tier", "")

    if filter_status and status not in filter_status:
        continue
    if filter_city and city not in filter_city:
        continue
    if filter_tier and tier not in filter_tier:
        continue

    shown += 1
    company = entry.get("company", "—")
    email   = entry.get("email", "")
    value   = entry.get("estimated_value", "")
    ptype   = entry.get("project_type", "")
    icon    = STATUS_ICON.get(status, "🔵")

    try:
        val_fmt = f"${float(str(value).replace(',','') or 0):,.0f}"
    except Exception:
        val_fmt = str(value)

    label = f"{icon} **{company}** — {email} | {city} | {ptype} | {val_fmt}"

    with st.expander(label, expanded=(status == "В очереди" and shown <= 3), key=f"entry_{email_key}"):
        left, right = st.columns([2, 3])

        # ── Left: info + status ───────────────────────────────
        with left:
            st.markdown(f"**Компания:** {company}")
            st.markdown(f"**Email:** `{email}`")
            if entry.get("address"):
                st.markdown(f"**Адрес:** {entry['address']}")
            if entry.get("project_name"):
                st.caption(entry["project_name"][:120])

            info_cols = st.columns(3)
            info_cols[0].markdown(f"**Tier:** {tier}")
            info_cols[1].markdown(f"**Город:** {city}")
            info_cols[2].markdown(f"**Бюджет:** {val_fmt}")
            if entry.get("added_date"):
                st.caption(f"В CRM: {entry['added_date']} · Источник: {entry.get('source','')}")

            st.markdown("---")

            # Status
            new_status = st.selectbox(
                "Статус", STATUSES,
                index=STATUSES.index(status) if status in STATUSES else 0,
                key=f"sel_{email_key}",
            )
            notes = st.text_area(
                "Заметки",
                value=entry.get("notes", ""),
                height=80,
                key=f"notes_{email_key}",
                placeholder="Ответил 28 мая, перезвонить через неделю…",
            )

            btn_cols = st.columns(2)
            if btn_cols[0].button("💾 Сохранить", key=f"save_{email_key}"):
                crm[email_key]["status"] = new_status
                crm[email_key]["notes"] = notes
                crm[email_key]["last_updated"] = date.today().isoformat()
                save_crm(crm)
                st.session_state.crm = crm
                st.success("Сохранено")
                st.rerun()

            if status == "В очереди":
                if can_send > 0:
                    if btn_cols[1].button("✅ Отправлено", key=f"sent_{email_key}", type="primary"):
                        crm = mark_sent(email_key, crm)
                        st.session_state.crm = crm
                        st.success("Статус обновлён → Отправлено")
                        st.rerun()
                else:
                    btn_cols[1].button("✅ Отправлено", key=f"sent_{email_key}", disabled=True,
                                       help="Дневной лимит достигнут")

        # ── Right: email text ─────────────────────────────────
        with right:
            subject = entry.get("email_subject", "")
            body    = entry.get("email_body", "")

            if not body:
                if st.button("✍️ Сгенерировать письмо", key=f"gen_{email_key}"):
                    with st.spinner("Генерирую…"):
                        subject, body = generate_email_for_lead(dict(entry))
                    crm[email_key]["email_subject"] = subject
                    crm[email_key]["email_body"] = body
                    crm[email_key]["last_updated"] = date.today().isoformat()
                    save_crm(crm)
                    st.session_state.crm = crm
                    st.rerun()
            else:
                st.markdown(f"**Тема:** `{subject}`")
                st.markdown("**Текст письма** (нажми кнопку копирования справа ↗):")
                # st.code shows built-in copy button
                st.code(body, language=None)

                if st.button("🔄 Перегенерировать", key=f"regen_{email_key}"):
                    with st.spinner("Генерирую…"):
                        subject, body = generate_email_for_lead(dict(entry))
                    crm[email_key]["email_subject"] = subject
                    crm[email_key]["email_body"] = body
                    crm[email_key]["last_updated"] = date.today().isoformat()
                    save_crm(crm)
                    st.session_state.crm = crm
                    st.rerun()

                st.caption("📋 Скопируй → Outlook → вставь → отправь → нажми «✅ Отправлено»")

if shown == 0:
    st.info("Нет лидов по выбранным фильтрам.")
