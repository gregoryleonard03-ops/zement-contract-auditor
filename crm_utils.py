"""Shared CRM helpers. Backend: Google Sheets (with CSV fallback for local dev)."""
import csv
import sys
from datetime import date
from pathlib import Path

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
CRM_FILE = DATA_DIR / "outreach_crm.csv"        # fallback only
SENT_LOG_FILE = DATA_DIR / "sent_log.csv"

FIELDNAMES = [
    "email", "first_name", "company", "contact_role", "project_type",
    "address", "estimated_value", "city", "tier", "issue_date",
    "source", "project_name", "description",
    "status", "notes", "email_subject", "email_body",
    "added_date", "sent_date", "last_updated",
]

STATUSES = [
    "В очереди",
    "Отправлено",
    "Ответил",
    "Митинг назначен",
    "КП отправлено",
    "Сделка",
    "Отказ",
    "Не актуально",
]

STATUS_ICON = {
    "В очереди":       "🔵",
    "Отправлено":      "📨",
    "Ответил":         "💬",
    "Митинг назначен": "📅",
    "КП отправлено":   "📋",
    "Сделка":          "✅",
    "Отказ":           "❌",
    "Не актуально":    "⚪",
}

# ── Google Sheets connection ───────────────────────────────────────────────────

def _get_sheet():
    """Return gspread Worksheet. Raises RuntimeError if not configured."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = None

    # 1) Streamlit secrets (production)
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
    except Exception:
        pass

    # 2) Local JSON file (dev)
    if creds_dict is None:
        local_key = APP_DIR / "service_account.json"
        if local_key.exists():
            import json
            with open(local_key) as f:
                creds_dict = json.load(f)

    if creds_dict is None:
        raise RuntimeError(
            "Google Sheets credentials not found. "
            "Add [gcp_service_account] to Streamlit secrets or place service_account.json in the app directory."
        )

    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    # Sheet ID from secrets or env
    sheet_id = None
    try:
        import streamlit as st
        sheet_id = st.secrets.get("GOOGLE_SHEET_ID") or st.secrets.get("gsheet", {}).get("sheet_id")
    except Exception:
        pass
    if not sheet_id:
        import os
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError(
            "GOOGLE_SHEET_ID not set. Add it to Streamlit secrets or .env."
        )

    spreadsheet = client.open_by_key(sheet_id)
    try:
        worksheet = spreadsheet.worksheet("CRM")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="CRM", rows=1000, cols=len(FIELDNAMES))
        worksheet.append_row(FIELDNAMES)
    return worksheet


def _use_sheets() -> bool:
    """Return True if Google Sheets backend is available."""
    try:
        import gspread  # noqa: F401
        import streamlit as st
        has_secrets = "gcp_service_account" in st.secrets
        has_local = (APP_DIR / "service_account.json").exists()
        return has_secrets or has_local
    except Exception:
        return False


# ── Public API ─────────────────────────────────────────────────────────────────

def load_crm() -> dict:
    """Return dict keyed by email (lowercase)."""
    if _use_sheets():
        return _load_from_sheets()
    return _load_from_csv()


def save_crm(crm: dict):
    if _use_sheets():
        _save_to_sheets(crm)
    else:
        _save_to_csv(crm)


# ── Google Sheets backend ──────────────────────────────────────────────────────

def _load_from_sheets() -> dict:
    try:
        ws = _get_sheet()
        rows = ws.get_all_records(expected_headers=FIELDNAMES, default_blank="")
        crm = {}
        for row in rows:
            key = str(row.get("email", "")).lower().strip()
            if key:
                crm[key] = {f: str(row.get(f, "")) for f in FIELDNAMES}
        return crm
    except Exception as e:
        import streamlit as st
        st.warning(f"Google Sheets недоступен, работаю с локальным CSV: {e}")
        return _load_from_csv()


def _save_to_sheets(crm: dict):
    try:
        ws = _get_sheet()
        ws.clear()
        ws.append_row(FIELDNAMES)
        rows = [[str(entry.get(f, "")) for f in FIELDNAMES] for entry in crm.values()]
        if rows:
            ws.append_rows(rows, value_input_option="RAW")
    except Exception as e:
        import streamlit as st
        st.warning(f"Не удалось сохранить в Google Sheets: {e}. Сохраняю локально.")
        _save_to_csv(crm)


# ── CSV fallback ───────────────────────────────────────────────────────────────

def _load_from_csv() -> dict:
    if not CRM_FILE.exists():
        return {}
    crm = {}
    with open(CRM_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row.get("email", "").lower().strip()
            if key:
                crm[key] = row
    return crm


def _save_to_csv(crm: dict):
    CRM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CRM_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(crm.values())


# ── Business logic (backend-agnostic) ─────────────────────────────────────────

def generate_email_for_lead(lead: dict) -> tuple:
    sys.path.insert(0, str(APP_DIR))
    try:
        from personalizer import generate_email
        result = generate_email(lead)
        return result.get("subject", ""), result.get("body", "")
    except Exception as e:
        return "Zement Stone — stone veneer for your project", f"(Error generating email: {e})"


def add_to_crm(row: dict, crm: dict) -> dict:
    email = str(row.get("email", "")).strip()
    email_key = email.lower()

    lead = {
        "first_name":      row.get("first_name") or row.get("contact_name", ""),
        "company":         row.get("company") or row.get("contractor_name", ""),
        "project_type":    row.get("project_type") or row.get("category", "commercial"),
        "address":         row.get("address", ""),
        "estimated_value": row.get("estimated_value", 0),
        "city":            row.get("city", ""),
        "project_city":    row.get("city", ""),
        "project_state":   row.get("state", "CO"),
        "project_name":    str(row.get("project_name") or row.get("description", ""))[:100],
        "project_value":   str(row.get("estimated_value", "")),
        "phase_note":      row.get("phase_note", ""),
        "issue_date":      row.get("issue_date", ""),
        "description":     str(row.get("description", "")),
    }

    subject, body = generate_email_for_lead(lead)

    crm[email_key] = {
        "email":           email,
        "first_name":      lead["first_name"],
        "company":         lead["company"],
        "contact_role":    row.get("contact_role", "GC"),
        "project_type":    lead["project_type"],
        "address":         lead["address"],
        "estimated_value": str(lead["estimated_value"]),
        "city":            lead["city"],
        "tier":            row.get("tier", ""),
        "issue_date":      lead["issue_date"],
        "source":          str(row.get("source", "")),
        "project_name":    str(row.get("project_name") or row.get("description", ""))[:100],
        "description":     str(row.get("description", ""))[:300],
        "status":          "В очереди",
        "notes":           "",
        "email_subject":   subject,
        "email_body":      body,
        "added_date":      date.today().isoformat(),
        "sent_date":       "",
        "last_updated":    date.today().isoformat(),
    }
    save_crm(crm)
    return crm


def mark_sent(email_key: str, crm: dict) -> dict:
    today = date.today().isoformat()
    if email_key in crm:
        crm[email_key]["status"] = "Отправлено"
        crm[email_key]["sent_date"] = today
        crm[email_key]["last_updated"] = today
        save_crm(crm)
        _append_sent_log(crm[email_key])
    return crm


def _append_sent_log(entry: dict):
    write_header = not SENT_LOG_FILE.exists()
    with open(SENT_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date", "email", "company", "city", "tier", "subject", "status"])
        writer.writerow([
            date.today().isoformat(),
            entry.get("email", ""),
            entry.get("company", ""),
            entry.get("city", ""),
            entry.get("tier", ""),
            entry.get("email_subject", ""),
            "sent",
        ])


def count_sent_today(crm: dict) -> int:
    today = date.today().isoformat()
    return sum(1 for e in crm.values() if e.get("sent_date") == today)
