
import sqlite3
import os

DATABASE = os.path.join("instance", "bus_reservation.db")


def get_connection():
    os.makedirs("instance", exist_ok=True)

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    return connection


def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Buses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_name TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            fare REAL NOT NULL,
            total_seats INTEGER NOT NULL
        )
    """)

    # Bookings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL,
            passenger_name TEXT NOT NULL,
            passenger_email TEXT NOT NULL,
            seats INTEGER NOT NULL,
            travel_date TEXT NOT NULL,
            total_fare REAL NOT NULL,
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bus_id) REFERENCES buses(id)
        )
    """)

    # Insert sample buses only if table is empty
    cursor.execute("SELECT COUNT(*) FROM buses")

    if cursor.fetchone()[0] == 0:
        sample_buses = [
            ("Faisal Movers", "Karachi", "Hyderabad", "09:00 AM", 1500, 40),
            ("Daewoo Express", "Karachi", "Hyderabad", "11:00 AM", 1800, 40),
            ("Road Master", "Karachi", "Lahore", "08:00 PM", 5500, 40),
            ("Skyways", "Karachi", "Islamabad", "07:00 PM", 6000, 40)
        ]

        cursor.executemany("""
            INSERT INTO buses
            (bus_name, source, destination, departure_time, fare, total_seats)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_buses)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database and tables created successfully!")
