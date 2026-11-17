"""Main Flask application for the BookLoop student book portal."""

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash
from mysql.connector import Error
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from database import get_db_connection
from whatsapp import (
    clean_phone_number,
    send_acceptance_message,
    send_donation_enquiry,
    send_exchange_coordination,
    send_rejection_message,
    send_request_message,
)


app = Flask(__name__)
app.secret_key = "secret-key"


def close_database(connection, cursor):
    """Close the cursor and connection after a database task."""
    if cursor is not None:
        cursor.close()
    if connection is not None and connection.is_connected():
        connection.close()


def get_whatsapp_button_message(action, phone_number, book_name):
    """Call the correct prepared-message function for a WhatsApp action."""
    if action == "request":
        return send_request_message(phone_number, book_name)
    if action == "accept":
        return send_acceptance_message(phone_number, book_name)
    if action == "reject":
        return send_rejection_message(phone_number, book_name)
    if action == "donation":
        return send_donation_enquiry(phone_number, book_name)
    if action == "coordinate":
        return send_exchange_coordination(phone_number, book_name)
    return False


@app.route("/")
def home():
    """Show the introduction and recently listed books."""
    connection = None
    cursor = None
    recent_books = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT Books.book_id, Books.book_name, Books.author, Books.subject,
                   Books.book_class, Books.book_condition, Books.exchange_type,
                   Students.name AS owner_name
            FROM Books
            JOIN Students ON Books.student_id = Students.student_id
            WHERE Books.status = 'Available'
            ORDER BY Books.date_added DESC
            LIMIT 6
        """
        cursor.execute(query)
        recent_books = cursor.fetchall()
    except Error as error:
        flash("The book list is not available yet. Set up MySQL first.", "error")
        print("Home page database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template("index.html", recent_books=recent_books)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a student and save a hashed password."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        student_class = request.form.get("student_class", "").strip()
        phone_number = clean_phone_number(request.form.get("whatsapp_number", ""))

        if name == "" or email == "" or password == "" or student_class == "":
            flash("Please complete every field.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Use a password with at least six characters.", "error")
            return render_template("register.html")

        if phone_number == "":
            flash("Enter a valid WhatsApp number with country code, such as 919876543210.", "error")
            return render_template("register.html")

        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT student_id FROM Students WHERE email = %s", (email,))
            existing_student = cursor.fetchone()

            if existing_student is not None:
                flash("That email is already registered. Please log in.", "error")
                return render_template("register.html")

            password_hash = generate_password_hash(password)
            insert_query = """
                INSERT INTO Students (name, email, password_hash, student_class, whatsapp_number)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(
                insert_query,
                (name, email, password_hash, student_class, phone_number)
            )
            connection.commit()
            flash("Registration complete. You can now log in.", "success")
            return redirect(url_for("login"))
        except Error as error:
            flash("Registration could not be saved. Check the MySQL settings.", "error")
            print("Registration database error:", error)
        finally:
            close_database(connection, cursor)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Check a student's email and password."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Students WHERE email = %s", (email,))
            student = cursor.fetchone()

            if student is not None and check_password_hash(student["password_hash"], password):
                session.clear()
                session["student_id"] = student["student_id"]
                session["student_name"] = student["name"]
                flash("Welcome back, " + student["name"] + ".", "success")
                return redirect(url_for("dashboard"))

            flash("Email or password is incorrect.", "error")
        except Error as error:
            flash("Login could not connect to MySQL.", "error")
            print("Student login database error:", error)
        finally:
            close_database(connection, cursor)

    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Log in an admin using the separate Admins table."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Admins WHERE username = %s", (username,))
            admin = cursor.fetchone()

            if admin is not None and check_password_hash(admin["password_hash"], password):
                session.clear()
                session["admin_id"] = admin["admin_id"]
                session["admin_name"] = admin["username"]
                return redirect(url_for("admin_dashboard"))

            flash("Admin username or password is incorrect.", "error")
        except Error as error:
            flash("Admin login could not connect to MySQL.", "error")
            print("Admin login database error:", error)
        finally:
            close_database(connection, cursor)

    return render_template("login.html", admin_login=True)


