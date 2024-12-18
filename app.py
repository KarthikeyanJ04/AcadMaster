from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, Response
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

global Total



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

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS placement (
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

            cursor.execute("""CREATE TABLE IF NOT EXISTS skills (
            usn VARCHAR(20), skills TEXT, PRIMARY KEY (usn), FOREIGN KEY (usn) REFERENCES subject_sgpa(USN))""")


            cursor.execute("""CREATE TABLE IF NOT exists students_sgpa (
            USN VARCHAR(50) PRIMARY KEY,
            student_name VARCHAR(255) NOT NULL,
            SGPA FLOAT)""")

            create_table_query = """
            CREATE TABLE IF NOT EXISTS subject_point (
            subject_code VARCHAR(10) PRIMARY KEY,
            credits INT
            );
            """

            # Insert data query
            insert_data_query = """
            INSERT INTO subject_point (subject_code, credits)
            VALUES
                ('BBOC407', 2),
                ('BCS401', 3),
                ('BCS402', 4),
                ('BCS403', 4),
                ('BCS404', 1),
                ('BCS405A', 3),
                ('BCS405B', 3),
                ('BCS405C', 3),
                ('BCS405D', 3),
                ('BCS456A', 1),
                ('BCS456B', 1),
                ('BCS456C', 1),
                ('BCS456D', 1),
                ('BCSL404', 1),
                ('BUHK408', 1);
            """

            try:
                # Execute the create table query
                cursor.execute(create_table_query)
                print("Table 'subject_point' created successfully.")

                # Execute the insert data query
                cursor.execute(insert_data_query)
                print("Data inserted into 'subject_point' table successfully.")

            

                connection.commit()
                print("Database and tables initialized successfully")

            except MySQLdb.Error as e:
                # Rollback in case of error
                print(f"Error occurred: {e}")
                db.rollback()   
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
import pymysql

pymysql.install_as_MySQLdb()
import MySQLdb



def get_subject_credits(subject_code):
    """ Fetch subject credits from the subject_point table using the subject_code """
    try:
        # Establish the database connection
        connection = MySQLdb.connect(
        host='localhost',  # or '127.0.0.1'
        user='root',
        password='jaikarthik',
        database='user_data'
        )
        cursor = connection.cursor()

        # Query to fetch credits for the given subject_code
        query = "SELECT credits FROM subject_point WHERE subject_code = %s"
        cursor.execute(query, (subject_code,))
        result = cursor.fetchone()

        # If subject_code found, return the credits
        if result:
            return result[0]
        else:
            print(f"Subject code {subject_code} not found in the database.")
            return 0
    except Exception as e:
        print(f"Error fetching subject credits: {e}")
        return 0
    finally:
        cursor.close()
        connection.close()

def extract_specific_info_from_pdf(pdf_file):
    data = {"Student Name": None, "University Seat Number": None, "subjects": []}
    Total = 0
    credit = 0
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
                                data["Student Name"] = row[1].strip().replace(":", "").strip()
                                print(f"Extracted Student Name: {data['Student Name']}")
                            if "University Seat Number" in row[0]:
                                data["University Seat Number"] = row[1].strip().replace(":", "").strip()
                                print(f"Extracted University Seat Number: {data['University Seat Number']}")

                    elif len(table[0]) >= 3:
                        for row in table:
                            if len(row) >= 3 and row[0].strip() and row[1].strip() and row[2].strip():
                                subject_code = row[0].strip()
                                subject_name = row[1].strip()
                                total_marks = row[4].strip()

                                # Fetch the credits for the subject
                                credits = get_subject_credits(subject_code)
                                
                                # Ensure that credits are an integer, and if not, handle gracefully
                                if not isinstance(credits, int) or credits <= 0:
                                    print(f"Invalid or missing credits for subject {subject_code}. Skipping.")
                                    continue

                                # Ensure total_marks is an integer
                                try:
                                    total_marks_int = int(total_marks)
                                    if 50 <= total_marks_int <= 59:
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
                                    grader = None  # In case total_marks is not a valid number

                                # If grader is valid, multiply by credits
                                if grader is not None:
                                    total_points = grader * credits
                                    data["subjects"].append({
                                        "subject_code": subject_code,
                                        "subject_name": subject_name,
                                        "total_marks": total_marks,
                                        "grader": grader,
                                        "credits": credits,
                                        "total_points": total_points
                                    })
                                    print(f"Extracted subject - Code: {subject_code}, Name: {subject_name}, Marks: {total_marks}, Grader: {grader}, Credits: {credits}, Total Points: {total_points}")

                                    Total = Total + total_points
                                    credit = credit + credits
                                    
                                else:
                                    print(f"Invalid grader for subject {subject_code}. Skipping.")
    except Exception as e:
        print(f"Error extracting data: {e}")

    print("Extraction complete")
    print("Total points:", Total)
    
    SGPA = Total / credit
    SGPA = round(SGPA, 2)
    print("SGPA:", SGPA)
    
    return data, SGPA  # Ensure we return both data and SGPA as expected.


    



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
            # Extract the data and SGPA
            data, SGPA = extract_specific_info_from_pdf(pdf_file)
            student_name = data.get("Student Name")
            university_seat_number = data.get("University Seat Number")
            

            # Insert student details into the students table
            cursor.execute("""
            INSERT INTO students_sgpa (USN, student_name, SGPA)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE SGPA = %s
            """, (university_seat_number, student_name, SGPA, SGPA))  # Store SGPA here

            student_id = cursor.lastrowid  # Get the student_id of the newly inserted student

            
            connection.commit()  # Commit changes for this student

            extracted_data.append({
                "student_name": student_name,
                "university_seat_number": university_seat_number,
                "SGPA": SGPA  # Include SGPA in the response
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

@app.route('/register__placement')
def register__placement():
    return render_template('placement_register.html')



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

@app.route('/register-placement', methods=['POST'])
def register_placement():
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
        cursor.execute("""CREATE TABLE IF NOT EXISTS PLACEMENT (name VARCHAR(100),
                    email VARCHAR(100) UNIQUE,
                    password VARCHAR(255))""")
        
        cursor.execute("""
            INSERT INTO placement (name, email, password)
            VALUES (%s, %s, %s)
        """, (name, email, hashed_password))
        connection.commit()

        return jsonify({'message': 'Placement Faculty registered successfully!'}), 201

    except Error as e:
        print(f"Error during placement faculty registration: {e}")
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

@app.route('/placement-faculty-login', methods=['POST'])
def placement_login():
    data = request.json
    if not data:
        return jsonify({"message": "Invalid request format"}), 400
    email = data.get('email').strip().lower()
    password = data.get('password').strip()

    try:
        db = MySQLdb.connect(host="localhost", user="root", passwd="jaikarthik", db="user_data")
        cursor = db.cursor()

        cursor.execute("SELECT password FROM placement WHERE email = %s", (email,))
        result = cursor.fetchone()

        if result:
            stored_hashed_password = result[0]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
                session['placement_logged_in'] = True
                session['email'] = email
                db.close()
                
                # Redirect to the placement faculty dashboard after successful login
                return redirect(url_for('placement_dashboard'))  # 'placement_dashboard' is the name of the view you want to redirect to
            else:
                db.close()
                return jsonify({"message": "Invalid email or password"}), 401
        else:
            db.close()
            return jsonify({"message": "Invalid email or password"}), 401

    except MySQLdb.MySQLError as e:
        return jsonify({"message": f"Database error: {str(e)}"}), 500




# Route for faculty login page
@app.route('/placement-faculty-login')
def placement_faculty_login():
    return render_template('placement_login.html')

@app.route('/placement-faculty-dashboard')
def placement_dashboard():
    if 'placement_logged_in' not in session:
        return redirect(url_for('placement_login'))  # Redirect to login if not logged in
    return render_template('placement_dashboard.html')


# Example faculty dashboard route (redirected after login)
@app.route('/faculty-dashboard')
def faculty_dashboard():
    
    if 'faculty_logged_in' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('faculty_login'))
    return render_template('faculty_dashboard.html')  # Render the faculty dashboard page

@app.route('/export_sgpa_csv', methods=['GET'])
def export_sgpa_csv():
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query to select SGPA data
    cursor.execute("SELECT USN, student_name, SGPA FROM students_sgpa")
    rows = cursor.fetchall()

    # Prepare the CSV file
    def generate():
        # Write header to CSV
        yield 'USN,Student Name,SGPA\n'
        
        # Write data rows
        for row in rows:
            yield f'{row[0]},{row[1]},{row[2]}\n'

    # Close the database connection
    cursor.close()
    conn.close()

    # Set the appropriate header for CSV file download
    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=sgpa_data.csv'})

@app.route('/view-students', methods=['GET'])
def view_students():
    try:
        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch data from the students_sgpa table
        cursor.execute("SELECT student_name, USN, SGPA FROM students_sgpa ORDER BY SGPA DESC")
        results = cursor.fetchall()

        print("Fetched Results:", results)

        # Close the connection
        cursor.close()
        connection.close()

        # Return the data as JSON
        return jsonify(results)

        

    except MySQLdb.Error as db_err:
        print("Database Error:", db_err)
        return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        print("Unexpected Error:", e)
        return jsonify({"error": "Unexpected error occurred"}), 500
    
@app.route('/enter-skills/<usn>')
def enter_skills(usn):
    return render_template('enter_skills.html', usn=usn)

# Route to save skills
@app.route('/save-skills/<usn>', methods=['POST'])
def save_skills(usn):
    data = request.get_json()
    new_skills = data.get('skills', '')

    try:
        # Connect to MySQL database
        db = MySQLdb.connect(host="localhost", user="root", passwd="jaikarthik", db="user_data")
        cursor = db.cursor()

        # Check if the student already has skills in the database
        cursor.execute("SELECT skills FROM skills WHERE usn = %s", (usn,))
        existing_skills = cursor.fetchone()

        if existing_skills:
            # If skills exist, append the new skills to the existing ones
            updated_skills = existing_skills[0] + ', ' + new_skills
            cursor.execute("UPDATE skills SET skills = %s WHERE usn = %s", (updated_skills, usn))
        else:
            # If no skills exist for the student, insert the new skills
            cursor.execute("INSERT INTO skills (usn, skills) VALUES (%s, %s)", (usn, new_skills))

        db.commit()
        db.close()
        
        return jsonify({"message": "Skills saved successfully!"}), 200

    except MySQLdb.MySQLError as e:
        # Log the error for debugging purposes
        print(f"Error saving skills: {str(e)}")  # This will show up in the Flask console
        return jsonify({"message": f"Error saving skills: {str(e)}"}), 500

    

# Database connection function to avoid repetitive code
def get_db_connection():
    return pymysql.connect(
        host="localhost",
        user="root",       # Replace with your username
        passwd="jaikarthik",  # Replace with your password
        db="user_data",    # Replace with your database name
    )


@app.route('/students-with-skill', methods=['POST'])
def students_with_skill():
    # Get the skill from the frontend
    data = request.get_json()
    skill = data.get('skill')

    # Connect to the remote MySQL database
    db = pymysql.connect(
        host="localhost",
        user="root",       
        passwd="jaikarthik",     
        db="user_data",    
    )
    cursor = db.cursor()

    # Query to get students who have the skill (using LIKE to match comma-separated skills)
    query = """
        SELECT s.usn, s.student_name, s.sgpa
        FROM students_sgpa s
        JOIN skills sk ON s.usn = sk.usn
        WHERE sk.skills LIKE %s
    """
    # Add the skill surrounded by commas to match the comma-separated list
    skill_search = f"%{skill}%"  # Use % as a wildcard for LIKE query
    cursor.execute(query, (skill_search,))
    result = cursor.fetchall()

    # Return the students as a JSON response
    students = [{"usn": row[0], "name": row[1], "sgpa": row[2]} for row in result]
    db.close()
    return jsonify({"students": students})





@app.route('/student-details/<usn>', methods=['GET'])
def student_details(usn):
    try:
        # Connect to the database
        db = get_db_connection()
        cursor = db.cursor()

        # Query to retrieve student name, SGPA, and skills from the corresponding tables
        query = """
            SELECT ss.student_name, ss.sgpa, sk.skills
            FROM students_sgpa ss
            LEFT JOIN skills sk ON ss.usn = sk.usn
            WHERE ss.usn = %s
        """
        cursor.execute(query, (usn,))
        result = cursor.fetchall()

        db.close()

        if result:
            # Parse the results
            student_name = result[0][0]
            sgpa = result[0][1]
            skills = [row[2] for row in result if row[2]]  # Only include non-null skills

            return jsonify({"name": student_name, "sgpa": sgpa, "skills": skills})
        else:
            return jsonify({"error": "Student not found"}), 404

    except pymysql.MySQLError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/get-skills/<student_usn>', methods=['GET'])
def get_skills(student_usn):
    try:
        # Connect to the database
        db = get_db_connection()
        cursor = db.cursor()

        # Query to fetch skills for the specific student based on USN
        query = "SELECT skills FROM skills WHERE usn = %s"
        cursor.execute(query, (student_usn,))
        skills_data = cursor.fetchall()

        db.close()

        if skills_data:
            # skills_data is a list of tuples, so we need to extract the skills
            skills = [skill[0] for skill in skills_data]
            return jsonify({"skills": skills})  # Return a JSON response with skills data
        else:
            return jsonify({"message": "No skills data found for this student"}), 404

    except pymysql.MySQLError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500












if __name__ == '__main__':
    initialize_database()
    app.run(debug=True)
