import streamlit as st
import pandas as pd
import database as db
import auth

st.set_page_config(page_title="Employers | AcademicGate", layout="wide")
auth.login_sidebar()

if st.session_state.role == "Applicant":
    st.error("Access denied. Applicants are not allowed to view Employer management.")
    st.stop()

st.title("Employer Management")

tab1, tab2 = st.tabs(["List Employers", "Add New Employer"])

with tab1:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("Search Employers by Name or ID")
    with col2:
        page_size = st.selectbox("Results per page", [20, 30, 50, 100])
    with col3:
        page = st.number_input("Page", min_value=1, value=1, step=1)
        
    query = "SELECT ID_University, UniversityName, ShortName, ID_Country, Status, NumberofRecentPositions FROM University"
    count_query = "SELECT COUNT(*) as total FROM University"
    params = []
    
    if search:
        where_clause = " WHERE UniversityName LIKE %s OR ID_University LIKE %s"
        query += where_clause
        count_query += where_clause
        params = [f"%{search}%", f"%{search}%"]
    
    total_employers = db.execute_one(count_query, params)["total"]
    total_pages = max(1, (total_employers + page_size - 1) // page_size)
    
    query += " ORDER BY NumberofRecentPositions DESC LIMIT %s OFFSET %s"
    params.extend([page_size, (page - 1) * page_size])
    
    st.write(f"**Showing page {page} of {total_pages}** (Total: {total_employers} employers)")
    
    employers = db.execute_query(query, params)
    if employers:
        df = pd.DataFrame(employers)
        # Điều chỉnh số thứ tự index
        start_idx = (page - 1) * page_size + 1
        df.index = range(start_idx, start_idx + len(df))
        
        st.dataframe(df, use_container_width=True, height=600)
    else:
        st.info("No employers found on this page.")

with tab2:
    with st.form("new_employer"):
        st.subheader("Add Employer")
        uid = st.text_input("University ID (max 20 chars)")
        name = st.text_input("University Name")
        country = st.text_input("Country ID (e.g. USA, GBR)")
        submit = st.form_submit_button("Save")
        
        if submit and uid and name and country:
            try:
                db.execute_write("INSERT INTO University (ID_University, UniversityName, ID_Country, Status, NumberofRecentPositions) VALUES (%s, %s, %s, 1, 0)", (uid, name, country))
                st.success(f"Added {name} successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
