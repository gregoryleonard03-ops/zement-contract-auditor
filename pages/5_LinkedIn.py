import os
import anthropic
import streamlit as st

st.set_page_config(page_title="LinkedIn Outreach", page_icon="💼", layout="wide")

SYSTEM_PROMPT = """You are writing LinkedIn outreach messages for Zement Stone — a Colorado-based manufacturer of manufactured stone veneer.

Key differentiators:
- Expanded shale (higher-than-industry-required PSI compressive strength, no specific numbers)
- Stone-to-stone coverage: 100 sq. ft. ordered = 100 sq. ft. received
- Custom colors for branded commercial projects
- Local Colorado manufacturer = fast turnaround, reliable logistics

Target audience: General Contractors, real estate developers, architects on commercial projects ($5M+).

Rules:
- B2B professional tone, no fluff
- Always reference the specific project or company
- Offer: samples, quick call, or catalog
- No emoji, no exclamation marks
- Sender: Lev Shumov, Sales Representative, Zement Stone

Output format — return valid JSON only, nothing else:
{"dm": "...", "connection": "..."}

dm — max 300 characters (LinkedIn cold DM limit)
connection — max 200 characters (LinkedIn connection request note)"""


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


def generate_messages(name: str, company: str, role: str, project: str, city: str, budget: str) -> dict:
    api_key = _get_api_key()
    if not api_key:
        return {"dm": "ANTHROPIC_API_KEY not configured.", "connection": ""}

    user_prompt = f"""Generate two LinkedIn messages for:
Contact: {name or 'the contact'} ({role}) at {company}
Project: {project}, {city}
{f'Budget: {budget}' if budget else ''}

DM: max 300 characters. Reference the project. Offer samples or a quick call.
Connection note: max 200 characters. Reference the project briefly.

Return JSON only."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        import json
        text = response.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        return {
            "dm": data.get("dm", ""),
            "connection": data.get("connection", ""),
        }
    except Exception as e:
        return {"dm": f"Error: {e}", "connection": ""}


# ── UI ──────────────────────────────────────────────────────────────────────

st.title("💼 LinkedIn Outreach Generator")
st.caption("AI генерирует персонализированное сообщение — ты отправляешь вручную.")

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Данные лида")
    name = st.text_input("Имя контакта", placeholder="Matt", help="Опционально")
    company = st.text_input("Компания *", placeholder="Kroenke Sports & Entertainment")
    role = st.selectbox("Роль", ["GC", "Developer", "Architect", "Owner", "Other"])
    project = st.text_input("Проект *", placeholder="Ball Arena Hotel, Denver CO")
    city = st.text_input("Город", placeholder="Denver")
    budget = st.text_input("Бюджет", placeholder="$31M", help="Опционально")

    ready = bool(company.strip() and project.strip())
    generate_btn = st.button("✍️ Сгенерировать", type="primary", disabled=not ready)
    if not ready:
        st.caption("Заполни Компания и Проект чтобы продолжить.")

with right:
    st.subheader("Результат")

    if generate_btn:
        with st.spinner("Генерирую..."):
            result = generate_messages(name, company, role, project, city, budget)
        st.session_state["linkedin_result"] = result

    res = st.session_state.get("linkedin_result")

    if res:
        dm = res.get("dm", "")
        conn = res.get("connection", "")

        st.markdown("**DM-сообщение** (холодный запрос, ≤300 символов)")
        dm_chars = len(dm)
        dm_color = "green" if dm_chars <= 300 else "red"
        st.markdown(f":{dm_color}[{dm_chars} / 300 символов]")
        st.code(dm, language=None)

        st.divider()

        st.markdown("**Connection Request** (запрос на связь, ≤200 символов)")
        conn_chars = len(conn)
        conn_color = "green" if conn_chars <= 200 else "red"
        st.markdown(f":{conn_color}[{conn_chars} / 200 символов]")
        st.code(conn, language=None)

        st.divider()
        st.info(
            f"**Как использовать:** найди **{name or company}** в LinkedIn → "
            "отправь DM или запрос на связь → вставь нужный текст."
        )
    else:
        st.markdown("_Заполни форму слева и нажми «Сгенерировать»_")
