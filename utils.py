"""
Utility Functions Module
Contains common functions used across all modules
"""

import secrets
import streamlit as st
from database import get_db_connection, hash_password
import mysql.connector


# --- ID Generation ---
def generate_id(prefix, table_name, column_name):
    """
    Generate a sequential ID for database records.
    
    Args:
        prefix: ID prefix (e.g., 'STU', 'TEA')
        table_name: Database table name
        column_name: Column containing the IDs
    
    Returns:
        New ID in format: prefix + 3-digit number
    """
    with get_db_connection() as conn:
        if conn is None:
            return f"{prefix}001"
        
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT {column_name} FROM {table_name} ORDER BY {column_name} DESC LIMIT 1"
            )
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                last_id = int(result[0][len(prefix):])
                return f"{prefix}{last_id + 1:03d}"
            return f"{prefix}001"
        
        except Exception as e:
            st.error(f"Error generating ID: {e}")
            return f"{prefix}001"


def generate_student_id():
    """Generate new student ID."""
    return generate_id("STU", "students", "student_id")


def generate_teacher_id():
    """Generate new teacher ID."""
    return generate_id("TEA", "teachers", "teacher_id")


def generate_grade_id():
    """Generate new grade ID."""
    return generate_id("GRA", "grades", "grade_id")


def generate_subject_id():
    """Generate new subject ID."""
    return generate_id("SUB", "subjects", "subject_id")


import time
import random
import string

def generate_attendance_id():
    """Generate unique attendance ID - shorter version"""
    timestamp = int(time.time() * 1000) % 1000000000
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ATT_{timestamp}_{random_chars}"

def generate_password(length=12):
    """
    Generate a random secure password.
    
    Args:
        length: Password length (default 12)
    
    Returns:
        URL-safe random password
    """
    return secrets.token_urlsafe(length)[:length]


# --- Grade Calculation ---
def calculate_grade(percentage):
    """
    Calculate letter grade from percentage.
    
    Grade Scale:
    A+ : 90-100%
    A  : 85-89%
    B+ : 80-84%
    B  : 75-79%
    C+ : 70-74%
    C  : 65-69%
    D  : 60-64%
    F  : Below 60%
    """
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


def get_grade_color(grade):
    """Get color code for a grade."""
    color_map = {
        'A+': '🟢', 'A': '🟢', 'B+': '🟡', 'B': '🟡',
        'C+': '🟠', 'C': '🟠', 'D': '🔴', 'F': '🔴'
    }
    return color_map.get(grade, '⚪')


# --- Database Operations ---
def update_student_password(student_id, new_password):
    """Update student password."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE students SET password = %s WHERE student_id = %s",
                (hash_password(new_password), student_id)
            )
            conn.commit()
        return True, "Password updated successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"


def update_teacher_password(teacher_id, new_password):
    """Update teacher password."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE teachers SET password = %s WHERE teacher_id = %s",
                (hash_password(new_password), teacher_id)
            )
            conn.commit()
        return True, "Password updated successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"


def delete_student(student_id):
    """Delete a student from database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            conn.commit()
        return True, f"Student {student_id} deleted successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"


def delete_teacher(teacher_id):
    """Delete a teacher from database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            conn.commit()
        return True, f"Teacher {teacher_id} deleted successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"


# --- Data Insertion ---
def insert_grade(student_id, subject, exam_type, marks_obtained, total_marks, date, teacher_id):
    """Insert a new grade record."""
    try:
        percentage = (marks_obtained / total_marks) * 100
        grade = calculate_grade(percentage)
        grade_id = generate_grade_id()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO grades (grade_id, student_id, subject, exam_type, 
                                   marks_obtained, total_marks, percentage, grade, date, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (grade_id, student_id, subject, exam_type, marks_obtained, 
                  total_marks, percentage, grade, date, teacher_id))
            conn.commit()
        
        return True, f"Grade recorded successfully! Grade: {grade} ({percentage:.1f}%)"
    except Exception as e:
        return False, f"Error recording grade: {str(e)}"


def insert_attendance(student_id, date, subject, status, teacher_id):
    """Insert attendance record."""
    try:
        attendance_id = generate_attendance_id()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attendance (attendance_id, student_id, date, subject, status, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE status = %s, updated_at = NOW()
            """, (attendance_id, student_id, date, subject, status, teacher_id, status))
            conn.commit()
        
        return True, "Attendance saved successfully"
    except Exception as e:
        return False, f"Error: {str(e)}"


# --- UI Helpers ---
def show_success_message(title, details):
    """Display a formatted success message."""
    st.success(f"✅ {title}")
    for key, value in details.items():
        st.info(f"**{key}:** `{value}`")


def show_error_message(message):
    """Display a formatted error message."""
    st.error(f"❌ {message}")


def show_warning_message(message):
    """Display a formatted warning message."""
    st.warning(f"⚠️ {message}")


# --- Semester Mapping ---
def get_semester_options(year):
    """Get semester options based on year."""
    semester_map = {
        "1st Year": ["1st Semester", "2nd Semester"],
        "2nd Year": ["3rd Semester", "4th Semester"],
        "3rd Year": ["5th Semester", "6th Semester"],
        "4th Year": ["7th Semester", "8th Semester"],
    }
    return semester_map.get(year, [])
