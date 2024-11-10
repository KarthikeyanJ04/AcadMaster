from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import bcrypt
import mysql.connector
from mysql.connector import Error
import fitz  # PyMuPDF for PDF processing
import re

app = Flask(__name__)
CORS(app)

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
                CREATE TABLE IF NOT EXISTS student_details (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_name VARCHAR(100),
                    university_seat_number VARCHAR(20),
                    subject_code VARCHAR(10),
                    subject_name VARCHAR(100)
                )
            """)

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


# PDF Text Extraction for Specific Fields
def extract_specific_info_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as pdf:
        for page in pdf:
            text += page.get_text()

    # Define regex patterns for each field
    seat_number_pattern = re.compile(r"University Seat Number\s*:\s*(\S+)")
    name_pattern = re.compile(r"Student Name\s*:\s*([A-Z\s]+)")
    subject_pattern = re.compile(
        r"(\b[A-Z]{3,4}\d{3}\b)\s+([A-Z &]+)\s+\d+\s+\d+\s+(\d+)\s+([PFWAXNE])"
    )

    # Extract information
    seat_number = seat_number_pattern.search(text)
    name = name_pattern.search(text)
    subjects = subject_pattern.findall(text)

    # Organize data in JSON format
    extracted_data = {
        "university_seat_number": seat_number.group(1) if seat_number else None,
        "student_name": name.group(1).strip() if name else None,
        "subjects": [
            {
                "subject_code": subject[0],
                "subject_name": subject[1].strip(),
                "total": subject[2],
                "result": subject[3]
            }
            for subject in subjects
        ]
    }
    return extracted_data


# Route to render the homepage
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload-pdf', methods=['GET'])
def upload_pdf_page():
    return render_template('pdf_upload.html')  # Render the upload page


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
            student_name = data.get("student_name")
            university_seat_number = data.get("university_seat_number")
            subjects = data.get("subjects")

            # Insert student details into the database
            for subject in subjects:
                cursor.execute("""
                    INSERT INTO student_details (student_name, university_seat_number, subject_code, subject_name)
                    VALUES (%s, %s, %s, %s)
                """, (student_name, university_seat_number, subject["subject_code"], subject["subject_name"]))
            
            connection.commit()  # Commit changes after all subjects are inserted
            extracted_data.append({
                "student_name": student_name,
                "university_seat_number": university_seat_number,
                "subjects": subjects
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
    data = request.json
    usn = data.get('usn')
    password = data.get('password')

    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
        cursor = connection.cursor(dictionary=True)

        # Fetch the user from the database
        cursor.execute("SELECT * FROM users WHERE usn = %s", (usn,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return jsonify({'message': 'Login successful!', 'redirect_url': '/student-corner'}), 200
        else:
            return jsonify({'message': 'Invalid password'}), 401
    except Error as e:
        print(f"Error during login: {e}")
        return jsonify({'message': 'Internal server error'}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()


# Route for student corner
@app.route('/student-corner')
def student_corner():
    return render_template('student_corner.html')  # Ensure this file exists


# Initialize the database and start the Flask app
if __name__ == '__main__':
    initialize_database()
    app.run(port=3000, debug=True)