@app.route("/logout")
def logout():
    """End the current student or admin session."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    """Show simple counts for the logged-in student."""
    if "student_id" not in session:
        flash("Please log in to open your dashboard.", "error")
        return redirect(url_for("login"))

    student_id = session["student_id"]
    connection = None
    cursor = None
    counts = {"books": 0, "incoming": 0, "outgoing": 0, "accepted": 0, "completed": 0}

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM Books WHERE student_id = %s", (student_id,))
        counts["books"] = cursor.fetchone()["total"]

        cursor.execute(
            """SELECT COUNT(*) AS total FROM Requests
               JOIN Books ON Requests.book_id = Books.book_id
               WHERE Books.student_id = %s AND Requests.request_status = 'Pending'""",
            (student_id,)
        )
        counts["incoming"] = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) AS total FROM Requests WHERE requester_id = %s AND request_status = 'Pending'",
            (student_id,)
        )
        counts["outgoing"] = cursor.fetchone()["total"]

        cursor.execute(
            """SELECT COUNT(*) AS total FROM Requests
               JOIN Books ON Requests.book_id = Books.book_id
               WHERE (Books.student_id = %s OR Requests.requester_id = %s)
               AND Requests.request_status = 'Accepted'""",
            (student_id, student_id)
        )
        counts["accepted"] = cursor.fetchone()["total"]

        cursor.execute(
            """SELECT COUNT(*) AS total FROM Exchanges
               JOIN Requests ON Exchanges.request_id = Requests.request_id
               JOIN Books ON Requests.book_id = Books.book_id
               WHERE Books.student_id = %s OR Requests.requester_id = %s""",
            (student_id, student_id)
        )
        counts["completed"] = cursor.fetchone()["total"]
    except Error as error:
        flash("Dashboard information could not be loaded.", "error")
        print("Dashboard database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template("dashboard.html", counts=counts)


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    """Save a new book listing for the logged-in student."""
    if "student_id" not in session:
        flash("Please log in before adding a book.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        book_name = request.form.get("book_name", "").strip()
        author = request.form.get("author", "").strip()
        subject = request.form.get("subject", "").strip()
        book_class = request.form.get("book_class", "").strip()
        price_text = request.form.get("original_price", "").strip()
        book_condition = request.form.get("book_condition", "")
        exchange_type = request.form.get("exchange_type", "")

        try:
            original_price = float(price_text)
        except ValueError:
            flash("Enter the original price as a number.", "error")
            return render_template("add_book.html")

        if original_price < 0:
            flash("Price cannot be negative.", "error")
            return render_template("add_book.html")

        if book_condition not in ["New", "Good", "Used"]:
            flash("Choose New, Good or Used as the condition.", "error")
            return render_template("add_book.html")

        if exchange_type not in ["Exchange", "Free Donation"]:
            flash("Choose Exchange or Free Donation.", "error")
            return render_template("add_book.html")

        if book_name == "" or author == "" or subject == "" or book_class == "":
            flash("Please complete every book detail.", "error")
            return render_template("add_book.html")

        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            insert_query = """
                INSERT INTO Books
                (student_id, book_name, author, subject, book_class,
                 original_price, book_condition, exchange_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Available')
            """
            cursor.execute(
                insert_query,
                (session["student_id"], book_name, author, subject, book_class,
                 original_price, book_condition, exchange_type)
            )
            connection.commit()
            flash("Your book listing has been added.", "success")
            return redirect(url_for("my_books"))
        except Error as error:
            flash("The book could not be saved.", "error")
            print("Add book database error:", error)
        finally:
            close_database(connection, cursor)

    return render_template("add_book.html")


@app.route("/books")
def browse_books():
    """Search and filter available books using the form fields."""
    book_name = request.args.get("book_name", "").strip()
    author = request.args.get("author", "").strip()
    subject = request.args.get("subject", "").strip()
    book_class = request.args.get("book_class", "").strip()
    book_condition = request.args.get("book_condition", "").strip()

    query = """
        SELECT Books.book_id, Books.book_name, Books.author, Books.subject,
               Books.book_class, Books.book_condition, Books.exchange_type,
               Books.status, Students.name AS owner_name
        FROM Books
        JOIN Students ON Books.student_id = Students.student_id
        WHERE Books.status = 'Available'
    """
    query_values = []

    if book_name != "":
        query = query + " AND Books.book_name LIKE %s"
        query_values.append("%" + book_name + "%")
    if author != "":
        query = query + " AND Books.author LIKE %s"
        query_values.append("%" + author + "%")
    if subject != "":
        query = query + " AND Books.subject LIKE %s"
        query_values.append("%" + subject + "%")
    if book_class != "":
        query = query + " AND Books.book_class = %s"
        query_values.append(book_class)
    if book_condition != "":
        query = query + " AND Books.book_condition = %s"
        query_values.append(book_condition)

    query = query + " ORDER BY Books.date_added DESC"
    connection = None
    cursor = None
    books = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, tuple(query_values))
        books = cursor.fetchall()
    except Error as error:
        flash("Books could not be loaded. Check the database setup.", "error")
        print("Browse books database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template("browse_books.html", books=books)


@app.route("/books/<int:book_id>/request", methods=["POST"])
def request_book(book_id):
    """Create a pending request if the book is available and not the student's own."""
    if "student_id" not in session:
        flash("Please log in before requesting a book.", "error")
        return redirect(url_for("login"))

    student_id = session["student_id"]
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()

        if book is None or book["status"] != "Available":
            flash("This book is no longer available.", "error")
            return redirect(url_for("browse_books"))
        if book["student_id"] == student_id:
            flash("You cannot request your own book.", "error")
            return redirect(url_for("browse_books"))

        cursor.execute(
            """SELECT request_id FROM Requests
               WHERE book_id = %s AND requester_id = %s
               AND request_status = 'Pending'""",
            (book_id, student_id)
        )
        existing_request = cursor.fetchone()
        if existing_request is not None:
            flash("You already have a pending request for this book.", "error")
            return redirect(url_for("requests_page"))

        cursor.execute(
            "INSERT INTO Requests (book_id, requester_id, request_status) VALUES (%s, %s, 'Pending')",
            (book_id, student_id)
        )
        connection.commit()
        flash("Your request was saved. You can message the book owner from your requests page.", "success")
        return redirect(url_for("requests_page"))
    except Error as error:
        flash("The request could not be saved.", "error")
        print("Request database error:", error)
    finally:
        close_database(connection, cursor)

    return redirect(url_for("browse_books"))


@app.route("/books/mine")
def my_books():
    """Show the logged-in student's own listings."""
    if "student_id" not in session:
        flash("Please log in to view your books.", "error")
        return redirect(url_for("login"))

    connection = None
    cursor = None
    books = []
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM Books WHERE student_id = %s ORDER BY date_added DESC",
            (session["student_id"],)
        )
        books = cursor.fetchall()
    except Error as error:
        flash("Your book list could not be loaded.", "error")
        print("My books database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template("my_books.html", books=books)


@app.route("/requests")
def requests_page():
    """Show requests received for the student's books and requests they made."""
    if "student_id" not in session:
        flash("Please log in to view requests.", "error")
        return redirect(url_for("login"))

    student_id = session["student_id"]
    connection = None
    cursor = None
    incoming_requests = []
    outgoing_requests = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        incoming_query = """
            SELECT Requests.request_id, Requests.request_status, Requests.request_date,
                   Books.book_id, Books.book_name, Books.exchange_type,
                   Students.name AS requester_name
            FROM Requests
            JOIN Books ON Requests.book_id = Books.book_id
            JOIN Students ON Requests.requester_id = Students.student_id
            WHERE Books.student_id = %s
            ORDER BY Requests.request_date DESC
        """
        cursor.execute(incoming_query, (student_id,))
        incoming_requests = cursor.fetchall()

        outgoing_query = """
            SELECT Requests.request_id, Requests.request_status, Requests.request_date,
                   Books.book_id, Books.book_name, Books.exchange_type,
                   Students.name AS owner_name
            FROM Requests
            JOIN Books ON Requests.book_id = Books.book_id
            JOIN Students ON Books.student_id = Students.student_id
            WHERE Requests.requester_id = %s
            ORDER BY Requests.request_date DESC
        """
        cursor.execute(outgoing_query, (student_id,))
        outgoing_requests = cursor.fetchall()
    except Error as error:
        flash("Requests could not be loaded.", "error")
        print("Requests database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template(
        "requests.html",
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests
    )


@app.route("/requests/<int:request_id>/<action>", methods=["POST"])
def update_request(request_id, action):
    """Allow a book owner to accept or reject a pending request."""
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))
    if action not in ["accept", "reject"]:
        flash("That request action is not available.", "error")
        return redirect(url_for("requests_page"))

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT Requests.request_status, Requests.book_id, Books.student_id
               FROM Requests JOIN Books ON Requests.book_id = Books.book_id
               WHERE Requests.request_id = %s""",
            (request_id,)
        )
        request_row = cursor.fetchone()

        if request_row is None or request_row["student_id"] != session["student_id"]:
            flash("Only the book owner can update this request.", "error")
            return redirect(url_for("requests_page"))
        if request_row["request_status"] != "Pending":
            flash("This request has already been handled.", "error")
            return redirect(url_for("requests_page"))

        if action == "accept":
            cursor.execute("SELECT status FROM Books WHERE book_id = %s", (request_row["book_id"],))
            book_row = cursor.fetchone()
            if book_row is None or book_row["status"] != "Available":
                cursor.execute(
                    "UPDATE Requests SET request_status = 'Rejected' WHERE request_id = %s",
                    (request_id,)
                )
                connection.commit()
                flash("The book is no longer available, so the request was rejected.", "error")
                return redirect(url_for("requests_page"))

            cursor.execute(
                "UPDATE Requests SET request_status = 'Accepted' WHERE request_id = %s",
                (request_id,)
            )
            cursor.execute(
                "UPDATE Books SET status = 'Reserved' WHERE book_id = %s",
                (request_row["book_id"],)
            )
            cursor.execute(
                """UPDATE Requests SET request_status = 'Rejected'
                   WHERE book_id = %s AND request_id <> %s AND request_status = 'Pending'""",
                (request_row["book_id"], request_id)
            )
            connection.commit()
            flash("Request accepted. The book is now reserved.", "success")
        else:
            cursor.execute(
                "UPDATE Requests SET request_status = 'Rejected' WHERE request_id = %s",
                (request_id,)
            )
            connection.commit()
            flash("Request rejected. The book remains available.", "success")
    except Error as error:
        flash("The request could not be updated.", "error")
        print("Update request database error:", error)
    finally:
        close_database(connection, cursor)

    return redirect(url_for("requests_page"))


@app.route("/requests/<int:request_id>/complete", methods=["POST"])
def complete_exchange(request_id):
    """Record a physical exchange after both students have arranged it."""
    if "student_id" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """SELECT Requests.request_status, Requests.book_id,
                      Requests.requester_id, Books.student_id, Books.status AS book_status
               FROM Requests JOIN Books ON Requests.book_id = Books.book_id
               WHERE Requests.request_id = %s""",
            (request_id,)
        )
        request_row = cursor.fetchone()

        if request_row is None:
            flash("Request not found.", "error")
            return redirect(url_for("requests_page"))

        student_id = session["student_id"]
        is_participant = (
            student_id == request_row["student_id"] or
            student_id == request_row["requester_id"]
        )
        if not is_participant:
            flash("Only the students involved can complete this exchange.", "error")
            return redirect(url_for("requests_page"))

        if request_row["request_status"] != "Accepted":
            flash("Only an accepted request can be marked completed.", "error")
            return redirect(url_for("requests_page"))

        cursor.execute(
            "UPDATE Requests SET request_status = 'Completed' WHERE request_id = %s",
            (request_id,)
        )
        cursor.execute(
            "UPDATE Books SET status = 'Exchanged' WHERE book_id = %s",
            (request_row["book_id"],)
        )
        cursor.execute(
            "INSERT INTO Exchanges (request_id, exchange_status) VALUES (%s, 'Completed')",
            (request_id,)
        )
        connection.commit()
        flash("The exchange has been recorded as completed.", "success")
    except Error as error:
        if connection is not None:
            connection.rollback()
        flash("The exchange could not be completed.", "error")
        print("Complete exchange database error:", error)
    finally:
        close_database(connection, cursor)

    return redirect(url_for("requests_page"))


@app.route("/whatsapp", methods=["POST"])
def open_whatsapp():
    """Open a prepared WhatsApp message only for students in that transaction."""
    if "student_id" not in session:
        flash("Please log in before contacting another student.", "error")
        return redirect(url_for("login"))

    action = request.form.get("action", "")
    student_id = session["student_id"]
    connection = None
    cursor = None
    phone_number = ""
    book_name = ""
    target_is_allowed = False

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if action == "donation":
            book_id = request.form.get("book_id", type=int)
            cursor.execute(
                """SELECT Books.book_name, Books.status, Books.exchange_type,
                          Books.student_id, Students.whatsapp_number
                   FROM Books JOIN Students ON Books.student_id = Students.student_id
                   WHERE Books.book_id = %s""",
                (book_id,)
            )
            row = cursor.fetchone()
            if row is not None and row["student_id"] != student_id:
                if row["status"] == "Available" and row["exchange_type"] == "Free Donation":
                    target_is_allowed = True
                    phone_number = row["whatsapp_number"]
                    book_name = row["book_name"]
        else:
            request_id = request.form.get("request_id", type=int)
            cursor.execute(
                """SELECT Requests.requester_id, Requests.request_status,
                          Books.student_id, Books.book_name,
                          Owner.whatsapp_number AS owner_phone,
                          Requester.whatsapp_number AS requester_phone
                   FROM Requests
                   JOIN Books ON Requests.book_id = Books.book_id
                   JOIN Students AS Owner ON Books.student_id = Owner.student_id
                   JOIN Students AS Requester ON Requests.requester_id = Requester.student_id
                   WHERE Requests.request_id = %s""",
                (request_id,)
            )
            row = cursor.fetchone()

            if row is not None:
                is_owner = row["student_id"] == student_id
                is_requester = row["requester_id"] == student_id
                status = row["request_status"]
                book_name = row["book_name"]

                if action == "request" and is_requester and status == "Pending":
                    target_is_allowed = True
                    phone_number = row["owner_phone"]
                elif action == "request" and is_owner and status == "Pending":
                    target_is_allowed = True
                    phone_number = row["requester_phone"]
                elif action == "accept" and is_owner and status == "Accepted":
                    target_is_allowed = True
                    phone_number = row["requester_phone"]
                elif action == "reject" and is_owner and status == "Rejected":
                    target_is_allowed = True
                    phone_number = row["requester_phone"]
                elif action == "coordinate" and status == "Accepted" and (is_owner or is_requester):
                    target_is_allowed = True
                    if is_owner:
                        phone_number = row["requester_phone"]
                    else:
                        phone_number = row["owner_phone"]

        close_database(connection, cursor)
        connection = None
        cursor = None

        if not target_is_allowed:
            flash("You can contact only a student involved in this available book or request.", "error")
            return redirect(request.referrer or url_for("requests_page"))

        message_opened = get_whatsapp_button_message(action, phone_number, book_name)
        if message_opened:
            flash("WhatsApp opened with a prepared message. Review it and press Send there.", "success")
        else:
            flash("The WhatsApp number could not be validated.", "error")
    except Error as error:
        flash("The contact details could not be loaded.", "error")
        print("WhatsApp lookup database error:", error)
    finally:
        close_database(connection, cursor)

    return redirect(request.referrer or url_for("requests_page"))


@app.route("/admin")
def admin_dashboard():
    """Show admin lists for students, books, requests and completed exchanges."""
    if "admin_id" not in session:
        flash("Log in as admin to open this page.", "error")
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None
    students = []
    books = []
    requests_list = []
    exchanges = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT student_id, name, email, student_class FROM Students ORDER BY name")
        students = cursor.fetchall()
        cursor.execute(
            """SELECT Books.book_id, Books.book_name, Books.subject, Books.book_class,
                      Books.status, Books.exchange_type, Students.name AS owner_name
               FROM Books JOIN Students ON Books.student_id = Students.student_id
               ORDER BY Books.date_added DESC"""
        )
        books = cursor.fetchall()
        cursor.execute(
            """SELECT Requests.request_id, Requests.request_status, Requests.request_date,
                      Books.book_name, Owner.name AS owner_name, Requester.name AS requester_name
               FROM Requests
               JOIN Books ON Requests.book_id = Books.book_id
               JOIN Students AS Owner ON Books.student_id = Owner.student_id
               JOIN Students AS Requester ON Requests.requester_id = Requester.student_id
               ORDER BY Requests.request_date DESC"""
        )
        requests_list = cursor.fetchall()
        cursor.execute(
            """SELECT Exchanges.exchange_id, Exchanges.exchange_date, Exchanges.exchange_status,
                      Books.book_name, Owner.name AS owner_name, Requester.name AS requester_name
               FROM Exchanges
               JOIN Requests ON Exchanges.request_id = Requests.request_id
               JOIN Books ON Requests.book_id = Books.book_id
               JOIN Students AS Owner ON Books.student_id = Owner.student_id
               JOIN Students AS Requester ON Requests.requester_id = Requester.student_id
               ORDER BY Exchanges.exchange_date DESC"""
        )
        exchanges = cursor.fetchall()
    except Error as error:
        flash("Admin information could not be loaded.", "error")
        print("Admin dashboard database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template(
        "admin.html",
        students=students,
        books=books,
        requests_list=requests_list,
        exchanges=exchanges
    )


@app.route("/admin/books/<int:book_id>/delete", methods=["POST"])
def admin_delete_book(book_id):
    """Remove a listing; retain it as Removed if request history refers to it."""
    if "admin_id" not in session:
        flash("Log in as admin first.", "error")
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT request_id FROM Requests WHERE book_id = %s LIMIT 1", (book_id,))
        has_history = cursor.fetchone()

        if has_history is None:
            cursor.execute("DELETE FROM Books WHERE book_id = %s", (book_id,))
            flash("The book listing was deleted.", "success")
        else:
            cursor.execute("UPDATE Books SET status = 'Removed' WHERE book_id = %s", (book_id,))
            flash("The listing was removed from browsing; its request history was kept.", "success")
        connection.commit()
    except Error as error:
        flash("The book listing could not be removed.", "error")
        print("Admin delete book database error:", error)
    finally:
        close_database(connection, cursor)

    return redirect(url_for("admin_dashboard"))


@app.route("/statistics")
def statistics():
    """Show simple database totals and create basic Matplotlib charts."""
    if "admin_id" not in session:
        flash("Log in as admin to view statistics.", "error")
        return redirect(url_for("admin_login"))

    connection = None
    cursor = None
    totals = {"students": 0, "books": 0, "exchanges": 0, "money_saved": 0, "average_price": 0}
    subject_rows = []
    class_rows = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total FROM Students")
        totals["students"] = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM Books WHERE status <> 'Removed'")
        totals["books"] = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM Exchanges WHERE exchange_status = 'Completed'")
        totals["exchanges"] = cursor.fetchone()["total"]
        cursor.execute(
            """SELECT COALESCE(SUM(Books.original_price), 0) AS total
               FROM Exchanges JOIN Requests ON Exchanges.request_id = Requests.request_id
               JOIN Books ON Requests.book_id = Books.book_id
               WHERE Exchanges.exchange_status = 'Completed'"""
        )
        totals["money_saved"] = cursor.fetchone()["total"]
        cursor.execute("SELECT COALESCE(AVG(original_price), 0) AS average FROM Books WHERE status <> 'Removed'")
        totals["average_price"] = cursor.fetchone()["average"]
        cursor.execute(
            "SELECT subject, COUNT(*) AS total FROM Books WHERE status <> 'Removed' GROUP BY subject ORDER BY total DESC"
        )
        subject_rows = cursor.fetchall()
        cursor.execute(
            "SELECT book_class, COUNT(*) AS total FROM Books WHERE status <> 'Removed' GROUP BY book_class ORDER BY book_class"
        )
        class_rows = cursor.fetchall()

        subject_names = []
        subject_counts = []
        for row in subject_rows:
            subject_names.append(row["subject"])
            subject_counts.append(row["total"])

        class_names = []
        class_counts = []
        for row in class_rows:
            class_names.append(row["book_class"])
            class_counts.append(row["total"])

        figure, chart_axes = plt.subplots(1, 2, figsize=(10, 4))
        if subject_names:
            chart_axes[0].bar(subject_names, subject_counts, color="#49a8e8")
            chart_axes[0].set_title("Books by subject")
            chart_axes[0].set_ylabel("Number of books")
            chart_axes[0].tick_params(axis="x", rotation=35)
        else:
            chart_axes[0].text(0.5, 0.5, "No book data yet", ha="center", va="center")
            chart_axes[0].set_title("Books by subject")
        if class_names:
            chart_axes[1].pie(class_counts, labels=class_names, autopct="%1.0f%%")
            chart_axes[1].set_title("Books by class")
        else:
            chart_axes[1].text(0.5, 0.5, "No book data yet", ha="center", va="center")
            chart_axes[1].set_title("Books by class")
        figure.tight_layout()
        chart_path = "static/images/bookloop_statistics.png"
        figure.savefig(chart_path, dpi=140)
        plt.close(figure)
    except Error as error:
        flash("Statistics could not be loaded.", "error")
        print("Statistics database error:", error)
    finally:
        close_database(connection, cursor)

    return render_template(
        "statistics.html",
        totals=totals,
        subject_rows=subject_rows,
        class_rows=class_rows
    )


if __name__ == "__main__":
    app.run(debug=True)
