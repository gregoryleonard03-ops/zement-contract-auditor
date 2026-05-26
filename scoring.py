import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

# ── Scoring weights (1-100 scale) ──────────────────────────────────────────────
BASE_SCORE = 40

PROJECT_TYPE_SCORE = {"commercial": 15, "residential": -20}

# (threshold, points). Falls through to first match. "no value" handled separately (0 pts).
VALUE_THRESHOLDS = [
    (10_000_000, 25),
    (3_000_000,  18),
    (1_000_000,  10),
    (500_000,     3),
    (0,         -15),
]

WORK_TYPE_SCORE = {
    "new construction":    12,
    "renovation":           3,
    "tenant improvement":  -8,
    "addition":            -5,
}

# Only the highest matching keyword score is applied
KEYWORD_SCORE = {
    "hotel": 20, "motel": 20, "inn": 20, "hospitality": 20, "resort": 20,
    "retail": 12, "restaurant": 12, "grocery": 12, "shopping": 12,
    "apartment": 12, "multifamily": 12, "multi-family": 12, "mixed-use": 12,
    "senior living": 12, "assisted living": 12, "office": 12, "warehouse": 12,
    "single family": -25, "sfr": -25, "single-family": -25, "residential": -15,
}

# Icons used in the Score breakdown UI
KEYWORD_ICONS = {
    "hotel": "🏨", "motel": "🏨", "inn": "🏨", "hospitality": "🏨", "resort": "🏨",
    "retail": "🛍", "restaurant": "🛍", "grocery": "🛍", "shopping": "🛍",
    "apartment": "🏢", "multifamily": "🏢", "multi-family": "🏢", "mixed-use": "🏢",
    "senior living": "🏢", "assisted living": "🏢",
    "office": "🏬", "warehouse": "🏭",
    "single family": "🏠", "sfr": "🏠", "single-family": "🏠", "residential": "🏠",
}

# ── Outreach templates (English) ───────────────────────────────────────────────
TEMPLATES = {
    "hotel": (
        "Hi {contractor},\n\n"
        "We noticed your project at {address} and wanted to reach out. "
        "Zement Stone specializes in architectural stone veneer for hospitality projects — "
        "with 2,000+ PSI compressive strength and true 100 sq.ft coverage "
        "(no mortar-joint padding like most manufacturers). "
        "We can also match any custom color to your brand standards.\n\n"
        "Would you be open to a free sample kit? Happy to connect at your convenience.\n\n"
        "Best,\nZement Stone | Littleton, CO | 303-993-2737 | zementstone.com"
    ),
    "multifamily": (
        "Hi {contractor},\n\n"
        "We came across your project at {address} and thought we'd introduce ourselves. "
        "Zement Stone supplies manufactured stone veneer to multi-family developers across Colorado — "
        "exact quantities shipped (no overbuying standard pallets), 2,000+ PSI strength "
        "built for freeze-thaw cycles, and local production for fast turnaround.\n\n"
        "We'd love to send you a free sample kit and discuss pricing for your project.\n\n"
        "Best,\nZement Stone | Littleton, CO | 303-993-2737 | zementstone.com"
    ),
    "retail": (
        "Hi {contractor},\n\n"
        "We noticed your upcoming project at {address} — Zement Stone could be a great fit. "
        "We supply manufactured stone veneer to retail and restaurant chains, "
        "with custom color matching for brand consistency and honest square footage "
        "so you only pay for what you need.\n\n"
        "Can we send you a free sample kit?\n\n"
        "Best,\nZement Stone | Littleton, CO | 303-993-2737 | zementstone.com"
    ),
    "commercial": (
        "Hi {contractor},\n\n"
        "We saw your project at {address} and wanted to introduce Zement Stone. "
        "We're a local Colorado manufacturer of architectural stone veneer — "
        "2,000+ PSI strength, 100% honest square footage coverage, "
        "custom colors, and fast lead times since we produce right here in Littleton.\n\n"
        "Happy to send a free sample kit or meet at our showroom.\n\n"
        "Best,\nZement Stone | Littleton, CO | 303-993-2737 | zementstone.com"
    ),
}

# ── Scoring logic ───────────────────────────────────────────────────────────────

