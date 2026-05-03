import streamlit as st
import pandas as pd
import database as db
import auth

st.set_page_config(page_title="Applications | AcademicGate", layout="wide")
auth.login_sidebar()
st.title("Applications")

tab1, tab2 = st.tabs(["List Applications", "Update Status"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        page_size = st.selectbox("Results per page", [20, 30, 50, 100])
    with col2:
        page = st.number_input("Page", min_value=1, value=1, step=1)
        
    apps = db.list_applications(page=page, page_size=page_size)
    
    if apps and apps['data']:
        total_pages = apps['total_pages']
        st.write(f"**Showing page {page} of {total_pages}** (Total: {apps['total']} applications)")
        
        df = pd.DataFrame(apps['data'])
        # Điều chỉnh số thứ tự index
        start_idx = (page - 1) * page_size + 1
        df.index = range(start_idx, start_idx + len(df))
        
        st.dataframe(df[["ApplicationID", "JobTitle", "ApplicantName", "ApplyDate", "Status"]], use_container_width=True, height=600)
    else:
        st.info("No applications found on this page.")

with tab2:
    if st.session_state.role == "Applicant":
        st.warning("Applicants are not allowed to modify application status.")
    else:
        st.subheader("Update Application Status")
        app_id = st.number_input("Application ID", min_value=1, step=1)
        new_status = st.selectbox("New Status", ["Pending", "Reviewed", "Shortlisted", "Rejected", "Accepted"])
        
        if st.button("Update Status"):
            try:
                db.update_status(app_id, new_status)
                st.success("Status updated successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
