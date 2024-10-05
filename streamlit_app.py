import streamlit as st
import sqlite3
import hashlib
import os
import zipfile
import io
from werkzeug.utils import secure_filename
import pandas as pd
from PIL import Image
import numpy as np
from datetime import datetime, date
from face_recognition_module import FaceRecognitionModule
from database import Database

# Initialize database and face recognition module
db = Database()
face_module = FaceRecognitionModule()

# Helper functions
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def save_file(file, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, secure_filename(file.name))
    with open(file_path, 'wb') as f:
        f.write(file.getbuffer())
    return file_path

# Streamlit app
st.logo("assets/srmist.jpg")
st.set_page_config(page_title="Student Management and Attendance Portal", layout="wide")
st.title('Student Management and Attendance Portal')

def main():
    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None

    # Check if user is logged in
    if st.session_state.user is None:
        page = st.sidebar.selectbox('Choose an action', ['Login', 'Register'])
        if page == 'Login':
            login()
        else:
            register()
    elif db.is_admin(st.session_state.user['id']):
        admin_view()
    else:
        student_view()

def login():
    st.subheader('Login')
    
    st.write("""
    ### Instructions:
    - For students: Use the username and password you created during registration.
    - For admins: Use your admin credentials.
    - If you don't have an account, please register using the sidebar option.
    """)
    
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    
    if st.button('Login'):
        user = db.check_user(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error('Invalid username or password')

def register():
    st.subheader('Student Registration')
    
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    name = st.text_input('Full Name')
    email = st.text_input('Email')
    course = st.selectbox('Course', db.get_all_courses())
    
    if st.button('Register'):
        if username and password and name and email and course:
            success, message = db.register_student(username, password, name, email, course)
            if success:
                st.success(message)
            else:
                st.error(message)
        else:
            st.error('Please fill in all fields')

def student_view():
    st.subheader(f'Student Dashboard - Welcome, {st.session_state.user["username"]}!')

    if st.sidebar.button('Logout'):
        st.session_state.user = None
        st.rerun()

    user_id = st.session_state.user['id']
    student = db.get_student(user_id)

    if student:
        # Convert sqlite3.Row to dictionary
        student = dict(student)

        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"Name: {student.get('name', 'N/A')}")
            st.write(f"Email: {student.get('email', 'N/A')}")
            st.write(f"Course: {student.get('course', 'N/A')}")
            st.write(f"Student ID: {student.get('student_id', 'N/A')}")
            st.write(f"Register No: {student.get('register_no', 'N/A')}")
            st.write(f"Academic Year: {student.get('academic_year', 'N/A')}")

        with col2:
            if student.get('photo_path'):
                st.image(student['photo_path'], caption='Profile Photo', use_column_width=True)
            else:
                st.write("No profile photo available.")
            
            if student.get('resume_path'):
                with open(student['resume_path'], "rb") as file:
                    st.download_button(
                        label="Download Your Resume",
                        data=file,
                        file_name="your_resume.pdf",
                        mime="application/pdf"
                    )
            else:
                st.write("No resume file available.")

    st.subheader('Update Your Details')
    
    fields = ['name', 'email', 'course', 'student_id', 'register_no', 'academic_year']
    inputs = {}

    for field in fields:
        if field == 'course':
            inputs[field] = st.selectbox('Course', db.get_all_courses(), 
                index=db.get_all_courses().index(student.get('course')) if student and student.get('course') in db.get_all_courses() else 0)
        else:
            inputs[field] = st.text_input(field.capitalize(), value=student.get(field, '') if student else '')

    resume = st.file_uploader('Upload Resume (PDF only)', type='pdf')
    photo = st.file_uploader('Upload Profile Photo', type=['jpg', 'jpeg', 'png'])
    
    if st.button('Update Details'):
        if all(inputs.values()):
            resume_path = save_file(resume, 'resumes') if resume else (student.get('resume_path') if student else None)
            photo_path = save_file(photo, 'photos') if photo else (student.get('photo_path') if student else None)
            
            db.update_student(user_id, inputs['name'], inputs['email'], inputs['course'], 
                              inputs['student_id'], inputs['register_no'], inputs['academic_year'],
                              resume_path, photo_path)
            st.success('Details updated successfully!')
            st.rerun()
        else:
            st.error('Please fill in all fields')

    st.subheader('Mark Attendance')
    course_id = st.selectbox("Select Course", options=db.get_student_courses(user_id))
    attendance_type = st.radio("Select attendance type:", ("In", "Out"))
    
    mark_method = st.radio("Select marking method:", ("Manual", "Facial Recognition"))

    if mark_method == "Manual":
        if st.button("Mark Attendance Manually"):
            current_time = datetime.now().strftime("%H:%M:%S")
            success, message = db.mark_attendance(user_id, course_id, attendance_type, current_time, is_manual=True)
            if success:
                st.success(f"{attendance_type} attendance marked manually at {current_time}")
            else:
                st.error(message)
    else:
        st.write("Look at the camera and click 'Mark Attendance' to use facial recognition.")
        picture = st.camera_input("Take a picture for attendance", key=f"mark_attendance_{user_id}")
        if picture:
            image = Image.open(picture)
            image_array = np.array(image)
            face_locations, face_names = face_module.recognize_face(image_array)
            
            if face_locations and face_names:
                if face_names[0] != "Unknown":
                    current_time = datetime.now().strftime("%H:%M:%S")
                    success, message = db.mark_attendance(user_id, course_id, attendance_type, current_time)
                    if success:
                        st.success(f"{attendance_type} attendance marked via facial recognition at {current_time}")
                    else:
                        st.error(message)
                else:
                    st.error(f"Face not recognized. Known faces: {face_module.known_face_names}")
                    st.error("Please try again or contact an administrator.")
            else:
                st.error("No face detected in the image. Please try again.")
            
            image_with_faces = face_module.draw_faces(image_array, face_locations, face_names)
            st.image(image_with_faces, channels="RGB")

    st.subheader('Your Attendance Records')
    attendance = db.get_attendance(user_id, course_id)
    if attendance:
        df = pd.DataFrame(attendance, columns=["Date", "In Time", "Out Time"])
        st.dataframe(df)
    else:
        st.info("No attendance records found for this course.")

