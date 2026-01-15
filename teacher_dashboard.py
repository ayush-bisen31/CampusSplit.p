"""
Teacher Dashboard Module
Complete teacher interface for grades, attendance, and student management
"""

import streamlit as st
import pandas as pd
from datetime import date
from database import (
    get_db_connection, get_all_students, get_all_subjects,
    get_student_grades, get_student_attendance
)
from auth import logout
from utils import (
    generate_grade_id, generate_attendance_id, calculate_grade,
    insert_grade, get_grade_color
)
from student_management import add_student_form, student_management_interface


def teacher_dashboard():
    """Main teacher dashboard interface."""
    st.title(f"👨‍🏫 Teacher Dashboard")
    
    # Sidebar
    st.sidebar.markdown(f"**Welcome, {st.session_state.current_user['first_name']}!**")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True, type="primary"):
        logout()

    # Navigation Menu
    menu = ["📊 Dashboard", "👨‍🎓 Manage Students", "📝 Record Grades", "📅 Mark Attendance", "📈 View Reports"]
    choice = st.selectbox("Navigation", menu, label_visibility="collapsed")

    if choice == "📊 Dashboard":
        teacher_home()
    elif choice == "👨‍🎓 Manage Students":
        teacher_manage_students()
    elif choice == "📝 Record Grades":
        teacher_record_grades()
    elif choice == "📅 Mark Attendance":
        teacher_mark_attendance()
    elif choice == "📈 View Reports":
        teacher_view_reports()


