"""
Admin Dashboard Module
Complete admin interface for managing teachers, students, and subjects
"""

import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date
from database import (
    get_db_connection, hash_password, get_all_students, 
    get_all_teachers, get_all_subjects
)
from auth import logout, validate_email
from utils import (
    generate_teacher_id, generate_student_id, generate_subject_id,
    generate_password, delete_student, delete_teacher, 
    update_student_password, update_teacher_password, 
    get_semester_options, show_success_message, show_error_message
)
from student_management import add_student_form, student_management_interface


def admin_dashboard():
    """Main admin dashboard interface."""
    st.title(f"👑 Admin Dashboard")
    
    # Sidebar
    st.sidebar.markdown(f"**Welcome, {st.session_state.current_user['first_name']}!**")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="primary"):
        logout()

    # Navigation Menu
    menu = ["📊 Dashboard", "👨‍🏫 Manage Teachers", "👨‍🎓 Manage Students", "📚 Manage Subjects"]
    choice = st.selectbox("Navigation", menu, label_visibility="collapsed")

    if choice == "📊 Dashboard":
        admin_home()
    elif choice == "👨‍🏫 Manage Teachers":
        manage_teachers_admin()
    elif choice == "👨‍🎓 Manage Students":
        manage_students_admin()
    elif choice == "📚 Manage Subjects":
        manage_subjects_admin()


def admin_home():
    """Admin dashboard homepage with system statistics."""
    st.subheader("📊 System Overview")
    
    students = get_all_students()
    teachers = get_all_teachers()
    subjects = get_all_subjects()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("👨‍🎓 Total Students", len(students), delta="Active users")
    col2.metric("👨‍🏫 Total Teachers", len(teachers), delta="Including admins")
    col3.metric("📚 Total Subjects", len(subjects), delta="Available courses")
    
    st.markdown("---")
    st.subheader("📈 Quick Stats")
    
    # Active vs Inactive students
    active_students = len([s for s in students if s.get('status') == 'Active'])
    inactive_students = len(students) - active_students
    
    col1, col2 = st.columns(2)
    col1.metric("Active Students", active_students, delta=f"{(active_students/len(students)*100):.0f}%")
    col2.metric("Inactive/Graduated", inactive_students)


def manage_teachers_admin():
    """Admin interface for managing teachers."""
    st.subheader("👨‍🏫 Manage Teachers")
    
    # Success message for newly added teacher
    if 'new_teacher_credentials' in st.session_state:
        creds = st.session_state.new_teacher_credentials
        show_success_message(
            "Teacher Added Successfully!",
            {
                "Teacher ID": creds['id'],
                "Username": creds['username'],
                "Password": creds['password'] if creds.get('password') else "Check email"
            }
        )
        st.warning("⚠️ Please copy these credentials securely and share with the teacher.")
        del st.session_state.new_teacher_credentials

    # Add New Teacher Form
    with st.expander("➕ Add a New Teacher", expanded=False):
        add_teacher_form()

    st.markdown("---")
    
    # Teachers List
    st.subheader("All Teachers")
    teachers = get_all_teachers()
    
    # Password reset success message
    if 'teacher_password_reset_info' in st.session_state:
        info = st.session_state.teacher_password_reset_info
        show_success_message(
            f"Password Reset for {info['teacher_id']}",
            {"New Password": info['new_password']}
        )
        st.warning("⚠️ Please share this new password securely.")
        del st.session_state.teacher_password_reset_info

    if teachers:
        df_teachers = pd.DataFrame(teachers)
        df_teachers_display = df_teachers[df_teachers['role'] != 'admin']
        
        if not df_teachers_display.empty:
            st.dataframe(df_teachers_display, use_container_width=True)
            
            # Teacher Selection
            teacher_options = {
                f"{t['teacher_id']} - {t['first_name']} {t['last_name']}": t['teacher_id']
                for t in teachers if t['role'] != 'admin'
            }
            
            selected_label = st.selectbox("Select teacher to manage", [""] + list(teacher_options.keys()))
            
            if selected_label:
                teacher_id = teacher_options[selected_label]
                manage_teacher_actions(teacher_id, selected_label)
        else:
            st.info("ℹ️ No regular teachers found. Add some above.")
    else:
        st.info("ℹ️ No teachers in system.")


