import os
import anthropic

SYSTEM_PROMPT = """You are an outreach email writer for Zement Stone, a Colorado-based stone veneer manufacturer.

Your job: write a personalized cold outreach email to a construction professional based on their permit data.

Rules:
- Sender is always Anastasia Shumova, Sales Representative, Zement Stone, sales@zementstone.com
- Follow the approved template structure exactly (shown below)
- Include the full showroom block and catalog link verbatim — do not paraphrase or shorten them
- Select 2–4 differentiator bullets appropriate for the project type
- No specific PSI numbers. You may say "higher-than-industry-required PSI compressive strength"
- No fluff, no "I hope this email finds you well"
- Subject line: lowercase, no emoji, references project name or city
- Body length: 120–200 words
- Output: subject line on first line, then blank line, then email body. No extra commentary.

Approved template structure:

Hi {first_name},

[Opening: we came across the {project_name} project near/in {city} and wanted to reach out while you're still in planning/pre-construction.]

[Company intro: Zement Stone is a true Colorado local manufacturer specializing in manufactured stone veneer, natural stone veneer, and thin brick veneer for residential, multifamily, and commercial projects throughout Colorado.]

A few things that set us apart:

[2–4 bullet points relevant to project type — see differentiators below]

Product catalog: https://drive.google.com/drive/folders/1If47SDCzq3XyItOzYU8VJ2IYrrLz_b70?usp=share_link

We currently have two convenient showroom and supply locations:

Zement Stone
7241 W. Titan Rd, Littleton, CO 80125
Main Line: 303-993-2737 | www.zementstone.com
Sales: Rich Dubois – 720-737-5695

ProBuro Supply, LLC
4935 York St, Denver, CO 80216
Main Line: 720-438-2185 | www.proburosupply.com
Sales: Art Pushkarev – 720-607-1758 | Tim Felecos – 720-822-3321

We also work with a network of trusted masonry and stucco installation partners and are happy to provide recommendations upon request.

We'd love to get samples in front of your team. Thank you for your time. We look forward to the opportunity to work together.

Anastasia Shumova
Sales Representative, Zement Stone
sales@zementstone.com

Differentiators by project type:

Hotel / Hospitality:
- Freeze/thaw durability (higher-than-industry-required PSI compressive strength)
- Custom color and texture matching for branded hospitality projects
- Stone-to-stone coverage: 100 sq. ft. ordered = 100 sq. ft. received
- Local CO manufacturer = reliable mountain-corridor logistics

Multifamily:
- Stone-to-stone coverage (competitors include mortar joints → ~87 sq. ft. per "100")
- Exact quantity shipping — no standard box sizes, no leftover waste
- Local CO manufacturer = fast turnaround and easy reorders
- Zement Mortar available (preferred by local crews)

Retail / Restaurant chains:
- Custom color matching for branded/tenant requirements
- Full range: manufactured stone, natural stone, thin brick veneer
- Local production = predictable lead times

Mixed-use:
- Single supplier for contrast collections (retail ground floor + residential upper floors)
- Custom color options for each zone
- Local CO manufacturer
"""


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


def generate_email(lead: dict, portfolio_link: str = "") -> dict:
    api_key = _get_api_key()
    if not api_key:
        return _fallback_email(lead)

    first_name = lead.get("first_name") or "there"
    project_name = lead.get("project_name", "")
    city = lead.get("project_city") or lead.get("city", "Colorado")
    state = lead.get("project_state", "")
    project_type = lead.get("project_type", "commercial")
    value = lead.get("project_value") or _format_value(lead.get("estimated_value", ""))
    company = lead.get("company", "")
    phase_note = lead.get("phase_note", "")
    address = lead.get("address", "")

    location = f"{city}, {state}".strip(", ") if state else city

    user_prompt = f"""Write a cold outreach email for this lead:

First name: {first_name}
Company: {company}
Project: {project_name}
Location: {location}
Project type: {project_type}
Estimated value: {value}
{f'Phase: {phase_note}' if phase_note else ''}
{f'Address: {address}' if address else ''}

Follow the template structure exactly. Output subject line on first line, blank line, then email body."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        lines = text.split("\n")
        subject = lines[0].strip()
        body_start = 1
        while body_start < len(lines) and not lines[body_start].strip():
            body_start += 1
        body = "\n".join(lines[body_start:])
        return {"subject": subject, "body": body}
    except Exception as e:
        print(f"[personalizer] Claude API error: {e}, using fallback")
        return _fallback_email(lead)


def _format_value(raw) -> str:
    if not raw:
        return ""
    try:
        num = float(str(raw).replace(",", "").replace("$", ""))
        if num >= 1_000_000:
            return f"${num / 1_000_000:.0f}M"
        if num >= 1_000:
            return f"${num / 1_000:.0f}K"
    except (ValueError, TypeError):
        pass
    return str(raw)


def _fallback_email(lead: dict) -> dict:
    company = lead.get("company") or lead.get("contractor_name", "your company")
    address = lead.get("address", "")
    city = lead.get("project_city") or lead.get("city", "Colorado")

    subject = f"{company} — {city} project"
    body = f"""Hi,

We came across your project{' at ' + address if address else ''} and wanted to introduce ourselves.

Zement Stone is a true Colorado local manufacturer specializing in manufactured stone veneer, natural stone veneer, and thin brick veneer for residential, multifamily, and commercial projects throughout Colorado.

Product catalog: https://drive.google.com/drive/folders/1If47SDCzq3XyItOzYU8VJ2IYrrLz_b70?usp=share_link

Zement Stone
7241 W. Titan Rd, Littleton, CO 80125
Main Line: 303-993-2737 | www.zementstone.com

Anastasia Shumova
Sales Representative, Zement Stone
sales@zementstone.com"""
    return {"subject": subject, "body": body}


if __name__ == "__main__":
    test_lead = {
        "first_name": "Steve",
        "company": "Dakota Pacific Real Estate",
        "project_name": "Kimball Junction West Hotel",
        "project_city": "Park City",
        "project_state": "UT",
        "project_type": "hotel",
        "estimated_value": "19000000",
        "phase_note": "still in planning",
    }
    result = generate_email(test_lead)
    print("Subject:", result["subject"])
    print()
    print(result["body"])