def score_permit(row: pd.Series) -> dict:
    score = BASE_SCORE
    breakdown = {"base": BASE_SCORE, "criteria": []}

    project_type = str(row.get("project_type", "")).lower()
    work_type    = str(row.get("work_type", "")).lower()
    description  = str(row.get("description", "")).lower()
    category     = str(row.get("category", "commercial")).lower()
    raw_value    = row.get("estimated_value", 0)
    try:
        value = float(raw_value) if pd.notna(raw_value) else 0.0
    except (TypeError, ValueError):
        value = 0.0
    contractor   = str(row.get("contractor_name", "")) or "Project Team"
    address      = str(row.get("address", "your location"))

    # 1. Project Type
    pts, found, matched = 0, "Not specified", False
    if project_type and project_type != "nan":
        matched = True
        for key, p in PROJECT_TYPE_SCORE.items():
            if key in project_type:
                pts = p
                found = key.title()
                break
        else:
            found = project_type.title()
    score += pts
    breakdown["criteria"].append({
        "key": "project_type", "label": "Project Type", "icon": "🏗",
        "found": found, "points": pts, "matched": matched,
    })

    # 2. Estimated Value
    pts, found, matched = 0, "Not disclosed", False
    if value > 0:
        matched = True
        found = f"${value:,.0f}"
        for threshold, p in VALUE_THRESHOLDS:
            if value >= threshold:
                pts = p
                break
    score += pts
    breakdown["criteria"].append({
        "key": "estimated_value", "label": "Estimated Value", "icon": "💰",
        "found": found, "points": pts, "matched": matched,
    })

    # 3. Work Type
    pts, found, matched = 0, "Not specified", False
    if work_type and work_type != "nan":
        matched = True
        for key, p in WORK_TYPE_SCORE.items():
            if key in work_type:
                pts = p
                found = key.title()
                break
        else:
            found = work_type.title()
    score += pts
    breakdown["criteria"].append({
        "key": "work_type", "label": "Work Type", "icon": "🔨",
        "found": found, "points": pts, "matched": matched,
    })

    # 4. Property Use Keywords (max of all matches)
    pts, found, matched, icon = 0, "No relevant keywords", False, "🏷"
    kw_hits = [(kw, p) for kw, p in KEYWORD_SCORE.items() if kw in description]
    if kw_hits:
        matched = True
        best_kw, pts = max(kw_hits, key=lambda x: x[1])
        found = best_kw.title()
        icon = KEYWORD_ICONS.get(best_kw, "🏷")
    score += pts
    breakdown["criteria"].append({
        "key": "keywords", "label": "Property Use Keywords", "icon": icon,
        "found": found, "points": pts, "matched": matched,
    })

    raw_score   = score
    final_score = max(1, min(100, score))
    breakdown["raw_score"]   = raw_score
    breakdown["final_score"] = final_score
    breakdown["clamped"]     = raw_score != final_score

    if final_score >= 75:
        tier   = "Hot"
        action = "Call today"
    elif final_score >= 55:
        tier   = "Warm"
        action = "Email this week"
    else:
        tier   = "Cold"
        action = "Skip"

    # reason (legacy textual summary, still used in card-meta)
    parts = []
    if "commercial" in project_type: parts.append("commercial project")
    if value >= 10_000_000:  parts.append(f"large budget ${value/1_000_000:.1f}M")
    elif value >= 3_000_000: parts.append(f"budget ${value/1_000_000:.1f}M")
    elif value >= 1_000_000: parts.append(f"budget ${value/1_000_000:.1f}M")
    elif value > 0:          parts.append(f"budget ${value:,.0f}")
    if "new construction" in work_type: parts.append("new construction")
    if category == "hotel":       parts.append("hotel — high stone demand")
    elif category == "multifamily": parts.append("multifamily — high volume")
    elif category == "retail":    parts.append("retail/restaurant — facade cladding")
    if "residential" in project_type or "single family" in description:
        parts.append("residential (low priority)")
    reason = ", ".join(parts) or "standard project"

    tpl_key = category if category in TEMPLATES else "commercial"
    outreach = TEMPLATES[tpl_key].format(contractor=contractor, address=address)

    return {"score": final_score, "tier": tier, "action": action,
            "reason": reason, "outreach": outreach,
            "breakdown": json.dumps(breakdown, ensure_ascii=False)}

# ── Main ────────────────────────────────────────────────────────────────────────

def process_permits(input_path: str, output_path: str):
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} records\n")

    results = []
    for _, row in df.iterrows():
        result = score_permit(row)
        result.update({
            "permit_id":       row.get("permit_id", ""),
            "address":         row.get("address", ""),
            "project_type":    row.get("project_type", ""),
            "estimated_value": row.get("estimated_value", 0),
            "description":     str(row.get("description", ""))[:150],
            "contractor_name": row.get("contractor_name", ""),
            "issue_date":      row.get("issue_date", ""),
            "category":        row.get("category", ""),
            "work_type":       row.get("work_type", ""),
            "source":          row.get("source", ""),
            "city":            row.get("city", ""),
        })
        results.append(result)

    out = pd.DataFrame(results).sort_values("score", ascending=False)
    out.to_csv(output_path, index=False)

    hot  = out[out["tier"] == "Hot"]
    warm = out[out["tier"] == "Warm"]
    cold = out[out["tier"] == "Cold"]

    print("=" * 65)
    print(f"  RESULTS: {len(hot)} Hot 🔥  |  {len(warm)} Warm 🟡  |  {len(cold)} Cold ❄️")
    print(f"  Saved: {output_path}")
    print("=" * 65)
    print("\n🔥 TOP HOT LEADS:\n")
    for _, lead in hot.head(5).iterrows():
        print(f"  [{lead['score']}/100] {lead['address']}  —  ${float(lead['estimated_value']):,.0f}")
        print(f"  Reason: {lead['reason']}")
        print(f"  Action: {lead['action']}\n")

if __name__ == "__main__":
    base = Path(__file__).parent
    combined  = base / "data" / "colorado_combined.csv"
    fallback  = base / "data" / "permits_clean.csv"
    if combined.exists():
        input_csv  = combined
        output_csv = base / "data" / f"scored_colorado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    else:
        input_csv  = fallback
        output_csv = base / "data" / f"scored_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    process_permits(str(input_csv), str(output_csv))
