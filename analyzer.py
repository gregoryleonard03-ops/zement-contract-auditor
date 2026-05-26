import json
import os
import time
import io

import anthropic
import pdfplumber
from docx import Document

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

MAX_CHARS = 18000
OVERLAP = 500


def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()

    if name.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ValueError(
                "PDF appears to be scanned (image-only). "
                "Please use a text-based PDF."
            )
        return text

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace").strip()

    raise ValueError(f"Unsupported file type: {uploaded_file.name}")


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _call_claude(chunk: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=chunk)}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if Claude added them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def merge_red_flags(flags_per_chunk: list) -> list:
    seen_titles = set()
    merged = []
    for flags in flags_per_chunk:
        for flag in flags:
            key = flag.get("title", "").lower().strip()
            if key not in seen_titles:
                seen_titles.add(key)
                merged.append(flag)
    return merged


def compute_score(red_flags: list) -> int:
    score = 85
    severity_map = {"high": -20, "medium": -10, "low": -5}
    counts = {"high": 0, "medium": 0, "low": 0}
    for flag in red_flags:
        sev = flag.get("severity", "low").lower()
        if counts.get(sev, 0) < 3:
            score += severity_map.get(sev, -5)
            counts[sev] = counts.get(sev, 0) + 1
    return max(5, min(95, score))


def compute_tier(score: int) -> tuple:
    if score >= 75:
        return "Low Risk", "SIGN"
    if score >= 50:
        return "Medium Risk", "SIGN WITH REVISIONS"
    return "High Risk", "DO NOT SIGN"


def analyze_contract(text: str) -> dict:
    chunks = chunk_text(text)
    all_flags = []
    last_summary = ""
    last_verdict = "SIGN"

    for i, chunk in enumerate(chunks):
        try:
            result = _call_claude(chunk)
        except (json.JSONDecodeError, Exception):
            result = {
                "red_flags": [],
                "summary": "Analysis failed for this section — please retry.",
                "signing_verdict": "SIGN",
            }
        all_flags.append(result.get("red_flags", []))
        last_summary = result.get("summary", "")
        last_verdict = result.get("signing_verdict", "SIGN")
        if i < len(chunks) - 1:
            time.sleep(0.5)

    red_flags = merge_red_flags(all_flags)
    score = compute_score(red_flags)
    tier, verdict = compute_tier(score)

    # Verdict from Claude takes precedence only if stricter
    verdict_rank = {"SIGN": 0, "SIGN WITH REVISIONS": 1, "DO NOT SIGN": 2}
    computed_rank = verdict_rank.get(verdict, 0)
    claude_rank = verdict_rank.get(last_verdict, 0)
    final_verdict = verdict if computed_rank >= claude_rank else last_verdict

    return {
        "score": score,
        "tier": tier,
        "verdict": final_verdict,
        "red_flags": red_flags,
        "summary": last_summary,
    }
