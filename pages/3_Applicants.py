import streamlit as st
import pandas as pd
import database as db
import auth

st.set_page_config(page_title="Applicants | AcademicGate", layout="wide")
auth.login_sidebar()

if st.session_state.role == "Applicant":
    st.error("Access denied. Only Admins and Employers can view the applicant list.")
    st.stop()

st.title("Applicants")

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    search = st.text_input("Search by Name or Email")
with col2:
    page_size = st.selectbox("Results per page", [20, 30, 50, 100])
with col3:
    page = st.number_input("Page", min_value=1, value=1, step=1)

applicants = db.list_applicants(search=search if search else None, page=page, page_size=page_size)

if applicants and applicants['data']:
    total_pages = applicants['total_pages']
    st.write(f"**Showing page {page} of {total_pages}** (Total: {applicants['total']} applicants)")
    
    df = pd.DataFrame(applicants['data'])
    # Điều chỉnh số thứ tự index
    start_idx = (page - 1) * page_size + 1
    df.index = range(start_idx, start_idx + len(df))
    
    display_cols = ["ApplicantID", "ApplicantName", "Age", "Gender", "Nationality", "Major", "Wanted_Job", "Email"]
    cols_to_show = [c for c in display_cols if c in df.columns] + [c for c in df.columns if c not in display_cols and c not in ["CVLink", "RegisteredAt", "IsActive", "PhoneNumber"]]
    st.dataframe(df[cols_to_show], use_container_width=True, height=600)
else:
    st.info("No applicants found on this page.")
