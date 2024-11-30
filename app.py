from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
import bcrypt
import mysql.connector
from mysql.connector import Error
import fitz  # PyMuPDF for PDF processing
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pdfplumber
from PyPDF2 import PdfReader



app = Flask(__name__)
CORS(app)
app.secret_key = 'jaikarthik'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'jaikarthik'
}

db_config_with_database = db_config.copy()
db_config_with_database['database'] = 'user_data'


# Initialize the database if it doesn't exist
def initialize_database():
    try:
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS user_data")
            cursor.execute("USE user_data")

            # Create the users table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    phone VARCHAR(15),
                    email VARCHAR(100) UNIQUE,
                    usn VARCHAR(20) UNIQUE,
                    semester INT,
                    grad_year INT,
                    password VARCHAR(255),
                    sgpa FLOAT DEFAULT NULL,
                    cgpa FLOAT DEFAULT NULL
                )
            """)

            # Create the student_details table if it doesn't exist
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faculty (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100) UNIQUE,
                    password VARCHAR(255)
                )
            """)

            cursor.execute("""CREATE TABLE IF NOT EXISTS student_details (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            university_seat_number VARCHAR(20) NOT NULL,
            subject_code VARCHAR(500) NOT NULL,
            subject_name VARCHAR(255) NOT NULL,
            total_marks INT NOT NULL)""")

            cursor.execute("""CREATE TABLE IF NOT EXISTS subjects (subject_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            subject_code VARCHAR(50) NOT NULL,
            subject_name VARCHAR(255) NOT NULL,
            total_marks INT DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students(student_id))""")


            cursor.execute("""CREATE TABLE IF NOT exists students (
            student_id INT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            university_seat_number VARCHAR(50) NOT NULL))""")

            

            connection.commit()
            print("Database and tables initialized successfully")
        cursor.close()
        connection.close()
    except Error as e:
        print(f"Error initializing database: {e}")


# Function to connect to the database after initialization
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config_with_database)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return None



# Helper function for extracting specific information from a PDF
import pdfplumber

def extract_specific_info_from_pdf(pdf_file):
    data = {"Student Name": None, "University Seat Number": None, "subjects": []}

    try:
        with pdfplumber.open(pdf_file) as pdf:
            print("Opened PDF file successfully")
            for page_number, page in enumerate(pdf.pages, start=1):
                print(f"Processing page {page_number}")
                tables = page.extract_tables()
                for table_number, table in enumerate(tables, start=1):
                    print(f"Processing table {table_number} on page {page_number}")

                    if len(table[0]) == 2:
                        for row in table:
                            if "Student Name" in row[0]:
                                data["Student Name"] = row[1].strip()
                                print(f"Extracted Student Name: {data['Student Name']}")
                            if "University Seat Number" in row[0]:
                                data["University Seat Number"] = row[1].strip()
                                print(f"Extracted University Seat Number: {data['University Seat Number']}")

                    
                    
                    elif len(table[0]) >= 3:
                        for row in table:
                            if len(row) >= 3 and row[0].strip() and row[1].strip() and row[2].strip():
                                subject_code = row[0].strip()
                                subject_name = row[1].strip()
                                total_marks = row[4].strip()
                                data["subjects"].append({
                                    "subject_code": subject_code,
                                    "subject_name": subject_name,
                                    "total_marks": total_marks,

                                })

                                try:
                                    total_marks_int = int(total_marks)
                                    if 0 <= total_marks_int <=9:
                                        grader=1
                                    elif 10 <= total_marks_int <= 19:
                                        grader = 2
                                    elif 20 <= total_marks_int <= 29:
                                        grader = 3
                                    elif 30 <= total_marks_int <= 39:
                                        grader = 4
                                    elif 40 <= total_marks_int <= 49:
                                        grader = 5
                                    

                                    
                                    elif 50 <= total_marks_int <= 59:
                                        grader = 6
                                    elif 60 <= total_marks_int <= 69:
                                        grader = 7
                                    elif 70 <= total_marks_int <= 79:
                                        grader = 8
                                    elif 80 <= total_marks_int <= 89:
                                        grader = 9
                                    elif 90 <= total_marks_int <= 100:
                                        grader = 10
                                    else:
                                        grader = None  # Marks out of range or invalid
                                except ValueError:
                                    grader = None
                                print(f"Extracted subject - Code: {subject_code}, Name: {subject_name}, Marks: {total_marks}, Grader: {grader}")
    except Exception as e:
        print(f"Error extracting data: {e}")

    
    
    
    print("Extraction complete")
    return data
    



