# BookLoop practical project guide

This guide explains the BookLoop files in simple terms so that the project can be demonstrated and discussed in a CBSE Class 12 IP practical. Flask, HTML, CSS, Werkzeug password helpers and Matplotlib are supporting tools for this website. They are not described as prescribed IP syllabus topics.

## 1. Project synopsis

BookLoop is a student book exchange portal. Students register, list used academic books, search books listed by others and request an available book. The owner accepts or rejects a request. If accepted, the book is reserved until the students complete the physical exchange. WhatsApp Click-to-Chat opens a prepared message to help the relevant students coordinate. An administrator can review students, listings, requests and completed exchanges.

The portal aims to make academic books easier to reuse and help students find books at a lower cost. It records listings and request activity in MySQL. The estimated savings shown by the admin page use the original listed price of completed exchange books; the figure is an estimate, not a payment record.

## 2. Problem definition, objectives and scope

### Problem definition

Students may have used academic books they no longer need, while other students are looking for the same books. Informal messages and scattered listings make it harder to find a book, check its availability and track a request.

### Objectives

1. Keep student accounts and book listings in a structured database.
2. Let students search by book name, author, subject, class and condition.
3. Record requests and update their status in MySQL.
4. Prevent a student from requesting their own book or requesting a book that is unavailable.
5. Help the students coordinate through WhatsApp Click-to-Chat.
6. Show the administrator basic totals and charts.

### Scope and limits

BookLoop is a small local demonstration website. It records listings and exchange status, but it does not make payments, verify student identity, arrange delivery or send WhatsApp messages automatically. The physical handover is arranged by the students. The included default book image keeps listings simple; image uploading is not included.

## 3. Requirements and project architecture

### Software and hardware

| Type | Requirement |
|---|---|
| Hardware | Computer or laptop, keyboard, mouse or touchpad, and internet access when opening WhatsApp |
| Operating system | Windows, macOS or Linux that can run Python and MySQL |
| Software | Python 3.10+, MySQL Server, a modern browser and a text editor |
| Python packages | Flask, mysql-connector-python and Matplotlib |
| Supporting package | Werkzeug is installed as part of Flask and provides password hashing helpers |

### Architecture

```text
Browser pages (HTML and CSS)
        ↓ form submission
Flask routes in app.py
        ↓ parameterised SQL statements
MySQL database bookloop_db

app.py → whatsapp.py → wa.me link → WhatsApp
app.py → Matplotlib → statistics chart image
```

An HTML form sends named values to a Flask route. The route reads them with `request.form` or `request.args`, checks them, and sends values with a parameterised SQL query. MySQL returns rows to Python; Flask passes those rows into a template, and the browser displays the page.

## 4. Main user flow

```text
Start
  ↓
Register or log in
  ↓
Add a book ───────────────→ book status = Available
  ↓                                  ↓
Browse / search books ←──────────────┘
  ↓
Request another student's available book
  ↓
Request stored as Pending
  ↓
Owner accepts or rejects
  ├── Reject → request status = Rejected; book stays Available
  └── Accept → request = Accepted; book = Reserved
                    ↓
         Students coordinate through WhatsApp
                    ↓
         Physical handover takes place
                    ↓
         Request = Completed; book = Exchanged
         Add a row to Exchanges
```

## 5. Database schema and relationships

The five tables are `Students`, `Books`, `Requests`, `Exchanges` and `Admins`. Each `*_id` primary key is an automatically generated integer. A foreign key stores the ID of a related row.

| Table | Important columns | Relationship and purpose |
|---|---|---|
| Students | `student_id`, `name`, `email`, `password_hash`, `student_class`, `whatsapp_number` | One student can list many books and make many requests. Email is unique. |
| Books | `book_id`, `student_id`, `book_name`, `author`, `subject`, `book_class`, `original_price`, `book_condition`, `exchange_type`, `status`, `date_added` | Each book belongs to one student. `student_id` references Students. |
| Requests | `request_id`, `book_id`, `requester_id`, `request_status`, `request_date` | Each request refers to one book and one requesting student. |
| Exchanges | `exchange_id`, `request_id`, `exchange_date`, `exchange_status` | A completed exchange refers to one request. `request_id` is unique here. |
| Admins | `admin_id`, `username`, `password_hash` | Separate credentials for the simple admin area. |

