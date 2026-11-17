"""MySQL setup and connection functions for BookLoop."""

import getpass
import os

import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash


# Change these settings to match MySQL on your computer.
MYSQL_HOST = "localhost"
MYSQL_USER = "sqlname"
MYSQL_PASSWORD = "password"
DATABASE_NAME = "bookloop_db"


def get_db_connection():
    """Open and return a connection to the BookLoop database."""
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=DATABASE_NAME
    )
    return connection


def create_database_and_tables():
    """Create the database, then make the five tables in the SQL file."""
    connection = None
    cursor = None

    try:
        # Connect to MySQL without selecting a database first.
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS " + DATABASE_NAME)
        connection.commit()
        cursor.close()
        connection.close()

        # Connect to the newly created database.
        connection = get_db_connection()
        cursor = connection.cursor()

        folder_path = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(folder_path, "create_database.sql")
        sql_file = open(sql_file_path, "r", encoding="utf-8")
        sql_text = sql_file.read()
        sql_file.close()

        # Run each CREATE TABLE statement from the SQL file.
        sql_commands = sql_text.split(";")
        for sql_command in sql_commands:
            if sql_command.strip() != "":
                cursor.execute(sql_command)

        connection.commit()
        print("BookLoop database and tables are ready.")

    except Error as error:
        print("MySQL setup error:", error)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


def create_first_admin():
    """Create one admin account if the Admins table is empty."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM Admins")
        admin_count = cursor.fetchone()[0]

        if admin_count > 0:
            print("An admin account already exists.")
            return

        username = input("Choose an admin username: ").strip()
        password = getpass.getpass("Choose an admin password: ")

        if username == "" or password == "":
            print("Username and password cannot be empty.")
            return

        password_hash = generate_password_hash(password)
        insert_query = "INSERT INTO Admins (username, password_hash) VALUES (%s, %s)"
        cursor.execute(insert_query, (username, password_hash))
        connection.commit()
        print("Admin account created.")

    except Error as error:
        print("Could not create the admin account:", error)

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    create_database_and_tables()
    create_first_admin()
