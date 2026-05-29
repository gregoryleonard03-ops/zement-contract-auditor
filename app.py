import streamlit as st

st.set_page_config(
    page_title="Zement AI Tools",
    page_icon="🏗",
    layout="wide",
)

outreach_page = st.Page(
    "pages/4_Outreach.py",
    title="CRM",
    icon="📨",
    default=True,
)
leads_page = st.Page(
    "pages/2_Lead_Scoring.py",
    title="Lead Scoring",
    icon="🏗",
)
linkedin_page = st.Page(
    "pages/5_LinkedIn.py",
    title="LinkedIn",
    icon="💼",
)
crm_page = st.Page(
    "pages/3_CRM_Analysis.py",
    title="CRM Analysis",
    icon="📊",
)
contract_page = st.Page(
    "pages/1_contract_auditor.py",
    title="Contract Auditor",
    icon="🔍",
)

pg = st.navigation([outreach_page, leads_page, linkedin_page, crm_page, contract_page])
pg.run()