```text
Students 1 ───── many Books
Students 1 ───── many Requests (as requester)
Books    1 ───── many Requests
Requests 1 ───── 0 or 1 Exchanges
```

The table design uses `student_class` and `book_class` instead of using `class` as a column name. Passwords are saved as hashes. WhatsApp numbers are used only after a related request or donation enquiry is checked; they do not appear on public cards or admin tables.

### Important SQL used

```sql
CREATE DATABASE IF NOT EXISTS bookloop_db;
```

This is run by `database.py`. The table statements are in `create_database.sql`.

```sql
SELECT Books.book_name, Students.name
FROM Books JOIN Students ON Books.student_id = Students.student_id
WHERE Books.status = 'Available'
ORDER BY Books.date_added DESC;
```

This joins a book to its owner and shows the newest available books first.

```sql
INSERT INTO Requests (book_id, requester_id, request_status)
VALUES (%s, %s, 'Pending');
```

The `%s` marks are placeholders. Python supplies the values separately, so user input is not pasted into the SQL text.

```sql
SELECT subject, COUNT(*) AS total
FROM Books
WHERE status <> 'Removed'
GROUP BY subject
ORDER BY total DESC;
```

This groups listings by subject, counts each group and sorts the most common subject first. The statistics page also uses `COUNT()`, `SUM()` and `AVG()`.

## 6. File and function explanations

### `database.py`

This file stores MySQL connection settings and creates the database, tables and first admin account.

- `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `DATABASE_NAME`: settings to change for the local MySQL installation.
- `get_db_connection()`: opens a connection to `bookloop_db` and returns it to the calling function.
- `create_database_and_tables()`: connects without selecting a database, runs `CREATE DATABASE`, reconnects to `bookloop_db`, reads the SQL file, and runs each table statement. The `for` loop executes one statement at a time.
- `create_first_admin()`: counts admin records. If none exist, it asks for a username and password, hashes the password, and inserts the admin. It does not print the password.
- `if __name__ == "__main__"`: runs database setup when this file is started directly.

### `app.py`

This file contains Flask routes. A route connects a website address and HTTP action to a Python function. Flask's `@app.route` decorator is required for that connection; it is a Flask feature, not an IP syllabus claim.

- `close_database(connection, cursor)`: closes database resources after a query.
- `get_whatsapp_button_message(action, phone_number, book_name)`: selects the prepared message function for the requested WhatsApp action.
- `home()`: loads the six most recent available books for the home page.
- `register()`: reads the registration form, checks required values and the phone number, checks that the email is unused, hashes the password, then inserts a student.
- `login()`: looks up the email and checks the entered password against its stored hash. It saves the student ID in the Flask session after a successful login.
- `admin_login()`: checks the separate Admins table and sets an admin session.
- `logout()`: clears the session so the account is logged out.
- `dashboard()`: uses `COUNT()` queries to show the student's books, incoming requests, outgoing requests, accepted requests and completed exchanges.
- `add_book()`: checks the price and the allowed condition and exchange type, then inserts the book with status `Available`.
- `browse_books()`: reads search filters, adds fixed SQL conditions where needed and supplies the search text separately as parameters. It joins Books and Students to show the owner's name.
- `request_book(book_id)`: checks the student is logged in, the book exists and is available, the owner is not the requester, and there is no pending duplicate request. It then inserts a Pending request.
- `my_books()`: selects listings belonging to the logged-in student.
- `requests_page()`: gets incoming and outgoing requests with JOIN queries and displays status controls.
- `update_request(request_id, action)`: checks that the current student owns the book and that the request is Pending. Accepting reserves the book and rejects other pending requests for it. Rejecting leaves the book available.
- `complete_exchange(request_id)`: checks that the request is Accepted and that the current student is one of the two participants. It updates the request and book, then inserts an Exchanges row.
- `open_whatsapp()`: checks the logged-in student is involved in the donation or request before loading the other student's phone number. It calls the matching message function. The number is never sent to a public template.
- `admin_dashboard()`: checks the admin session and loads student, book, request and exchange tables for review.
- `admin_delete_book(book_id)`: deletes a listing with no request history. If the listing has request history, it marks it `Removed` so foreign-key history is preserved.
- `statistics()`: uses aggregate SQL queries, creates a bar chart and pie chart with Matplotlib, and displays the totals.

### `whatsapp.py`

This file uses only the standard-library modules `urllib.parse` and `webbrowser` for Click-to-Chat.

- `clean_phone_number(phone)`: keeps digits and accepts common formatting characters, then checks for 10 to 15 digits.
- `make_whatsapp_url(phone, message)`: applies `urllib.parse.quote()` to the message and builds `https://wa.me/PHONE_NUMBER?text=ENCODED_MESSAGE`.
- `send_whatsapp(phone, message)`: validates the number, calls `webbrowser.open()` with the URL, and returns whether the number was accepted.
- `send_request_message(...)`: prepares a new-request notification.
- `send_acceptance_message(...)`: prepares an acceptance message for the requester.
- `send_rejection_message(...)`: prepares a rejection message for the requester.
- `send_donation_enquiry(...)`: prepares a donation enquiry for the owner.
- `send_exchange_coordination(...)`: prepares an exchange coordination message.