def admin_view():
    st.subheader('Admin Dashboard')
    
    if st.sidebar.button('Logout'):
        st.session_state.user = None
        st.rerun()
    
    # Initialize session state for tab selection if it doesn't exist
    if 'admin_tab' not in st.session_state:
        st.session_state.admin_tab = "Student List"

    # Use radio buttons for tab selection
    st.session_state.admin_tab = st.sidebar.radio(
        "Select a tab",
        ["Student List", "Student Details", "Pending Registrations", "Course Management", "Attendance", "Train Faces"]
    )
    
    if st.session_state.admin_tab == "Student List":
        student_list_tab()
    elif st.session_state.admin_tab == "Student Details":
        student_details_tab()
    elif st.session_state.admin_tab == "Pending Registrations":
        pending_registrations_tab()
    elif st.session_state.admin_tab == "Course Management":
        course_management_tab()
    elif st.session_state.admin_tab == "Attendance":
        attendance_tab()
    elif st.session_state.admin_tab == "Train Faces":
        train_faces_tab()

def student_list_tab():
    st.subheader('Student List')
    search_query = st.text_input('Search by name or email')
    courses = ['All'] + db.get_all_courses()
    course_filter = st.selectbox('Filter by course', courses)
    
    if course_filter == 'All':
        course_filter = None
    
    students = db.search_students(search_query, course_filter)
    
    if students:
        df = pd.DataFrame(students)
        st.dataframe(df)
        
        if st.button('Download All Resumes'):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for student in students:
                    if student.get('resume_path'):
                        file_name = f"{student.get('name', 'Unknown')}_{student.get('course', 'no_course')}_resume.pdf"
                        zip_file.write(student['resume_path'], file_name)
            
            zip_buffer.seek(0)
            st.download_button(
                label="Download Resumes Zip",
                data=zip_buffer,
                file_name="student_resumes.zip",
                mime="application/zip"
            )
    else:
        st.write('No student details found matching the search criteria.')

