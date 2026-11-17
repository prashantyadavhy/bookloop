# BookLoop - Student Book Exchange Portal

BookLoop is a small Flask and MySQL website for listing, finding, requesting and exchanging used academic books. It is designed as a Class 12 Informatics Practices project: the Python uses functions, conditions, loops, basic validation and parameterised SQL queries.

## What the project can do

- Register students with a generated MySQL student ID and hashed password.
- Add books and browse/search available listings.
- Send a request to another student's available book.
- Let the owner accept or reject a pending request.
- Reserve an accepted book and record a completed exchange.
- Open pre-filled WhatsApp Click-to-Chat messages for the students involved.
- Give an admin a separate login to review records, remove listings and see simple totals and charts.

WhatsApp messages are **not sent automatically**. A student reviews the message in WhatsApp and presses Send. Student phone numbers are not shown in public book cards or admin tables.

## Folder contents

```text
BookLoop/
  app.py
  database.py
  whatsapp.py
  create_database.sql
  requirements.txt
  README.md
  PROJECT_GUIDE.md
  templates/
  static/css/style.css
  static/images/default-book.svg
```

## Install and run on Windows

1. Install Python 3.10 or later and MySQL Community Server. Start the MySQL service. MySQL Workbench is optional; it is a visual program for viewing the database.
2. Open `database.py`. Set `MYSQL_HOST`, `MYSQL_USER` and `MYSQL_PASSWORD` to the values for your MySQL account. The example uses `localhost`, `root` and a placeholder password.
3. Open Command Prompt or PowerShell in this BookLoop folder and install the listed packages:

   ```text
   python -m pip install -r requirements.txt
   ```

4. Create the database and tables, and make the first admin account:

   ```text
   python database.py
   ```

   The script creates `bookloop_db`, reads the five `CREATE TABLE` statements in `create_database.sql`, then asks for an admin username and password if no admin exists.

5. Start the website:

   ```text
   python app.py
   ```

6. Open `http://127.0.0.1:5000` in a browser. Register two student accounts to demonstrate listing, requesting, accepting, WhatsApp coordination and completion. Use `/admin/login` or the footer link for the admin account.

## WhatsApp phone-number format

Enter the country code followed by the phone digits, for example `919876543210` for a sample Indian number. You may type `+`, spaces, hyphens or parentheses; the program removes those characters before making the `wa.me` URL. It checks that the cleaned number has 10 to 15 digits.

The project calls Python's `webbrowser.open()` from Flask. It is intended to run locally on the same computer as the browser. WhatsApp opens with a pre-filled message; the student must press Send. If another device uses a Flask server on a different computer, `webbrowser.open()` opens the browser on the server computer, because Python runs there.

## Book and request statuses

- A new listing starts as `Available`.
- A request starts as `Pending`.
- When the owner accepts it, the request becomes `Accepted` and the book becomes `Reserved`.
- Other pending requests for that book are rejected so no second student can claim it.
- When either participant records the physical handover, the request becomes `Completed`, the book becomes `Exchanged`, and a row is added to `Exchanges`.
- An admin removes a listing with no request history by deleting its row. If it has request history, its status becomes `Removed` so the related records remain connected.

## Common errors

| Error | What to check |
|---|---|
| `Access denied for user` | Check `MYSQL_USER` and `MYSQL_PASSWORD` in `database.py`. |
| `Can't connect to MySQL server` | Start the MySQL service and confirm the host and port. |
| `No module named flask` | Run `python -m pip install -r requirements.txt` using the same Python that runs the project. |
| `Unknown database 'bookloop_db'` | Run `python database.py` before `python app.py`. |
| Admin login does not work | Run `python database.py`; it creates the first admin when the Admins table is empty. |
| WhatsApp number is rejected | Enter 10 to 15 digits, including the country code. |
| WhatsApp opens in a different browser | `webbrowser.open()` uses the default browser on the computer running Flask. |
| Port 5000 is already in use | Close the other local Flask program, then run `python app.py` again. |

## Project explanation and practical preparation

Read [PROJECT_GUIDE.md](PROJECT_GUIDE.md) for the database relationships, file and function explanations, SQL examples, test checklist, viva questions and a short demonstration script.

## Supporting technologies

Python, MySQL, SQL and basic data handling are the main learning concepts. Flask connects Python routes to HTML templates. HTML and CSS build and style the pages. Werkzeug password helpers are included with Flask and store a one-way password hash. Matplotlib makes the two simple admin charts. These are supporting project tools, not claims about prescribed CBSE IP syllabus topics.
