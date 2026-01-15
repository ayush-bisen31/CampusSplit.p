"""
Database Configuration & Helper Functions
Manages all database connections and queries
"""

import mysql.connector
import streamlit as st
import pandas as pd
import hashlib
from contextlib import contextmanager

# --- Database Configuration ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root1',
    'database': 'campus_management'
}


# --- Database Connection Management ---
@contextmanager
def get_db_connection():
    """Context manager for safe database connections."""
    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        yield connection
    except mysql.connector.Error as e:
        st.error(f"🔴 Database connection error: {e}")
        yield None
    finally:
        if connection and connection.is_connected():
            connection.close()


# --- Database Initialization ---
def init_database():
    """Create all required database tables."""
    with get_db_connection() as conn:
        if conn is None:
            return False
        cursor = conn.cursor()

        try:
            # Teachers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    teacher_id VARCHAR(20) PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(64) NOT NULL,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    subjects JSON,
                    role ENUM('teacher', 'admin') NOT NULL DEFAULT 'teacher',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id VARCHAR(20) PRIMARY KEY,
                    first_name VARCHAR(50) NOT NULL,
                    last_name VARCHAR(50) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    date_of_birth DATE NOT NULL,
                    gender ENUM('Male', 'Female', 'Other') NOT NULL,
                    course VARCHAR(100) NOT NULL,
                    year VARCHAR(20) NOT NULL,
                    semester VARCHAR(20) NOT NULL,
                    address TEXT,
                    emergency_contact VARCHAR(20),
                    enrollment_date DATE NOT NULL,
                    password VARCHAR(64) NOT NULL,
                    status ENUM('Active', 'Inactive', 'Graduated') DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Subjects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    subject_id VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    credits INT NOT NULL
                )
            """)

            # Grades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS grades (
                    grade_id VARCHAR(20) PRIMARY KEY,
                    student_id VARCHAR(20) NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    exam_type ENUM('Mid-term', 'Final', 'Quiz', 'Assignment', 'Project') NOT NULL,
                    marks_obtained DECIMAL(5,2) NOT NULL,
                    total_marks DECIMAL(5,2) NOT NULL,
                    percentage DECIMAL(5,2) NOT NULL,
                    grade CHAR(2) NOT NULL,
                    date DATE NOT NULL,
                    teacher_id VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
                )
            """)

            # Attendance table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id VARCHAR(20) PRIMARY KEY,
                    student_id VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    status ENUM('Present', 'Absent') NOT NULL,
                    teacher_id VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
                    UNIQUE KEY unique_attendance (student_id, date, subject)
                )
            """)

            conn.commit()
            cursor.close()
            return True

        except mysql.connector.Error as e:
            st.error(f"Error creating tables: {e}")
            return False


def initialize_default_data():
    """Add default admin user and subjects."""
    with get_db_connection() as conn:
        if conn is None:
            return
        cursor = conn.cursor()

        try:
            # Add default admin
            cursor.execute("SELECT COUNT(*) FROM teachers WHERE username = 'admin'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO teachers (teacher_id, username, password, first_name, last_name, email, subjects, role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    "TEA001", "admin", hash_password("admin123"),
                    "Admin", "User", "admin@school.com",
                    '["All Subjects"]', 'admin'
                ))

            # Add default subjects
            cursor.execute("SELECT COUNT(*) FROM subjects")
            if cursor.fetchone()[0] == 0:
                default_subjects = [
                    ("SUB001", "Data Science", 4),
                    ("SUB002", "Computer Science", 4),
                    ("SUB003", "Machine Learning", 4),
                    ("SUB004", "Web Development", 4),
                    ("SUB005", "Database Systems", 3),
                    ("SUB006", "Software Engineering", 3)
                ]
                cursor.executemany(
                    "INSERT INTO subjects (subject_id, name, credits) VALUES (%s, %s, %s)",
                    default_subjects
                )

            conn.commit()
            cursor.close()

        except mysql.connector.Error as e:
            st.error(f"Error initializing data: {e}")


# --- Password Hashing ---
def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


# --- Data Retrieval Functions ---
def get_student_grades(student_id):
    """Get all grades for a student."""
    with get_db_connection() as conn:
        if conn is None:
            return []
        return pd.read_sql(
            "SELECT * FROM grades WHERE student_id = %s ORDER BY date DESC",
            conn,
            params=(student_id,)
        ).to_dict('records')


def get_student_attendance(student_id):
    """Get all attendance records for a student."""
    with get_db_connection() as conn:
        if conn is None:
            return []
        return pd.read_sql(
            "SELECT * FROM attendance WHERE student_id = %s ORDER BY date DESC",
            conn,
            params=(student_id,)
        ).to_dict('records')


def get_all_students():
    """Get all students."""
    with get_db_connection() as conn:
        if conn is None:
            return []
        return pd.read_sql(
            "SELECT * FROM students ORDER BY first_name, last_name",
            conn
        ).to_dict('records')


def get_all_teachers():
    """Get all teachers."""
    with get_db_connection() as conn:
        if conn is None:
            return []
        return pd.read_sql(
            "SELECT teacher_id, username, first_name, last_name, email, role FROM teachers ORDER BY first_name",
            conn
        ).to_dict('records')


def get_all_subjects():
    """Get all subjects."""
    with get_db_connection() as conn:
        if conn is None:
            return []
        return pd.read_sql(
            "SELECT * FROM subjects ORDER BY name",
            conn
        ).to_dict('records')
