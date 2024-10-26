from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import bcrypt
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
CORS(app)

# Initial database configuration without specifying the database
db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': 'jaikarthik',  # Replace with your MySQL password
}

# Database configuration with the database specified, for use after initialization
db_config_with_database = db_config.copy()
db_config_with_database['database'] = 'user_data'


# Initialize the database if it doesn't exist
def initialize_database():
    try:
        # Connect to MySQL without specifying the database initially
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS user_data")
            cursor.execute("USE user_data")  # Switch to the new database

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


# Route to render the homepage
@app.route('/')
def home():
    return render_template('index.html')  # Main homepage


# Route to render the registration page
@app.route('/register-page')
def register_page():
    print("Accessing register page")
    return render_template('register.html')  # Registration page


# Route to render the login page
@app.route('/login-page')
def login_page():
    print("Accessing login page")
    return render_template('login.html')  # Login page


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
            return jsonify({'message': 'Login successful!', 'user': user}), 200
        else:
            return jsonify({'message': 'Invalid password'}), 401
    except Error as e:
        print(f"Error during login: {e}")
        return jsonify({'message': 'Internal server error'}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()


# API route to update SGPA and CGPA
@app.route('/update-sgpa-cgpa', methods=['POST'])
def update_sgpa_cgpa():
    data = request.json
    usn = data.get('usn')
    sgpa = data.get('sgpa')
    cgpa = data.get('cgpa')

    if not all([usn, sgpa, cgpa]):
        return jsonify({'message': 'All fields are required'}), 400

    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({'message': 'Database connection failed'}), 500
        cursor = connection.cursor()

        # Update SGPA and CGPA in the database
        cursor.execute("UPDATE users SET sgpa = %s, cgpa = %s WHERE usn = %s", (sgpa, cgpa, usn))
        connection.commit()

        return jsonify({'message': 'SGPA and CGPA updated successfully!'}), 200
    except Error as e:
        print(f"Error updating SGPA and CGPA: {e}")
        return jsonify({'message': 'Internal server error'}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()


# Test route to check if the server is working
@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Fetch working!'})


# Initialize the database and start the Flask app
if __name__ == '__main__':
    initialize_database()
    app.run(port=3000)
