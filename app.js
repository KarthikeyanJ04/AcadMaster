const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const bcrypt = require('bcrypt');
const mysql = require('mysql2/promise'); // Use promise-based MySQL
const app = express();
const port = 3000;

// Enable CORS for all requests
app.use(cors());
app.use(bodyParser.json());

// Create MySQL connection
const dbConfig = {
  host: 'localhost',
  user: 'root', // Change to your MySQL username
  password: 'Root@nur1n24', // Change to your MySQL password
  database: 'user_data', // Change to your database name
};

let connection;

// Function to establish a database connection
async function initDb() {
  connection = await mysql.createConnection(dbConfig);
}

// POST route to handle registration
app.post('/register', async (req, res) => {
  const { name, phone, email, usn, semester, grad_year, password } = req.body;

  // Validate the input data
  if (!name || !phone || !email || !usn || !semester || !grad_year || !password) {
    return res.status(400).json({ message: 'All fields are required' });
  }

  try {
    // Check if the user is already registered
    const [rows] = await connection.execute('SELECT * FROM users WHERE usn = ? OR email = ?', [usn, email]);
    if (rows.length > 0) {
      return res.status(409).json({ message: 'User already registered' });
    }

    // Hash the password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Insert user data into the database with sgpa and cgpa initialized to NULL
    await connection.execute(
      'INSERT INTO users (name, phone, email, usn, semester, grad_year, password, sgpa, cgpa) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [name, phone, email, usn, semester, grad_year, hashedPassword, null, null] // Set sgpa and cgpa to null
    );

    res.status(201).json({ message: 'Registered successfully!' });
  } catch (error) {
    console.error('Error during registration:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// POST route to handle login
app.post('/login', async (req, res) => {
  const { usn, password } = req.body;

  try {
    const [rows] = await connection.execute('SELECT * FROM users WHERE usn = ?', [usn]);
    const user = rows[0];
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    // Compare the hashed password
    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
      return res.status(401).json({ message: 'Invalid password' });
    }

    // Login successful
    res.status(200).json({ message: 'Login successful!', user });
  } catch (error) {
    console.error('Error during login:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// POST route to update SGPA and CGPA
app.post('/update-sgpa-cgpa', async (req, res) => {
  const { usn, sgpa, cgpa } = req.body;

  // Validate the input data
  if (!usn || sgpa === undefined || cgpa === undefined) {
    return res.status(400).json({ message: 'All fields are required' });
  }

  try {
    // Update SGPA and CGPA in the database
    await connection.execute(
      'UPDATE users SET sgpa = ?, cgpa = ? WHERE usn = ?',
      [sgpa, cgpa, usn]
    );

    res.status(200).json({ message: 'SGPA and CGPA updated successfully!' });
  } catch (error) {
    console.error('Error updating SGPA and CGPA:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// Test route to check if the server is working
app.get('/test', (req, res) => {
  res.json({ message: 'Fetch working!' });
});

// Start the server
initDb().then(() => {
  app.listen(port, () => {
    console.log(`Server running on http://localhost:${port}`);
  });
}).catch(err => {
  console.error('Failed to connect to the database:', err);
});
