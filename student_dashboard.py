"""
Student Dashboard Module
Complete student interface for viewing grades, attendance, and profile
"""

import streamlit as st
import pandas as pd
from database import get_student_grades, get_student_attendance
from auth import logout


def student_dashboard():
    """Main student dashboard interface."""
    st.title(f"👨‍🎓 Student Dashboard")
    
    # Sidebar
    st.sidebar.markdown(f"**Welcome, {st.session_state.current_user['first_name']}!**")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="primary"):
        logout()

    # Navigation Menu
    menu = ["📊 Dashboard", "📝 View Grades", "📅 View Attendance", "👤 Profile"]
    choice = st.selectbox("Navigation", menu, label_visibility="collapsed")

    if choice == "📊 Dashboard":
        student_home()
    elif choice == "📝 View Grades":
        student_view_grades()
    elif choice == "📅 View Attendance":
        student_view_attendance()
    elif choice == "👤 Profile":
        student_profile()


def student_home():
    """Student dashboard homepage."""
    st.subheader("📊 Your Academic Overview")
    
    student_id = st.session_state.current_user['student_id']
    grades = get_student_grades(student_id)
    attendance = get_student_attendance(student_id)
    
    col1, col2, col3 = st.columns(3)
    
    # Overall Average
    if grades:
        avg_percentage = sum(g['percentage'] for g in grades) / len(grades)
        col1.metric("📈 Overall Average", f"{avg_percentage:.1f}%", delta="All subjects")
    else:
        col1.metric("📈 Overall Average", "N/A", delta="No grades yet")
    
    # Total Exams
    col2.metric("📝 Total Exams Logged", len(grades), delta="All time")
    
    # Attendance
    if attendance:
        present_count = len([a for a in attendance if a['status'] == 'Present'])
        attendance_percentage = (present_count / len(attendance)) * 100
        col3.metric("📅 Attendance", f"{attendance_percentage:.1f}%", delta=f"{present_count} present")
    else:
        col3.metric("📅 Attendance", "N/A", delta="No records yet")

    st.markdown("---")
    st.subheader("🎯 Quick Navigation")
    
    col1, col2, col3 = st.columns(3)
    
    if col1.button("📝 View My Grades", use_container_width=True):
        st.session_state.page = "View Grades"
    
    if col2.button("📅 View Attendance", use_container_width=True):
        st.session_state.page = "View Attendance"
    
    if col3.button("👤 My Profile", use_container_width=True):
        st.session_state.page = "Profile"


def student_view_grades():
    """Student interface for viewing grades."""
    st.subheader("📝 Your Grades")
    
    student_id = st.session_state.current_user['student_id']
    grades = get_student_grades(student_id)
    
    if grades:
        df_grades = pd.DataFrame(grades)
        
        # Display grades table
        display_df = df_grades[['subject', 'exam_type', 'marks_obtained', 'total_marks', 'percentage', 'grade', 'date']].copy()
        display_df['percentage'] = display_df['percentage'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📊 Grade Analysis by Subject")
        
        # Subject averages
        subject_averages = df_grades.groupby('subject')['percentage'].mean().reset_index()
        subject_averages.columns = ['Subject', 'Average %']
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.bar_chart(subject_averages.set_index('Subject'))
        
        with col2:
            st.write("**Subject Summary**")
            for idx, row in subject_averages.iterrows():
                pct = row['Average %']
                grade = get_grade_from_percentage(pct)
                st.metric(row['Subject'], f"{pct:.1f}%", delta=grade)

    else:
        st.info("ℹ️ No grades available yet. Check back later!")


def student_view_attendance():
    """Student interface for viewing attendance."""
    st.subheader("📅 Your Attendance")
    
    student_id = st.session_state.current_user['student_id']
    attendance = get_student_attendance(student_id)
    
    if attendance:
        df_attendance = pd.DataFrame(attendance)
        
        st.dataframe(df_attendance[['date', 'subject', 'status']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📊 Attendance Summary")
        
        total = len(attendance)
        present = len([a for a in attendance if a['status'] == 'Present'])
        absent = total - present
        percent = (present / total * 100) if total > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Classes", total, delta="All subjects")
        col2.metric("🟢 Present", present, delta=f"{percent:.0f}%")
        col3.metric("🔴 Absent", absent, delta=f"{(100-percent):.0f}%")
        col4.metric("Overall Attendance", f"{percent:.1f}%", delta="Achievement")
        
        st.markdown("---")
        st.write("**Subject-wise Attendance**")
        subject_summary = df_attendance.groupby('subject')['status'].apply(
            lambda s: (s == 'Present').sum() / len(s) * 100
        ).reset_index()
        subject_summary.columns = ['Subject', 'Attendance %']
        
        st.bar_chart(subject_summary.set_index('Subject'))

    else:
        st.info("ℹ️ No attendance records available yet")


def student_profile():
    """Student profile page showing personal information."""
    st.subheader("👤 Your Profile")
    
    user = st.session_state.current_user
    
    # Profile Header
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.info("👤")
    
    with col2:
        st.write(f"## {user.get('first_name', '')} {user.get('last_name', '')}")
        st.write(f"**Student ID:** `{user.get('student_id', 'N/A')}`")

    st.markdown("---")
    
    # Personal Information
    st.subheader("📋 Personal Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Email", user.get('email', 'N/A'))
        st.metric("Phone", user.get('phone', 'N/A'))
    
    with col2:
        st.metric("Gender", user.get('gender', 'N/A'))
        st.metric("Date of Birth", str(user.get('date_of_birth', 'N/A')))
    
    with col3:
        st.metric("Status", user.get('status', 'N/A'))
        st.metric("Enrollment Date", str(user.get('enrollment_date', 'N/A')))

    st.markdown("---")
    
    # Academic Information
    st.subheader("🎓 Academic Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Course", user.get('course', 'N/A'))
    
    with col2:
        st.metric("Year", user.get('year', 'N/A'))
    
    with col3:
        st.metric("Semester", user.get('semester', 'N/A'))

    if user.get('address'):
        st.markdown("---")
        st.subheader("🏠 Address")
        st.write(user.get('address', 'N/A'))

    if user.get('emergency_contact'):
        st.markdown("---")
        st.subheader("🚨 Emergency Contact")
        st.write(user.get('emergency_contact', 'N/A'))


def get_grade_from_percentage(percentage):
    """Get letter grade from percentage."""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 85:
        return 'A'
    elif percentage >= 80:
        return 'B+'
    elif percentage >= 75:
        return 'B'
    elif percentage >= 70:
        return 'C+'
    elif percentage >= 65:
        return 'C'
    elif percentage >= 60:
        return 'D'
    else:
        return 'F'