`urllib.parse.quote()` encodes spaces, line breaks and punctuation so they can be included in a URL. `webbrowser.open()` asks the computer running Python to open that URL. WhatsApp displays a draft message. The user must check it and press Send; BookLoop does not deliver the message automatically. Since the project is intended for local use, Flask and the browser should run on the same computer. If someone visits a remote Flask server, `webbrowser.open()` runs on the server computer.

### HTML templates and CSS

- `base.html` is the shared page frame with navigation, message alerts and footer links. Other templates extend it.
- `index.html` shows the introduction, purpose, recent listings and three-step explanation.
- `register.html` and `login.html` collect student and admin login data.
- `dashboard.html` shows the student's activity counts.
- `add_book.html` collects book details.
- `browse_books.html` has search filters and book cards. Forms submit requests and WhatsApp actions to Flask routes.
- `my_books.html` displays a student's own listings.
- `requests.html` displays incoming and outgoing requests and the relevant actions.
- `admin.html` displays admin-only tables.
- `statistics.html` displays database counts and the Matplotlib chart.
- `static/css/style.css` sets the white/light-blue colours, cards, forms, tables and responsive layout.
- `static/images/default-book.svg` is the default cover image used for every listing.

HTML forms use `method="post"` for changes. For example, the add-book form sends fields such as `book_name` and `author`; Flask reads those names from `request.form`, validates the values and inserts them into MySQL.

## 7. Request and WhatsApp rules

1. The requester submits the book ID from an available book card.
2. Python checks the book exists, is Available and belongs to someone else.
3. Python checks for an existing Pending request from that student for the same book.
4. The request is inserted with status Pending.
5. The owner sees the request on the incoming side of the Requests page.
6. Accepting changes the request to Accepted and the book to Reserved. Other pending requests for that book become Rejected.
7. The participants can open the relevant prepared WhatsApp message and arrange the exchange.
8. After the physical handover, either participant can mark the accepted request complete. Python updates the status and inserts an Exchanges row.

The `open_whatsapp()` route only provides phone details after checking the current account's relationship to the book or request. It does not display those numbers.

## 8. Testing checklist and expected results

| Check | Expected result |
|---|---|
| Register with a new email | Student account is inserted and an ID is generated. |
| Register using the same email again | Registration is refused. |
| Log in with correct password | Student dashboard opens. |
| Add a book | It appears in My Books and Browse Books with Available status. |
| Search by title, author, subject, class or condition | Only matching available books are shown. |
| Request someone else's available book | One Pending request is created. |
| Request one's own book | Request is refused. |
| Submit the same Pending request twice | The second request is refused. |
| Request a Reserved or Exchanged book | Request is refused. |
| Accept as the book owner | Request becomes Accepted; book becomes Reserved; other Pending requests are rejected. |
| Accept as another student | Action is refused. |
| Reject a request | Status becomes Rejected; book remains Available. |
| Complete an accepted exchange as a participant | Request becomes Completed; book becomes Exchanged; Exchanges gets one row. |
| Complete as a student not involved | Action is refused. |
| Click WhatsApp action | WhatsApp opens with a prepared message; user must manually press Send. |
| Browse books or admin records | No student's WhatsApp number appears publicly. |
| Sign in as admin | Admin lists and statistics are available; a student cannot open those pages. |
| Remove a book with request history | It is marked Removed; history stays connected. |

## 9. CBSE practical viva questions and answers

