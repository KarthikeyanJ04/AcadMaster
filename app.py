from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': 'Root@nur1n24',  # Replace with your MySQL password
    'database': 'user_data'  # Replace with your database name
}

# Connect to MySQL database
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return None

# Route for user registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')
    email = data.get('email')
    usn = data.get('usn')
    semester = data.get('semester')
    grad_year = data.get('grad_year')
    password = data.get('password')

    # Check if all fields are provided
    if not all([name, phone, email, usn, semester, grad_year, password]):
        return jsonify({'message': 'All fields are required'}), 400

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            # Check if user already exists
            cursor.execute("SELECT * FROM users WHERE usn = %s OR email = %s", (usn, email))
            if cursor.fetchone():
                return jsonify({'message': 'User already registered'}), 409

            # Hash the password and insert the user data
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute(
                "INSERT INTO users (name, phone, email, usn, semester, grad_year, password, sgpa, cgpa) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (name, phone, email, usn, semester, grad_year, hashed_password, None, None)
            )
            connection.commit()
            return jsonify({'message': 'Registered successfully!'}), 201

        except Error as e:
            print(f"Error during registration: {e}")
            return jsonify({'message': 'Internal server error'}), 500

        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'message': 'Database connection failed'}), 500

# Route for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    usn = data.get('usn')
    password = data.get('password')

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE usn = %s", (usn,))
            user = cursor.fetchone()
            if user and bcrypt.check_password_hash(user['password'], password):
                return jsonify({'message': 'Login successful!', 'user': user}), 200
            else:
                return jsonify({'message': 'Invalid USN or password'}), 401

        except Error as e:
            print(f"Error during login: {e}")
            return jsonify({'message': 'Internal server error'}), 500

        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'message': 'Database connection failed'}), 500

# Route to update SGPA and CGPA
@app.route('/update-sgpa-cgpa', methods=['POST'])
def update_sgpa_cgpa():
    data = request.get_json()
    usn = data.get('usn')
    sgpa = data.get('sgpa')
    cgpa = data.get('cgpa')

    # Check if all fields are provided
    if not all([usn, sgpa, cgpa]):
        return jsonify({'message': 'All fields are required'}), 400

    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
        try:
            cursor.execute("UPDATE users SET sgpa = %s, cgpa = %s WHERE usn = %s", (sgpa, cgpa, usn))
            connection.commit()
            return jsonify({'message': 'SGPA and CGPA updated successfully!'}), 200

        except Error as e:
            print(f"Error updating SGPA and CGPA: {e}")
            return jsonify({'message': 'Internal server error'}), 500

        finally:
            cursor.close()
            connection.close()
    else:
        return jsonify({'message': 'Database connection failed'}), 500

# Test route to check if the server is working
@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'Fetch working!'})

# Start the Flask server
if __name__ == '__main__':
    app.run(port=3000, debug=True)
