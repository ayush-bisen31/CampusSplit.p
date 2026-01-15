"""
Authentication Module
Handles login, logout, and user validation
"""

import streamlit as st
import re
from database import get_db_connection, hash_password


# --- Input Validation ---
def validate_email(email):
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password, min_length=6):
    """Validate password strength."""
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"
    return True, "Valid"


# --- Authentication Functions ---
def authenticate_user(username, password, user_type):
    """
    Authenticate a user by checking credentials.
    
    Args:
        username: Username or Student ID
        password: User password
        user_type: 'student' or 'staff' (teacher/admin)
    
    Returns:
        User dict if authenticated, None otherwise
    """
    with get_db_connection() as conn:
        if conn is None:
            return None
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            if user_type == "student":
                cursor.execute(
                    "SELECT * FROM students WHERE student_id = %s AND password = %s",
                    (username, hash_password(password))
                )
            else:  # teacher or admin
                cursor.execute(
                    "SELECT * FROM teachers WHERE username = %s AND password = %s",
                    (username, hash_password(password))
                )
            
            user = cursor.fetchone()
            cursor.close()
            return user
        
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None


def login_page():
    """Display the main login interface."""
    st.title("🎓 Campus Management System")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["👨‍🎓 Student Login", "👨‍🏫 Staff Login"])

    # --- Student Login Tab ---
    with tab1:
        with st.form("student_login"):
            st.write("**Enter your credentials to login**")
            username = st.text_input(
                "Student ID",
                placeholder="e.g., STU001",
                key="student_id_input"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="student_pwd_input"
            )
            submitted = st.form_submit_button("🔓 Login", type="primary")

            if submitted:
                if not username or not password:
                    st.error("❌ Please enter both Student ID and Password")
                else:
                    student = authenticate_user(username, password, "student")
                    if student:
                        st.session_state.logged_in = True
                        st.session_state.user_type = "student"
                        st.session_state.current_user = student
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Student ID or Password")

    # --- Staff Login Tab ---
    with tab2:
        with st.form("staff_login"):
            st.write("**Teacher/Admin Login**")
            username = st.text_input(
                "Username",
                placeholder="e.g., admin",
                key="staff_username_input"
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                key="staff_pwd_input"
            )
            submitted = st.form_submit_button("🔓 Login", type="primary")

            if submitted:
                if not username or not password:
                    st.error("❌ Please enter both Username and Password")
                else:
                    staff_user = authenticate_user(username, password, "staff")
                    if staff_user:
                        st.session_state.logged_in = True
                        st.session_state.user_type = staff_user['role']
                        st.session_state.current_user = staff_user
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Username or Password")

    # --- Demo Credentials Section ---
    st.markdown("---")
    with st.expander("ℹ️ Demo Credentials"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**👑 Admin Access**")
            st.code("Username: admin\nPassword: admin123", language="text")
        
        with col2:
            st.write("**📌 Note**")
            st.info("Use these credentials to explore the system.")


def logout():
    """Clear session state to log the user out."""
    st.session_state.logged_in = False
    st.session_state.user_type = None
    st.session_state.current_user = None
    st.success("✅ You have been logged out successfully")
    st.rerun()
