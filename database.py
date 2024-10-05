# File: database.py

import sqlite3
import hashlib
from datetime import datetime

class Database:
    def __init__(self, db_name='students.db'):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, is_admin INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS students
                     (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT, email TEXT, course TEXT,
                     resume_path TEXT, photo_path TEXT, student_id TEXT, register_no TEXT, academic_year TEXT,
                     FOREIGN KEY (user_id) REFERENCES users(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS pending_registrations
                     (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, name TEXT, email TEXT, course TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS courses
                     (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
        c.execute('''CREATE TABLE IF NOT EXISTS attendance
                     (id INTEGER PRIMARY KEY, student_id INTEGER, course_id INTEGER, date TEXT, 
                     in_time TEXT, out_time TEXT,
                     FOREIGN KEY (student_id) REFERENCES students(id),
                     FOREIGN KEY (course_id) REFERENCES courses(id))''')
        self.conn.commit()

    def hash_password(self, password):
        return hashlib.sha256(str.encode(password)).hexdigest()

    def check_user(self, username, password):
        c = self.conn.cursor()
        c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, self.hash_password(password)))
        return c.fetchone()

    def is_admin(self, user_id):
        c = self.conn.cursor()
        c.execute('SELECT is_admin FROM users WHERE id=?', (user_id,))
        result = c.fetchone()
        return result['is_admin'] if result else False

    def get_all_courses(self):
        c = self.conn.cursor()
        c.execute('SELECT name FROM courses')
        return [row['name'] for row in c.fetchall()]
    
    def get_all_attendance(self):
        c = self.conn.cursor()
        query = """
        SELECT students.name, courses.name AS course, attendance.date, 
            attendance.in_time, attendance.out_time
        FROM attendance 
        INNER JOIN students ON attendance.student_id = students.id
        INNER JOIN courses ON attendance.course_id = courses.id
        ORDER BY attendance.date DESC, students.name
        """
        c.execute(query)
        return [dict(row) for row in c.fetchall()]

    def search_students(self, search_query='', course_filter=None):
        c = self.conn.cursor()
        query = '''SELECT * FROM students WHERE 
                (name LIKE ? OR email LIKE ?)'''
        params = [f'%{search_query}%', f'%{search_query}%']
        
        if course_filter:
            query += ' AND course = ?'
            params.append(course_filter)
        
        c.execute(query, params)
        return [dict(row) for row in c.fetchall()]

    def register_student(self, username, password, name, email, course):
        if not email.endswith('@srmist.edu.in'):
            return False, "Please use an email address with the domain srmist.edu.in"
        
        c = self.conn.cursor()
        try:
            c.execute('INSERT INTO pending_registrations (username, password, name, email, course) VALUES (?, ?, ?, ?, ?)',
                      (username, self.hash_password(password), name, email, course))
            self.conn.commit()
            return True, "Registration submitted successfully! Please wait for admin approval."
        except sqlite3.IntegrityError:
            return False, "Username already exists. Please choose a different username."

    def get_pending_registrations(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM pending_registrations')
        return c.fetchall()

    def approve_registration(self, registration_id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM pending_registrations WHERE id = ?', (registration_id,))
        registration = c.fetchone()
        
        if registration:
            c.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)',
                      (registration['username'], registration['password']))
            user_id = c.lastrowid
            c.execute('INSERT INTO students (user_id, name, email, course) VALUES (?, ?, ?, ?)',
                      (user_id, registration['name'], registration['email'], registration['course']))
            c.execute('DELETE FROM pending_registrations WHERE id = ?', (registration_id,))
            self.conn.commit()

    def add_course(self, course_name):
        c = self.conn.cursor()
        try:
            c.execute('INSERT INTO courses (name) VALUES (?)', (course_name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_course(self, course_name):
        c = self.conn.cursor()
        c.execute('DELETE FROM courses WHERE name = ?', (course_name,))
        self.conn.commit()

    def get_all_students(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM students')
        return [dict(row) for row in c.fetchall()]

    def get_student(self, user_id):
        c = self.conn.cursor()
        c.execute('SELECT * FROM students WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return dict(result) if result else None

    def update_student(self, user_id, name, email, course, student_id, register_no, academic_year, resume_path, photo_path):
        c = self.conn.cursor()
        c.execute('''UPDATE students SET name=?, email=?, course=?, student_id=?, register_no=?, academic_year=?, 
                    resume_path=?, photo_path=? WHERE user_id=?''', 
                    (name, email, course, student_id, register_no, academic_year, resume_path, photo_path, user_id))
        self.conn.commit()

    def delete_student(self, student_id):
        c = self.conn.cursor()
        c.execute('DELETE FROM students WHERE id = ?', (student_id,))
        self.conn.commit()

    def get_student_courses(self, user_id):
        c = self.conn.cursor()
        c.execute('SELECT course FROM students WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return [result['course']] if result else []

    def mark_attendance(self, student_id, course_id, attendance_type, time, is_manual=False):
        c = self.conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        c.execute("SELECT * FROM attendance WHERE student_id = ? AND course_id = ? AND date = ?", 
                  (student_id, course_id, today))
        existing_record = c.fetchone()
        
        if existing_record:
            if attendance_type == "In":
                return False, "Attendance already marked for today"
            elif attendance_type == "Out":
                in_time = datetime.strptime(existing_record['in_time'], "%H:%M:%S")
                out_time = datetime.strptime(time, "%H:%M:%S")
                if out_time <= in_time:
                    return False, "Out time cannot be earlier than or equal to In time"
                c.execute("UPDATE attendance SET out_time = ? WHERE id = ?", (time, existing_record['id']))
        else:
            if attendance_type == "In":
                c.execute("INSERT INTO attendance (student_id, course_id, date, in_time) VALUES (?, ?, ?, ?)",
                          (student_id, course_id, today, time))
            else:
                return False, "Cannot mark Out without marking In first"
        
        self.conn.commit()
        return True, "Attendance marked successfully"

    def get_attendance(self, student_id, course_id):
        c = self.conn.cursor()
        c.execute("""SELECT date, in_time, out_time 
                     FROM attendance 
                     WHERE student_id = ? AND course_id = ? 
                     ORDER BY date DESC""", (student_id, course_id))
        return c.fetchall()

    def get_attendance_by_date(self, course_id, date):
        c = self.conn.cursor()
        c.execute("""SELECT students.name, students.course AS department, 
                     attendance.in_time, attendance.out_time
                     FROM students 
                     INNER JOIN attendance ON students.id = attendance.student_id 
                     WHERE attendance.course_id = ? AND attendance.date = ?""", (course_id, date))
        records = c.fetchall()
        
        result = []
        for record in records:
            in_time = datetime.strptime(record['in_time'], "%H:%M:%S") if record['in_time'] else None
            out_time = datetime.strptime(record['out_time'], "%H:%M:%S") if record['out_time'] else None
            
            if in_time and out_time:
                duration = str(out_time - in_time)
            else:
                duration = "N/A"
            
            result.append(record + (duration,))
        
        return result

    def close(self):
        self.conn.close()