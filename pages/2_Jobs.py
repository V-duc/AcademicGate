import streamlit as st
import pandas as pd
import database as db
import datetime
import auth
import smart_suggest

st.set_page_config(page_title="Jobs | AcademicGate", layout="wide")
auth.login_sidebar()
st.title("Job Postings")

tab1, tab2, tab3, tab4 = st.tabs(["Job List", "Post a Job", "Apply for Job", "Smart Suggest"])

with tab1:
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search = st.text_input("Search Jobs")
    with col2:
        page_size = st.selectbox("Results per page", [20, 30, 50, 100])
    with col3:
        page = st.number_input("Page", min_value=1, value=1, step=1)
    with col4:
        st.write(" ")
        st.write(" ")
        show_all = st.checkbox("Show Closed Jobs")
        
    jobs = db.list_jobs(
        search=search if search else None, 
        is_alive=None if show_all else 1,
        page=page, 
        page_size=page_size
    )
    
    if jobs and jobs['data']:
        total_pages = jobs['total_pages']
        st.write(f"**Showing page {page} of {total_pages}** (Total: {jobs['total']} jobs)")
        
        df = pd.DataFrame(jobs['data'])
        # Điều chỉnh số thứ tự index để nối tiếp các trang (bắt đầu từ 1)
        start_idx = (page - 1) * page_size + 1
        df.index = range(start_idx, start_idx + len(df))
        
        st.dataframe(df[["JobTitle", "UniversityName", "CountryName", "Deadline", "IsAlive"]], use_container_width=True, height=600)
    else:
        st.info("No jobs found on this page.")

with tab2:
    if st.session_state.role == "Applicant":
        st.warning("Applicants are not allowed to post jobs. This feature is for Employers and Admins only.")
    else:
        with st.form("new_job"):
            st.subheader("Post New Job")
            univ_id = st.text_input("University ID")
            pos_id = st.text_input("Position Type ID (e.g. PHD, POSTDOC)")
            title = st.text_input("Job Title")
            deadline = st.date_input("Deadline", min_value=datetime.date.today())
            
            submit = st.form_submit_button("Post Job")
            if submit and univ_id and pos_id and title:
                try:
                    job_id = db.post_job({
                        "ID_University": univ_id,
                        "ID_Position": pos_id,
                        "ID_Country": "", 
                        "JobTitle": title,
                        "Deadline": deadline.strftime("%Y-%m-%d")
                    })
                    st.success(f"Job posted! ID: {job_id}")
                except Exception as e:
                    st.error(f"Error: {e}")

with tab3:
    if st.session_state.role == "Employer":
        st.warning("Employers cannot apply for jobs.")
    else:
        st.subheader("Apply for a Job")
        
        # Fetch 500 most recent active jobs for suggestions
        active_jobs = db.execute_query("""
            SELECT p.ID, p.JobTitle, u.UniversityName 
            FROM Positions p 
            LEFT JOIN University u ON p.ID_University = u.ID_University 
            WHERE p.IsAlive=1 
            ORDER BY p.DateofPost DESC LIMIT 500
        """)
        
        if active_jobs:
            job_options = {f"{j['JobTitle']} ({j.get('UniversityName', 'N/A')})": j['ID'] for j in active_jobs}
        else:
            job_options = {"No open positions available": ""}

        with st.form("apply_form"):
            selected_job_label = st.selectbox("Select a Job (type to search):", options=list(job_options.keys()))
            applicant_id = st.number_input("Your Applicant ID (e.g. 1, 2, 3)", min_value=1, step=1)
            cover_letter = st.text_area("Cover Letter")
            submit_apply = st.form_submit_button("Submit Application")
            
            if submit_apply:
                job_id_apply = job_options.get(selected_job_label)
                if not job_id_apply:
                    st.error("Please select a valid job.")
                elif not applicant_id:
                    st.error("Please enter your Applicant ID.")
                else:
                    try:
                        db.apply_for_job(job_id_apply, applicant_id, cover_letter)
                        st.success(f"Application submitted successfully for: {selected_job_label}!")
                    except Exception as e:
                        st.error(f"Error: {e}")

with tab4:
    if st.session_state.role == "Employer":
        st.warning("Employers cannot use the job recommendation feature. This is for Applicants only.")
    else:
        st.subheader("AI-Powered Job Recommendations (Semantic Search)")
        st.markdown(
            "The system uses **Sentence-Transformers** (model `all-MiniLM-L6-v2`) to encode "
            "your profile and thousands of jobs into vectors, then searches by **semantic meaning** "
            "(Cosine Similarity). For example: *'AI'* will match *'Artificial Intelligence'* and *'Machine Learning'*."
        )
        
        col_a, col_b = st.columns([1, 2])
        with col_a:
            rec_app_id = st.number_input("Enter your Applicant ID:", min_value=1, step=1, key="rec_app_id")
            btn_suggest = st.button("Find Matching Jobs", type="primary", use_container_width=True)
            
            st.divider()
            if st.button("Rebuild AI Index", help="Rebuild embeddings when new jobs are added"):
                with st.spinner("Rebuilding index..."):
                    smart_suggest.build_job_index(force=True)
                st.success("Index rebuilt successfully!")
            
        with col_b:
            if btn_suggest:
                # Show applicant info first
                applicant = db.get_applicant(rec_app_id)
                if applicant:
                    st.info(
                        f"**{applicant.get('ApplicantName', 'N/A')}**  \n"
                        f"**Major:** {applicant.get('Major', 'N/A')}  \n"
                        f"**Wanted Job:** {applicant.get('Wanted_Job', 'N/A')}"
                    )
                    
                    with st.spinner("AI is analyzing your profile and matching against thousands of jobs..."):
                        top_jobs = smart_suggest.recommend(rec_app_id, limit=10)
                        
                    if top_jobs:
                        st.success(f"Found {len(top_jobs)} best matching jobs for your profile!")
                        for i, j in enumerate(top_jobs, 1):
                            score_pct = f"{j['score'] * 100:.1f}%"
                            with st.expander(f"Top {i}: {j['JobTitle']} - {j.get('UniversityName', 'N/A')} ({score_pct} match)"):
                                st.write(f"**University:** {j.get('UniversityName', 'N/A')}")
                                st.write(f"**Country:** {j.get('CountryName', 'N/A')}")
                                st.write(f"**Match Score:** {score_pct}")
                                desc = str(j.get('NonHTMLAdvertisement', ''))
                                if desc:
                                    st.markdown(f"**Description:** {desc[:500]}...")
                    else:
                        st.warning("No matching jobs found. Please update your profile.")
                else:
                    st.error(f"Applicant with ID = {rec_app_id} not found.")
