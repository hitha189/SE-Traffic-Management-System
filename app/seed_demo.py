"""Create demo accounts for the Sprint 2 demo video.

Run once from the app folder:  python seed_demo.py
Demo passwords are for local demos only - never use them anywhere real.
"""
from werkzeug.security import generate_password_hash

import app as tms

DEMO_USERS = [
    ("admin1", "admin1@tms.local", "Admin@123", "admin"),
    ("ambulance1", "ambulance1@tms.local", "Ambulance@123", "emergency"),
    ("driver1", "driver1@tms.local", "Driver@123", "user"),
]


def main():
    tms.init_db()
    conn = tms.get_db()
    for username, email, password, role in DEMO_USERS:
        conn.execute(
            "INSERT OR REPLACE INTO users (id, username, email, "
            "password_hash, role) VALUES ((SELECT id FROM users WHERE "
            "username = ?), ?, ?, ?, ?)",
            (username, username, email, generate_password_hash(password),
             role))
        print("%-11s %-14s role=%s" % (username, password, role))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