# Send OTP to the user's email
def send_otp(email, otp):
    sender_email = "temp88953@gmail.com"  # Your email address
    sender_password = "temp@123blr"  # Your email password (for example, App Password)
    recipient_email = email

    # Email server settings (Gmail example)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Prepare email content
    subject = "OTP for Student Registration"
    body = f"Your OTP for registration is: {otp}"

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        print(f"Attempting to send OTP to {email}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message.as_string())
        print(f"OTP sent to {email}")
    except Exception as e:
        print(f"Error sending OTP: {e}")


# Route to handle OTP request
@app.route('/send-otp', methods=['POST'])
def send_otp_route():
    data = request.json
    email = data.get('email')

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    # Validate email to ensure it ends with "@saividya.ac.in"
    if not re.match(r'^[a-zA-Z0-9_.+-]+@saividya\.ac\.in$', email):
        return jsonify({'message': 'Invalid email domain. Please use @saividya.ac.in'}), 400

    # Generate a random OTP
    otp = random.randint(100000, 999999)

    # Send OTP to the provided email
    send_otp(email, otp)

    # Store OTP in the session or database for verification later
    global stored_otp
    stored_otp = otp

    return jsonify({'message': 'OTP sent to your email'}), 200



# Route to verify the OTP
@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    otp = data.get('otp')

    if not otp:
        return jsonify({'message': 'OTP is required'}), 400

    # Verify the OTP
    global stored_otp
    if int(otp) == stored_otp:
        return jsonify({'message': 'OTP verified successfully'}), 200
    else:
        return jsonify({'message': 'Invalid OTP'}), 400


# Route to render the homepage
@app.route('/')
def home():
    return render_template('index.html')



# Route to render the upload PDF page
@app.route('/upload-pdf', methods=['GET'])
def upload_pdf_page():
    return render_template('pdf_upload.html')  # Render the upload page


# Route to process the uploaded PDFs and extract information
@app.route('/process-pdfs', methods=['POST'])
def process_pdfs():
    if 'pdf_files' not in request.files:
        return jsonify({"message": "No files uploaded"}), 400

    extracted_data = []
    files = request.files.getlist('pdf_files')

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        for pdf_file in files:
            data = extract_specific_info_from_pdf(pdf_file)
            student_name = data.get("Student Name")
            university_seat_number = data.get("University Seat Number")
            subjects_data = data.get("subjects")  # Assuming you have a list of subjects

            # Insert student details into the students table
            cursor.execute("""
                INSERT INTO students (student_name, university_seat_number)
                VALUES (%s, %s)
            """, (student_name, university_seat_number))

            student_id = cursor.lastrowid  # Get the student_id of the newly inserted student

            # Insert subjects for the student into the subjects table
            for subject in subjects_data:
                subject_code = subject.get("subject_code")  # Extract from the PDF
                subject_name = subject.get("subject_name")  # Extract from the PDF
                total_marks = subject.get("total_marks", 0)  # Default to 0 if missing

                # Insert each subject in a new row
                cursor.execute("""
                    INSERT INTO subjects (student_id, subject_code, subject_name, total_marks)
                    VALUES (%s, %s, %s, %s)
                """, (student_id, subject_code, subject_name, total_marks))

            connection.commit()  # Commit changes for this student

            extracted_data.append({
                "student_name": student_name,
                "university_seat_number": university_seat_number,
                "subjects": subjects_data
            })

        return jsonify(extracted_data)

    except Error as e:
        return jsonify({"message": f"Error: {e}"}), 500

    finally:
        if connection:
            cursor.close()
            connection.close()




# Route to render the registration page
@app.route('/register-page')
def register_page():
    return render_template('register.html')


# Route to render the student registration page
@app.route('/student-register')
def student_page():
    return render_template('student-register.html')


# Route to render the login page
@app.route('/login-page')
def login_page():
    return render_template('login.html')


# API route to handle user registration
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    usn = data.get('usn')
    semester = data.get('semester')
    grad_year = data.get('grad_year')
    password = data.get('password')

    if not all([name, phone, email, usn, semester, grad_year, password]):
        return jsonify({'message': 'All fields are required'}), 400

    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
        cursor = connection.cursor(dictionary=True)

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE usn = %s OR email = %s", (usn, email))
        if cursor.fetchone():
            return jsonify({'message': 'User already registered'}), 409

        # Hash the password and insert user data
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(""" 
            INSERT INTO users (name, phone, email, usn, semester, grad_year, password, sgpa, cgpa)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, phone, email, usn, semester, grad_year, hashed_password, None, None))
        connection.commit()

        return jsonify({'message': 'Registered successfully!'}), 201
    except Error as e:
        print(f"Error during registration: {e}")
        return jsonify({'message': 'Internal server error'}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()


# API route to handle user login
@app.route('/login', methods=['POST'])
def login():
   
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # Validate email format (ends with @saividya.ac.in)
    if not email.endswith('@saividya.ac.in'):
        return jsonify({'message': 'Invalid email format.'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    # Check if the email exists in the faculty table and match the password
    cursor.execute('SELECT * FROM faculty WHERE email = %s AND password = %s', (email, password))
    faculty_member = cursor.fetchone()

    if faculty_member:
        # Login successful, return success response
        return jsonify({'success': True, 'redirect_url': '/pdf_upload.html'})
    else:
        # Invalid credentials
        return jsonify({'success': False, 'message': 'Invalid email or password.'}), 401
    
@app.route('/register__faculty')
def register__faculty():
    return render_template('faculty_register.html')



@app.route('/register-faculty', methods=['POST'])
def register_faculty():
    # Check if the request data is JSON, then parse it accordingly
    if request.is_json:
        data = request.get_json()
    else:
        # Attempt to parse as form data as a fallback
        data = request.form

    # Extract fields from the request data
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({'message': 'All fields are required'}), 400

    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
        cursor = connection.cursor(dictionary=True)

        # Hash the password before storing it
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert the faculty details into the 'faculty' table
        cursor.execute("""
            INSERT INTO faculty (name, email, password)
            VALUES (%s, %s, %s)
        """, (name, email, hashed_password))
        connection.commit()

        return jsonify({'message': 'Faculty registered successfully!'}), 201

    except Error as e:
        print(f"Error during faculty registration: {e}")
        return jsonify({'message': 'Internal server error'}), 500

    finally:
        if connection:
            cursor.close()
            connection.close()


@app.route('/faculty-login', methods=['POST'])
def faculty_login_post():
    email = request.form['email']
    password = request.form['password'].encode('utf-8')  # Encode the input password

    # Establish connection and query the faculty table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM faculty WHERE email = %s", (email,))
    result = cursor.fetchone()
    conn.close()

    if result:
        stored_password = result[0].encode('utf-8')  # Encode stored hash for bcrypt comparison
        if bcrypt.checkpw(password, stored_password):
            session['faculty_logged_in'] = True
            session['faculty_email'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('faculty_dashboard'))  # Redirect to faculty dashboard
        else:
            flash('Incorrect password. Please try again.', 'danger')
    else:
        flash('Email not found. Please check or register first.', 'warning')

    return redirect(url_for('faculty_login'))

# Route for faculty login page
@app.route('/faculty-login')
def faculty_login():
    return render_template('faculty_login.html')

# Example faculty dashboard route (redirected after login)
@app.route('/faculty-dashboard')
def faculty_dashboard():
    if 'faculty_logged_in' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('faculty_login'))
    return render_template('faculty_dashboard.html')  # Render the faculty dashboard page



if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