def teacher_home():
    """Teacher dashboard homepage."""
    st.subheader("📊 Your Dashboard")
    
    students = get_all_students()
    subjects = get_all_subjects()
    teacher_id = st.session_state.current_user['teacher_id']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("👨‍🎓 Total Students", len(students), delta="In system")
    col2.metric("📚 Available Subjects", len(subjects), delta="To teach")
    
    # Recent grades recorded
    with get_db_connection() as conn:
        if conn:
            recent_grades = pd.read_sql("""
                SELECT COUNT(*) as count FROM grades 
                WHERE teacher_id = %s AND date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """, conn, params=(teacher_id,))
            col3.metric("📝 Grades This Week", recent_grades['count'].iloc[0] if not recent_grades.empty else 0)

    st.markdown("---")
    st.subheader("📈 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    if col1.button("📝 Record Grades", use_container_width=True, key="quick_grades"):
        st.session_state.page = "Record Grades"
    
    if col2.button("📅 Mark Attendance", use_container_width=True, key="quick_attendance"):
        st.session_state.page = "Mark Attendance"
    
    if col3.button("📊 View Reports", use_container_width=True, key="quick_reports"):
        st.session_state.page = "View Reports"


def teacher_manage_students():
    """Teacher interface for managing students."""
    st.subheader("👨‍🎓 Student Management")
    add_student_form()
    student_management_interface(can_delete=False)


def teacher_record_grades():
    """Teacher interface for recording student grades."""
    st.subheader("📝 Record Student Grades")
    
    students = get_all_students()
    subjects = get_all_subjects()
    teacher_id = st.session_state.current_user['teacher_id']
    
    if not students:
        st.warning("⚠️ No students found. Please add students first.")
        return
    
    if not subjects:
        st.warning("⚠️ No subjects available. Contact admin to add subjects.")
        return

    with st.form("grade_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            student_options = [f"{s['student_id']} - {s['first_name']} {s['last_name']}" for s in students]
            selected_student = st.selectbox("Select Student*", options=student_options)
            
            subject_options = [s['name'] for s in subjects]
            selected_subject = st.selectbox("Select Subject*", options=subject_options)
            
            exam_type = st.selectbox("Exam Type*", options=["Mid-term", "Final", "Quiz", "Assignment", "Project"])
        
        with col2:
            marks_obtained = st.number_input("Marks Obtained*", min_value=0.0, max_value=1000.0, step=0.5)
            total_marks = st.number_input("Total Marks*", min_value=1.0, max_value=1000.0, step=0.5, value=100.0)
            exam_date = st.date_input("Exam Date*", value=date.today())
        
        submitted = st.form_submit_button("Record Grade", type="primary", use_container_width=True)
        
        if submitted:
            if not all([selected_student, selected_subject, marks_obtained is not None, total_marks > 0]):
                st.error("❌ Please fill all required fields")
                return

            student_id = selected_student.split(" - ")[0]
            success, message = insert_grade(
                student_id, selected_subject, exam_type,
                marks_obtained, total_marks, exam_date, teacher_id
            )
            
            if success:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ {message}")

    st.markdown("---")
    st.subheader("📊 Recent Grades Recorded")
    
    with get_db_connection() as conn:
        if conn:
            recent_grades = pd.read_sql("""
                SELECT g.grade_id, g.student_id, s.first_name, s.last_name, g.subject, g.exam_type,
                       g.marks_obtained, g.total_marks, g.percentage, g.grade, g.date
                FROM grades g
                JOIN students s ON g.student_id = s.student_id
                WHERE g.teacher_id = %s
                ORDER BY g.date DESC
                LIMIT 10
            """, conn, params=(teacher_id,))
            
            if not recent_grades.empty:
                # Format the dataframe for display
                display_df = recent_grades.copy()
                display_df['percentage'] = display_df['percentage'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ No grades recorded yet")


def teacher_mark_attendance():
    """
    FIXED: Teacher interface for marking student attendance.
    No more duplicate ID errors.
    """
    st.subheader("📅 Mark Student Attendance")
    
    students = get_all_students()
    subjects = get_all_subjects()
    teacher_id = st.session_state.current_user['teacher_id']
    
    if not students:
        st.warning("⚠️ No students found")
        return
    if not subjects:
        st.warning("⚠️ No subjects found")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        subject_options = [s['name'] for s in subjects]
        selected_subject = st.selectbox("Select Subject", options=subject_options)
    with col2:
        attendance_date = st.date_input("Date", value=date.today())
    
    if selected_subject and attendance_date:
        st.markdown("---")
        st.subheader(f"📍 {selected_subject} - {attendance_date}")

        # Get existing attendance records
        existing_attendance = {}
        try:
            with get_db_connection() as conn:
                if conn:
                    existing_df = pd.read_sql(
                        "SELECT student_id, status FROM attendance WHERE date = %s AND subject = %s",
                        conn,
                        params=(attendance_date, selected_subject)
                    )
                    if not existing_df.empty:
                        existing_attendance = dict(zip(existing_df['student_id'], existing_df['status']))
        except Exception as e:
            st.warning(f"Could not load previous records")

        with st.form("attendance_form"):
            attendance_data = {}
            
            for student in students:
                student_id = student['student_id']
                current_status = existing_attendance.get(student_id, 'Present')
                status_index = 0 if current_status == 'Present' else 1
                
                cols = st.columns([3, 1])
                cols[0].write(f"{student['first_name']} {student['last_name']} ({student_id})")
                attendance_data[student_id] = cols[1].radio(
                    "Status",
                    ['Present', 'Absent'],
                    index=status_index,
                    key=f"status_{student_id}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
            
            if st.form_submit_button("💾 Save Attendance", type="primary", use_container_width=True):
                save_attendance_records(
                    attendance_data,
                    attendance_date,
                    selected_subject,
                    teacher_id
                )

                
def save_attendance_records(attendance_data, attendance_date, subject, teacher_id):
    """
    FIXED: Save attendance with unique ID generation and error handling.
    This separate function makes the code cleaner and more reliable.
    """
    try:
        with get_db_connection() as conn:
            if conn is None:
                st.error("❌ Database connection failed")
                return
            
            cursor = conn.cursor()
            
            # Step 1: DELETE existing records for this date and subject
            try:
                delete_sql = """
                    DELETE FROM attendance 
                    WHERE date = %s AND subject = %s
                """
                cursor.execute(delete_sql, (attendance_date, subject))
            except Exception as e:
                st.warning(f"Note: Could not delete old records")
            
            # Step 2: INSERT new attendance records
            insert_sql = """
                INSERT INTO attendance 
                (attendance_id, student_id, date, subject, status, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            saved_count = 0
            failed_students = []
            
            for student_id, status in attendance_data.items():
                try:
                    # FIXED: Import at top, use inside loop
                    attendance_id = generate_attendance_id()
                    
                    # Insert record
                    cursor.execute(
                        insert_sql,
                        (attendance_id, student_id, attendance_date, subject, status, teacher_id)
                    )
                    saved_count += 1
                    
                except Exception as e:
                    failed_students.append(f"{student_id}")
                    st.warning(f"Error for {student_id}: {str(e)}")
                    continue
            
            # Commit ALL changes at once
            conn.commit()
            cursor.close()
            
            # Show result
            if saved_count == len(attendance_data):
                st.success(f"✅ Attendance saved successfully! ({saved_count} students)")
                import time
                time.sleep(1)
                st.rerun()
            elif saved_count > 0:
                st.warning(f"⚠️ Saved {saved_count}/{len(attendance_data)} students. Failed: {len(failed_students)}")
            else:
                st.error(f"❌ Failed to save attendance")
    
    except Exception as e:
        st.error(f"❌ Critical Error: {str(e)}")


def teacher_view_reports():
    """Teacher interface for viewing detailed student reports."""
    st.subheader("📈 Student Reports & Analytics")
    
    students = get_all_students()
    if not students:
        st.warning("⚠️ No students found")
        return
    
    student_options = [""] + [f"{s['student_id']} - {s['first_name']} {s['last_name']}" for s in students]
    selected_student = st.selectbox("Select Student for Detailed Report", options=student_options)
    
    if selected_student:
        student_id = selected_student.split(" - ")[0]
        student_info = next((s for s in students if s['student_id'] == student_id), None)
        
        if student_info:
            st.markdown("---")
            st.subheader(f"📋 Report: {student_info['first_name']} {student_info['last_name']}")
            
            # Student Info
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Student ID", student_id)
            col2.metric("Course", student_info['course'])
            col3.metric("Year", student_info['year'])
            col4.metric("Status", student_info['status'])
            
            st.markdown("---")
            
            # Grades Section
            grades = get_student_grades(student_id)
            if grades:
                st.subheader("📝 Grades")
                df_grades = pd.DataFrame(grades)
                
                # Format for display
                display_cols = ['subject', 'exam_type', 'marks_obtained', 'total_marks', 'percentage', 'grade', 'date']
                display_df = df_grades[display_cols].copy()
                display_df['percentage'] = display_df['percentage'].apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Grade statistics
                col1, col2, col3 = st.columns(3)
                avg_percentage = df_grades['percentage'].mean()
                col1.metric("Average Percentage", f"{avg_percentage:.1f}%")
                col2.metric("Total Exams", len(grades))
                col3.metric("Best Grade", df_grades['grade'].mode()[0] if not df_grades.empty else 'N/A')
                
                # Subject-wise analysis
                st.write("**Subject-wise Average**")
                subject_avg = df_grades.groupby('subject')['percentage'].mean().reset_index()
                subject_avg.columns = ['Subject', 'Average %']
                st.bar_chart(subject_avg.set_index('Subject'))
            else:
                st.info("ℹ️ No grades recorded for this student")
            
            st.markdown("---")
            
            # Attendance Section
            attendance = get_student_attendance(student_id)
            if attendance:
                st.subheader("📅 Attendance")
                df_attendance = pd.DataFrame(attendance)
                
                st.dataframe(df_attendance[['date', 'subject', 'status']], use_container_width=True, hide_index=True)
                
                # Attendance Summary
                total = len(attendance)
                present = len([a for a in attendance if a['status'] == 'Present'])
                absent = total - present
                percent = (present / total * 100) if total > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Classes", total)
                col2.metric("Classes Present", present, delta=f"{present} days")
                col3.metric("Classes Absent", absent, delta=f"{absent} days")
                col4.metric("Attendance %", f"{percent:.1f}%")
                
                # Subject-wise attendance
                st.write("**Subject-wise Attendance**")
                subject_summary = df_attendance.groupby('subject')['status'].apply(
                    lambda s: (s == 'Present').sum() / len(s) * 100
                ).reset_index()
                subject_summary.columns = ['Subject', 'Attendance %']
                st.bar_chart(subject_summary.set_index('Subject'))
            else:
                st.info("ℹ️ No attendance records for this student")