EMAIL_BODY = """Hi {company},

We came across your project at {address} and wanted to introduce ourselves.

Zement Stone is a true Colorado local manufacturer specializing in manufactured stone veneer, natural stone veneer, and thin brick veneer for residential, multifamily, and commercial projects throughout Colorado.

A few things that set us apart:
- Local Colorado manufacturing with faster lead times and dependable availability
- Higher-than-industry-required PSI compressive strength designed to withstand Colorado freeze/thaw conditions
- Custom color and texture matching capabilities
- Full range of installation materials available

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

You can browse our product catalog and brochures here: https://drive.google.com/drive/folders/1If47SDCzq3XyItOzYU8VJ2IYrrLz_b70?usp=share_link

We'd love to get samples in front of your team. Thank you for your time. We look forward to the opportunity to work together."""

EMAIL_SUBJECT = "{company} — {city} project"


def generate_email(lead: dict, portfolio_link: str = "") -> dict:
    """Generate outreach email for a lead.

    lead dict keys: company, address, city (+ any others, ignored)
    Returns: {"subject": str, "body": str}
    """
    company = lead.get("company") or lead.get("contractor_name", "your company")
    address = lead.get("address", "")
    city = lead.get("city", "Colorado")

    return {
        "subject": EMAIL_SUBJECT.format(company=company, city=city),
        "body": EMAIL_BODY.format(company=company, address=address),
    }


if __name__ == "__main__":
    test_leads = [
        {"company": "The Weitz Company", "address": "3875 Walnut ST, Denver, CO", "city": "Denver"},
        {"company": "Wood Partners", "address": "Alta Longmont, Longmont CO", "city": "Longmont"},
        {"company": "Colarelli Construction", "address": "CityROCK Athletic Facility, Colorado Springs CO", "city": "Colorado Springs"},
    ]
    for lead in test_leads:
        result = generate_email(lead)
        print("Subject:", result["subject"])
        print()
        print(result["body"])
        print("\n" + "="*60 + "\n")
