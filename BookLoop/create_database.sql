-- BookLoop uses five related MySQL tables.
-- database.py creates bookloop_db before it runs these statements.

CREATE TABLE IF NOT EXISTS Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    student_class VARCHAR(20) NOT NULL,
    whatsapp_number VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS Books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    book_name VARCHAR(150) NOT NULL,
    author VARCHAR(100) NOT NULL,
    subject VARCHAR(80) NOT NULL,
    book_class VARCHAR(20) NOT NULL,
    original_price DECIMAL(10, 2) NOT NULL,
    book_condition VARCHAR(20) NOT NULL,
    exchange_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Available',
    date_added DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES Students(student_id)
);

CREATE TABLE IF NOT EXISTS Requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    requester_id INT NOT NULL,
    request_status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    request_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES Books(book_id),
    FOREIGN KEY (requester_id) REFERENCES Students(student_id)
);

CREATE TABLE IF NOT EXISTS Exchanges (
    exchange_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL UNIQUE,
    exchange_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exchange_status VARCHAR(20) NOT NULL DEFAULT 'Completed',
    FOREIGN KEY (request_id) REFERENCES Requests(request_id)
);

CREATE TABLE IF NOT EXISTS Admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);