def student_details_tab():
    st.subheader('Student Details')
    
    students = db.get_all_students()
    
    if students:
        for student in students:
            with st.expander(f"{student['name']} - {student['email']}"):
                st.write(f"Course: {student['course']}")
                st.write(f"Student ID: {student['student_id']}")
                st.write(f"Register No: {student['register_no']}")
                st.write(f"Academic Year: {student['academic_year']}")

                if student.get('photo_path') and os.path.exists(student['photo_path']):
                    st.image(student['photo_path'], caption='Profile Photo', width=200)
                else:
                    st.write("No profile photo available.")
                
                if student.get('resume_path') and os.path.exists(student['resume_path']):
                    with open(student['resume_path'], "rb") as file:
                        st.download_button(
                            label=f"Download {student['name']}'s Resume",
                            data=file,
                            file_name=f"{student['name']}_resume.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.write("No resume file available.")
                
                if st.button(f"Delete {student['name']}", key=f"delete_{student['id']}"):
                    db.delete_student(student['id'])
                    st.success(f"Deleted student {student['name']}")
                    st.rerun()
    else:
        st.write('No student details found.')

def pending_registrations_tab():
    st.subheader('Pending Registrations')
    pending_registrations = db.get_pending_registrations()
    
    if pending_registrations:
        for registration in pending_registrations:
            st.write(f"Username: {registration['username']}")
            st.write(f"Name: {registration['name']}")
            st.write(f"Email: {registration['email']}")
            st.write(f"Course: {registration['course']}")
            if st.button(f"Approve {registration['username']}", key=f"approve_{registration['id']}"):
                db.approve_registration(registration['id'])
                st.success(f"Approved registration for {registration['username']}")
                st.rerun()
            st.write('---')
    else:
        st.write('No pending registrations.')

def course_management_tab():
    st.subheader('Course Management')
    
    new_course = st.text_input('Add New Course')
    if st.button('Add Course'):
        if new_course:
            if db.add_course(new_course):
                st.success(f"Course '{new_course}' added successfully.")
                st.rerun()
            else:
                st.error(f"Course '{new_course}' already exists.")
        else:
            st.error("Please enter a course name.")
    
    st.subheader('Existing Courses')
    courses = db.get_all_courses()
    for course in courses:
        col1, col2 = st.columns([3, 1])
        col1.write(course)
        if col2.button('Delete', key=f"delete_course_{course}"):
            db.delete_course(course)
            st.success(f"Course '{course}' deleted successfully.")
            st.rerun()

def attendance_tab():
    st.subheader('View Attendance')
    
    courses = db.get_all_courses()
    course_options = {f"{c}": c for c in courses}
    selected_course = st.selectbox("Select course:", options=list(course_options.keys()))
    course_id = course_options[selected_course]
    
    selected_date = st.date_input("Select date:", date.today())
    
    if st.button("View Attendance"):
        attendance = db.get_attendance_by_date(course_id, selected_date.strftime("%Y-%m-%d"))
        if attendance:
            df = pd.DataFrame(attendance, columns=["Name", "Department", "In Time", "Out Time", "Duration"])
            st.dataframe(df)
        else:
            st.info("No attendance records found for the selected date and course.")


def train_faces_tab():
    st.subheader("Train Faces")
    students = db.get_all_students()
    if students:
        student_id = st.selectbox("Select a student to train face:", 
                                  options=[s['id'] for s in students],
                                  format_func=lambda x: next(s['name'] for s in students if s['id'] == x))
        student = next(s for s in students if s['id'] == student_id)
        st.write(f"Training face for: {student['name']}")
        picture = st.camera_input("Take a picture to train face recognition", key=f"train_face_{student_id}")
        if picture:
            try:
                image = Image.open(picture)
                image_array = np.array(image)
                if face_module.add_face(image_array, student['name']):
                    st.success(f"Face recognition trained for {student['name']}")
                    st.write(f"Current known faces: {face_module.known_face_names}")
                else:
                    st.error("No face detected in the image. Please try again.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    else:
        st.info("No students found in the database. Add students first.")

if __name__ == '__main__':
    main()

    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)