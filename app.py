import streamlit as st

st.set_page_config(
    page_title="Zement AI Tools",
    page_icon="🏗",
    layout="wide",
)

contract_page = st.Page(
    "pages/1_contract_auditor.py",
    title="Contract Auditor",
    icon="🔍",
    default=True,
)
leads_page = st.Page(
    "pages/2_Lead_Scoring.py",
    title="Lead Scoring",
    icon="🏗",
)
crm_page = st.Page(
    "pages/3_CRM_Analysis.py",
    title="CRM Analysis",
    icon="📊",
)
outreach_page = st.Page(
    "pages/4_Outreach.py",
    title="CRM",
    icon="📨",
)

pg = st.navigation([contract_page, leads_page, crm_page, outreach_page])
pg.run()
