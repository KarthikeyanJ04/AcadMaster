CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    usn VARCHAR(20) NOT NULL UNIQUE,
    semester INT NOT NULL,
    grad_year INT NOT NULL,
    password VARCHAR(255) NOT NULL
);