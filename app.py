import streamlit as st
import pandas as pd
import database as db
import auth

st.set_page_config(page_title="AcademicGate", layout="wide")
auth.login_sidebar()

st.title("AcademicGate Dashboard")
st.markdown("Welcome to the AcademicGate Management Console.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Jobs", db.execute_one("SELECT COUNT(*) AS n FROM Positions")["n"])
with col2:
    st.metric("Active Employers", db.execute_one("SELECT COUNT(*) AS n FROM University WHERE Status=1")["n"])
with col3:
    st.metric("Total Applications", db.execute_one("SELECT COUNT(*) AS n FROM Applications")["n"])

st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Job Postings Trend (Last 30 Days)")
    trend = db.execute_query("SELECT DATE(DateofPost) AS post_date, COUNT(*) AS postings FROM Positions WHERE DateofPost >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) GROUP BY DATE(DateofPost) ORDER BY post_date")
    if trend:
        df_trend = pd.DataFrame(trend)
        df_trend.set_index("post_date", inplace=True)
        st.line_chart(df_trend)

with col_b:
    st.subheader("Application Funnel")
    funnel = db.execute_query("SELECT Status, COUNT(*) AS count FROM Applications GROUP BY Status ORDER BY FIELD(Status, 'Pending','Reviewed','Shortlisted','Accepted','Rejected')")
    if funnel:
        df_funnel = pd.DataFrame(funnel)
        df_funnel.set_index("Status", inplace=True)
        st.bar_chart(df_funnel)
