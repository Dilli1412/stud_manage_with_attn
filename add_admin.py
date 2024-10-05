# File: add_admin.py

import sqlite3
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def add_admin(db_name='students.db'):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Create users table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, is_admin INTEGER)''')

    # Add admin user
    username = 'admin'
    password = 'admin'
    hashed_password = hash_password(password)

    try:
        c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
                  (username, hashed_password, 1))
        conn.commit()
        print(f"Admin user '{username}' added successfully.")
    except sqlite3.IntegrityError:
        print(f"Admin user '{username}' already exists.")
    finally:
        conn.close()

if __name__ == "__main__":
    add_admin()
    print("You can now log in to the admin account with:")
    print("Username: admin")
    print("Password: admin")
    print("Please change this password after your first login for security reasons.")