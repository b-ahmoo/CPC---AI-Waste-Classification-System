import hashlib
import sqlite3

from database import get_connection


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, country):
    connection = get_connection()
    cursor = connection.cursor()

    password_hash = hash_password(password)

    try:
        cursor.execute("""
            INSERT INTO users
            (user_name, password_hash, selected_country)
            VALUES (?, ?, ?)
        """, (username, password_hash, country))

        connection.commit()

        user_id = cursor.lastrowid

        return {
            "success": True,
            "user_id": user_id,
            "message": "Account created successfully."
        }

    except sqlite3.IntegrityError:
        return {
            "success": False,
            "message": "Username already exists."
        }

    finally:
        connection.close()


def login_user(username, password):
    connection = get_connection()
    cursor = connection.cursor()

    password_hash = hash_password(password)

    cursor.execute("""
        SELECT user_id, user_name, selected_country
        FROM users
        WHERE user_name = ?
        AND password_hash = ?
    """, (username, password_hash))

    user = cursor.fetchone()

    connection.close()

    if user:
        return {
            "success": True,
            "user_id": user[0],
            "username": user[1],
            "country": user[2]
        }

    return {
        "success": False,
        "message": "Invalid username or password."
    }