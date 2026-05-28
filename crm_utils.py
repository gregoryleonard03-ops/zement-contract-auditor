"""Shared CRM helpers used by Lead Scoring and CRM pages."""
import csv
import sys
from datetime import date
from pathlib import Path

# App root (tools/document_analyzer/) — works both locally and on Streamlit Cloud
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
CRM_FILE = DATA_DIR / "outreach_crm.csv"
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
    "В очереди":     "🔵",
    "Отправлено":    "📨",
    "Ответил":       "💬",
    "Митинг назначен": "📅",
    "КП отправлено": "📋",
    "Сделка":        "✅",
    "Отказ":         "❌",
    "Не актуально":  "⚪",
}


def load_crm() -> dict:
    """Return dict keyed by email (lowercase)."""
    if not CRM_FILE.exists():
        return {}
    crm = {}
    with open(CRM_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row.get("email", "").lower().strip()
            if key:
                crm[key] = row
    return crm


def save_crm(crm: dict):
    CRM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CRM_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(crm.values())


def generate_email_for_lead(lead: dict) -> tuple:
    """Generate email subject+body. Returns (subject, body)."""
    sys.path.insert(0, str(APP_DIR))
    try:
        from personalizer import generate_email
        result = generate_email(lead)
        return result.get("subject", ""), result.get("body", "")
    except Exception as e:
        return "Zement Stone — stone veneer for your project", f"(Error generating email: {e})"


def add_to_crm(row: dict, crm: dict) -> dict:
    """Add a lead row to CRM, generate email. Returns updated crm."""
    email = str(row.get("email", "")).strip()
    email_key = email.lower()

    # Build unified lead dict for personalizer
    lead = {
        "first_name":      row.get("first_name") or row.get("contact_name", ""),
        "company":         row.get("company") or row.get("contractor_name", ""),
        "project_type":    row.get("project_type") or row.get("category", "commercial"),
        "address":         row.get("address", ""),
        "estimated_value": row.get("estimated_value", 0),
        "city":            row.get("city", ""),
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
    """Mark lead as sent, append to sent_log.csv."""
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