def add_teacher_form():
    """Form to add a new teacher."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Password Options**")
        password_option = st.radio(
            "Choose password method",
            ("Generate Automatically", "Set Manually"),
            horizontal=True,
            key="teacher_pwd_option",
            label_visibility="collapsed"
        )

    with st.form("new_teacher_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username*")
            first_name = st.text_input("First Name*")
            email = st.text_input("Email*")
        
        with col2:
            last_name = st.text_input("Last Name*")
            phone = st.text_input("Phone (optional)")

        st.markdown("---")
        
        manual_password = ""
        confirm_password = ""
        
        if password_option == "Set Manually":
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                manual_password = st.text_input("Password*", type="password", key="teacher_pwd")
            with p_col2:
                confirm_password = st.text_input("Confirm Password*", type="password", key="teacher_pwd_confirm")

        submitted = st.form_submit_button("Add Teacher", type="primary")
        
        if submitted:
            if not all([username, first_name, last_name, email]):
                show_error_message("Please fill all required fields marked with *")
                return
            
            if not validate_email(email):
                show_error_message("Please enter a valid email address")
                return

            password = None
            show_password = False

            if password_option == "Generate Automatically":
                password = generate_password()
                show_password = True
            else:
                if not manual_password:
                    show_error_message("Password cannot be empty")
                    return
                if manual_password != confirm_password:
                    show_error_message("Passwords do not match")
                    return
                password = manual_password

            if password:
                try:
                    teacher_id = generate_teacher_id()
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO teachers (teacher_id, username, password, first_name, last_name, email, role)
                            VALUES (%s, %s, %s, %s, %s, %s, 'teacher')
                        """, (teacher_id, username, hash_password(password), first_name, last_name, email))
                        conn.commit()

                    st.session_state.new_teacher_credentials = {
                        'id': teacher_id,
                        'username': username,
                        'password': password if show_password else None
                    }
                    st.rerun()
                
                except mysql.connector.IntegrityError as e:
                    if "username" in str(e):
                        show_error_message("Username already exists")
                    elif "email" in str(e):
                        show_error_message("Email already exists")
                    else:
                        show_error_message(f"Database error: {str(e)}")


def manage_teacher_actions(teacher_id, selected_label):
    """Manage actions for a selected teacher."""
    with st.expander("🔑 Manage Selected Teacher", expanded=True):
        st.write(f"**Actions for:** {selected_label}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Generate New Password", key=f"gen_teacher_pw_{teacher_id}", use_container_width=True):
                new_pw = generate_password()
                success, msg = update_teacher_password(teacher_id, new_pw)
                if success:
                    st.session_state.teacher_password_reset_info = {
                        'teacher_id': teacher_id,
                        'new_password': new_pw
                    }
                    st.rerun()
                else:
                    show_error_message(msg)
        
        with col2:
            if st.button("🗑️ Delete Teacher", key=f"del_teacher_{teacher_id}", use_container_width=True, type="secondary"):
                success, msg = delete_teacher(teacher_id)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    show_error_message(msg)

        st.markdown("---")
        
        with st.form(key=f"custom_teacher_pw_{teacher_id}"):
            st.write("**Set Custom Password**")
            custom_pw = st.text_input("New Password", type="password", key=f"custom_pwd_{teacher_id}")
            
            if st.form_submit_button("Set Password", use_container_width=True):
                if not custom_pw:
                    show_error_message("Password cannot be empty")
                else:
                    success, msg = update_teacher_password(teacher_id, custom_pw)
                    if success:
                        st.success(msg)
                    else:
                        show_error_message(msg)


def manage_students_admin():
    """Admin interface for managing students."""
    st.subheader("👨‍🎓 Manage Students")
    add_student_form()
    student_management_interface(can_delete=True)


def manage_subjects_admin():
    """Admin interface for managing subjects."""
    st.subheader("📚 Manage Subjects")

    with st.form("new_subject_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            name = st.text_input("Subject Name*", placeholder="e.g., Data Science")
        with col2:
            credits = st.number_input("Credits*", min_value=1, max_value=10, step=1, value=3)

        submitted = st.form_submit_button("Add Subject", type="primary", use_container_width=True)
        
        if submitted:
            if not name:
                show_error_message("Please enter subject name")
                return

            try:
                subject_id = generate_subject_id()
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO subjects (subject_id, name, credits) VALUES (%s, %s, %s)",
                        (subject_id, name, credits)
                    )
                    conn.commit()
                
                st.success(f"✅ Subject '{name}' added successfully!")
                st.rerun()
            
            except mysql.connector.IntegrityError:
                show_error_message("Subject name already exists")
            except Exception as e:
                show_error_message(f"Error: {str(e)}")

    st.markdown("---")
    st.subheader("All Subjects")
    
    subjects = get_all_subjects()
    if subjects:
        df_subjects = pd.DataFrame(subjects)
        st.dataframe(df_subjects, use_container_width=True)
    else:
        st.info("ℹ️ No subjects found.")
