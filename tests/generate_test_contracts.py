"""
Generate 3 synthetic vendor contracts for demo purposes.
Run: python3 tests/generate_test_contracts.py
Requires ANTHROPIC_API_KEY in environment or .env in project root.
"""
import os
import sys
from pathlib import Path

# Load .env from project root (two levels up)
root = Path(__file__).parent.parent.parent.parent
env_file = root / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

OUT_DIR = Path(__file__).parent / "sample_contracts"
OUT_DIR.mkdir(exist_ok=True)

CONTRACTS = [
    {
        "filename": "contract_a_clean.txt",
        "description": "Generate a CLEAN, fair vendor contract (score target: 85+, verdict: SIGN).",
        "instructions": """
Create a shipping/logistics vendor agreement between Zement Stone (buyer) and Colorado Freight LLC (vendor).
Contract is CLEAN and FAIR — no hidden fees, no auto-renewal traps, no harsh penalties.
- Clear pricing: flat rate per shipment, no per-transaction commissions
- 30-day written notice required for termination or renewal
- Scope is specific and well-defined
- Standard net-30 payment terms
- Colorado governing law, standard dispute resolution
- 12-month initial term, mutual renewal option
""",
    },
    {
        "filename": "contract_b_medium.txt",
        "description": "Generate a MEDIUM RISK contract (score target: 55-70, verdict: SIGN WITH REVISIONS).",
        "instructions": """
Create a marketing agency services agreement between Zement Stone (buyer) and RockSolid Marketing Inc (vendor).
Contract has 2-3 MEDIUM issues — yellow flags that need revision but not dealbreakers.
Include these issues naturally in the contract text:
1. Auto-renewal with only 10-day written notice (instead of standard 30+)
2. Vague scope: "and other marketing services as determined by vendor from time to time"
3. Price increase clause: "Vendor may adjust rates annually up to 15% at its discretion"
- Payment: $4,500/month retainer
- 12-month term
- Colorado governing law
""",
    },
    {
        "filename": "contract_c_toxic.txt",
        "description": "Generate a HIGH RISK, TOXIC contract (score target: <40, verdict: DO NOT SIGN).",
        "instructions": """
Create a payment processing / software subscription agreement between Zement Stone (buyer) and QuickPay Solutions (vendor).
Contract is TOXIC — contains multiple serious red flags, including the famous $1,500 per-transaction fee.
Include these issues naturally buried in the contract text:
1. Section 4.3: Processing fee of $1,500.00 per transaction processed through the platform
2. Auto-renewal: contract renews automatically unless cancelled with 5-day notice (barely readable)
3. Early termination: 75% of remaining contract value as termination penalty
4. Unilateral changes: "Vendor reserves the right to modify any term of this agreement with 24-hour notice"
5. Mandatory arbitration in Delaware, buyer waives right to jury trial
- Monthly base fee: $299/month
- 24-month term
- Make the $1500/transaction fee subtle but present — easy to miss on first read
""",
    },
]


def generate_contract(contract_def: dict) -> str:
    print(f"  Generating: {contract_def['filename']}...")
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1500,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{contract_def['description']}\n\n"
                    f"Instructions:\n{contract_def['instructions']}\n\n"
                    "Format: Plain text only. Realistic legal contract language. "
                    "No JSON, no markdown, no explanations outside the contract itself."
                ),
            }
        ],
    )
    return response.content[0].text.strip()


def main():
    print("Generating 3 sample contracts...\n")
    for contract_def in CONTRACTS:
        try:
            text = generate_contract(contract_def)
            out_path = OUT_DIR / contract_def["filename"]
            out_path.write_text(text, encoding="utf-8")
            print(f"  Saved: {out_path} ({len(text)} chars)")
        except Exception as e:
            print(f"  ERROR generating {contract_def['filename']}: {e}", file=sys.stderr)
    print("\nDone. Sample contracts saved to tests/sample_contracts/")


if __name__ == "__main__":
    main()
