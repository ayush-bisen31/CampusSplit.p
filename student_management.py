"""
Student Management Module
Handles student creation, password management, and listing
"""

import streamlit as st
import pandas as pd
import mysql.connector
from datetime import date, timedelta
from database import (
    get_db_connection, hash_password, get_all_students
)
from auth import validate_email
from utils import (
    generate_student_id, generate_password, delete_student,
    update_student_password, get_semester_options, show_error_message
)


def add_student_form():
    """Form for adding new students with password options."""
    if 'new_student_credentials' in st.session_state:
        creds = st.session_state.new_student_credentials
        st.success("✅ Student added successfully!")
        st.info(f"**Student ID:** `{creds['id']}`")
        if creds['password']:
            st.info(f"**Generated Password:** `{creds['password']}`")
            st.warning("⚠️ Please copy these credentials and share securely with the student")
        del st.session_state.new_student_credentials

    with st.expander("➕ Add New Student", expanded=False):
        
        # Password option selector (outside form to prevent resets)
        st.write("**Password Options**")
        password_option = st.radio(
            "Choose password method",
            ("Generate Automatically", "Set Manually"),
            horizontal=True,
            key="student_pwd_option",
            label_visibility="collapsed"
        )
        
        # Year selector (outside form to trigger semester update)
        st.write("**Course Details**")
        year_options = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
        year = st.selectbox("Year*", year_options, key="student_year_selector")
        semester_options = get_semester_options(year)

        with st.form("add_student_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Personal Details**")
                first_name = st.text_input("First Name*")
                last_name = st.text_input("Last Name*")
                email = st.text_input("Email*")
                phone = st.text_input("Phone Number*")
                date_of_birth = st.date_input(
                    "Date of Birth*",
                    value=date.today() - timedelta(days=6570)
                )
            
            with col2:
                st.write("‎")  # Spacing
                gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
                course = st.selectbox(
                    "Course*",
                    ["Data Science", "Computer Science", "Machine Learning", 
                     "Web Development", "Software Engineering"]
                )
                semester = st.selectbox("Semester*", semester_options)
                address = st.text_area("Address (Optional)", height=80)

            st.markdown("---")
            
            # Password fields (shown conditionally based on radio button)
            manual_password = ""
            confirm_password = ""
            
            if password_option == "Set Manually":
                st.write("**Set Custom Password**")
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    manual_password = st.text_input("Password*", type="password", key="student_pwd")
                with p_col2:
                    confirm_password = st.text_input("Confirm Password*", type="password", key="student_pwd_confirm")
            
            # Submit button
            submitted = st.form_submit_button("Add Student", type="primary", use_container_width=True)
            
            if submitted:
                # Validation
                if not all([first_name, last_name, email, phone, course, year, semester]):
                    show_error_message("Please fill all required fields marked with *")
                    return
                
                if not validate_email(email):
                    show_error_message("Please enter a valid email address")
                    return

                # Password handling
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

                # Insert into database
                if password:
                    try:
                        student_id = generate_student_id()
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO students (
                                    student_id, first_name, last_name, email, phone,
                                    date_of_birth, gender, course, year, semester,
                                    address, enrollment_date, password, status
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Active')
                            """, (
                                student_id, first_name, last_name, email, phone,
                                date_of_birth, gender, course, year, semester,
                                address if address else None, date.today(),
                                hash_password(password)
                            ))
                            conn.commit()

                        st.session_state.new_student_credentials = {
                            "id": student_id,
                            "password": password if show_password else None
                        }
                        st.rerun()

                    except mysql.connector.IntegrityError as e:
                        if "email" in str(e):
                            show_error_message("Email already exists")
                        elif "phone" in str(e):
                            show_error_message("Phone number already exists")
                        else:
                            show_error_message(f"Database error: {str(e)}")
                    except Exception as e:
                        show_error_message(f"Error adding student: {str(e)}")


def student_management_interface(can_delete=False):
    """
    Reusable UI component for viewing and managing students.
    
    Args:
        can_delete: Boolean to allow deletion (True for admins, False for teachers)
    """
    st.markdown("---")
    st.subheader("Student List & Management")
    
    students = get_all_students()

    if not students:
        st.info("ℹ️ No students found")
        return

    # Display students table
    df_students = pd.DataFrame(students)
    display_cols = ['student_id', 'first_name', 'last_name', 'gender', 'course', 'email', 'phone', 'status']
    st.dataframe(df_students[display_cols], use_container_width=True, hide_index=True)

    # Password reset success message
    if 'password_reset_info' in st.session_state:
        info = st.session_state.password_reset_info
        st.success(f"✅ Password reset for {info['student_id']}")
        st.info(f"**New Password:** `{info['new_password']}`")
        st.warning("⚠️ Please share this new password securely with the student")
        del st.session_state.password_reset_info

    # Student selection dropdown
    student_options = {
        f"{s['student_id']} - {s['first_name']} {s['last_name']}": s['student_id']
        for s in students
    }
    
    selected_label = st.selectbox(
        "Select a student to manage",
        [""] + list(student_options.keys()),
        key="student_management_select"
    )

    if selected_label:
        student_id = student_options[selected_label]
        manage_student_actions(student_id, selected_label, can_delete)


def manage_student_actions(student_id, selected_label, can_delete):
    """
    Manage actions for a selected student (password reset, deletion).
    
    Args:
        student_id: The student's ID
        selected_label: Display label for the student
        can_delete: Whether to show delete button
    """
    with st.expander("🔑 Manage Selected Student", expanded=True):
        st.write(f"**Actions for:** {selected_label}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "🔄 Generate New Password",
                key=f"gen_pw_{student_id}",
                use_container_width=True
            ):
                new_pw = generate_password()
                success, msg = update_student_password(student_id, new_pw)
                if success:
                    st.session_state.password_reset_info = {
                        'student_id': student_id,
                        'new_password': new_pw
                    }
                    st.rerun()
                else:
                    show_error_message(msg)
        
        if can_delete:
            with col2:
                if st.button(
                    "🗑️ Delete Student",
                    key=f"del_student_{student_id}",
                    use_container_width=True,
                    type="secondary"
                ):
                    success, msg = delete_student(student_id)
                    if success:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        show_error_message(msg)

        st.markdown("---")
        
        # Custom password form
        with st.form(key=f"custom_pw_{student_id}"):
            st.write("**Set Custom Password**")
            custom_pw = st.text_input(
                "New Password",
                type="password",
                key=f"custom_pwd_{student_id}"
            )
            
            if st.form_submit_button("Set Password", use_container_width=True):
                if not custom_pw:
                    show_error_message("Password cannot be empty")
                else:
                    success, msg = update_student_password(student_id, custom_pw)
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        show_error_message(msg)