1. **What is BookLoop?** A website for students to list, find, request and exchange used academic books.
2. **What problem does it address?** It helps connect students who have books with students who need them.
3. **Which database does it use?** MySQL, in a database named `bookloop_db`.
4. **What is a primary key?** A field that uniquely identifies each row in a table.
5. **What is a foreign key?** A field that links a row to a related row in another table.
6. **Why is `student_id` in Books?** It identifies the student who owns each listing.
7. **Why are there five tables?** To keep students, books, requests, exchanges and admin accounts in separate related groups.
8. **What does `CREATE TABLE` do?** It creates a table structure in a database.
9. **What does `INSERT` do?** It adds a new row to a table.
10. **What does `SELECT` do?** It retrieves data from one or more tables.
11. **What does `UPDATE` do?** It changes values in existing rows.
12. **What does `DELETE` do?** It removes selected rows from a table.
13. **What does `WHERE` do?** It limits a query to rows meeting a condition.
14. **Why use `ORDER BY`?** To display rows in a chosen order, such as newest books first.
15. **What does `GROUP BY` do?** It groups rows that share a value, such as the same subject.
16. **What does `COUNT()` calculate?** The number of rows in a result or group.
17. **What does `SUM()` calculate?** The total of numeric values, used for estimated saved money.
18. **What does `AVG()` calculate?** The arithmetic average of numeric values.
19. **What does a JOIN do?** It combines related rows from tables using matching key values.
20. **What is a parameterised query?** SQL with placeholders whose values are supplied separately by Python.
21. **Why use parameterised queries?** They keep user input separate from SQL text and help prevent SQL injection.
22. **What is a Python function?** A named set of instructions that performs a task and can be reused.
23. **What is a variable?** A named place to store a value while a program runs.
24. **Where are conditions used?** To check login, book availability, ownership and request status.
25. **Where is a loop used?** To execute each SQL table command and to prepare chart label lists.
26. **What is Flask used for here?** It connects website URLs and HTML forms to Python functions.
27. **What does an HTML form do?** It collects user input and sends it to a Flask route.
28. **What does CSS do?** It controls the layout, colours, spacing and appearance of the pages.
29. **How is the student ID created?** MySQL assigns it with `AUTO_INCREMENT` when a student row is inserted.
30. **How are passwords stored?** As password hashes, not as readable password text.
31. **What is a session?** A way for Flask to remember that a student or admin has logged in between page requests.
32. **How does BookLoop prevent requesting one's own book?** It compares the listing owner's ID with the logged-in student ID.
33. **How does BookLoop prevent duplicate pending requests?** It searches Requests for the same book, requester and Pending status before inserting.
34. **What happens when a request is accepted?** The request becomes Accepted and the book becomes Reserved.
35. **When is Exchanges updated?** After a participant marks an accepted physical handover completed.
36. **What is WhatsApp Click-to-Chat?** A `wa.me` URL that opens a chat with a prepared message.
37. **Why use `urllib.parse.quote()`?** It encodes the message so spaces and line breaks work in the URL.
38. **What does `webbrowser.open()` do?** It asks the computer running Python to open the URL in a browser.
39. **Does BookLoop automatically send a WhatsApp message?** No. The user must review the draft and press Send.
40. **How are charts made?** SQL groups counts by subject or class; Matplotlib draws a bar chart and a pie chart.

## 10. Short demonstration script

“My project is BookLoop, a student book exchange portal. First, I will register two sample students and log in. I will add a book from the first account, then use the second account to search for it and send a request. The request appears as Pending in the owner's incoming requests. The owner can accept or reject it. On acceptance, BookLoop reserves the book so it cannot be requested again. The students can open a prepared WhatsApp message and arrange the handover themselves. After the handover, one participant marks it complete. The portal records the exchange in MySQL. Finally, I will show the admin records and the subject/class statistics. WhatsApp messages are never sent automatically.”

## 11. Bibliography

- Sumita Arora, *Informatics Practices* textbook used by the school, Classes XI and XII.
- Python URL quoting: https://docs.python.org/3/library/urllib.parse.html
- Python browser module: https://docs.python.org/3/library/webbrowser.html
- MySQL Connector/Python Developer Guide: https://dev.mysql.com/doc/connector-python/en/
- Flask Quickstart: https://flask.palletsprojects.com/en/stable/quickstart/
- Matplotlib documentation: https://matplotlib.org/stable/
- WhatsApp Click-to-Chat guide: https://faq.whatsapp.com/5913398998672934
