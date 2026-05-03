import streamlit as st

def login_sidebar():
    # Khởi tạo session state nếu chưa có
    if "logged_in_role" not in st.session_state:
        st.session_state.logged_in_role = None
        st.session_state.role = None

    with st.sidebar:
        st.markdown("### Authentication")
        
        # Trạng thái CHƯA đăng nhập
        if st.session_state.logged_in_role is None:
            st.info("Please log in to continue.")
            selected_role = st.selectbox(
                "Select your role:", 
                ["Admin", "Employer", "Applicant"]
            )
            if st.button("Login", type="primary", use_container_width=True):
                st.session_state.logged_in_role = selected_role
                st.session_state.role = selected_role
                st.rerun()
                
        # Logged-in state
        else:
            role = st.session_state.logged_in_role
            if role == "Admin":
                st.success(f"Welcome, **{role}**\n\n*Access: ALL PRIVILEGES*")
            elif role == "Employer":
                st.info(f"Welcome, **{role}**\n\n*Access: Post Jobs & Review Applications*")
            else:
                st.warning(f"Welcome, **{role}**\n\n*Access: Browse Jobs & Apply*")
                
            if st.button("Logout", use_container_width=True):
                st.session_state.logged_in_role = None
                st.session_state.role = None
                st.rerun()

    # Block page content if not logged in
    if st.session_state.logged_in_role is None:
        st.error("You are not logged in. Please select a role in the sidebar and click 'Login'.")
        st.stop()
