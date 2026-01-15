"""
Campus Management System - Main Application Entry Point
Author: Campus Management Team
"""

import streamlit as st
from database import init_database, initialize_default_data
from auth import login_page, logout
from admin_dashboard import admin_dashboard
from teacher_dashboard import teacher_dashboard
from student_dashboard import student_dashboard

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = None


def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(
        page_title="Campus Management System",
        layout="wide",
        page_icon="🎓"
    )

    # Database initialization on first run
    if 'db_initialized' not in st.session_state:
        if init_database():
            initialize_default_data()
            st.session_state.db_initialized = True
        else:
            st.error(
                "❌ DATABASE INITIALIZATION FAILED.\n\n"
                "Please verify:\n"
                "- MySQL server is running\n"
                "- Database credentials in database.py are correct\n"
                "- 'campus_management' database exists"
            )
            return

    # Route users based on login status
    if not st.session_state.get('logged_in'):
        login_page()
    else:
        user_type = st.session_state.user_type
        
        if user_type == "admin":
            admin_dashboard()
        elif user_type == "teacher":
            teacher_dashboard()
        elif user_type == "student":
            student_dashboard()
        else:
            st.error("Unknown user type. Please log out and try again.")
            if st.button("Logout"):
                logout()
                st.rerun()


if __name__ == "__main__":
    main()
