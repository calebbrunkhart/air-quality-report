import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/opt/airquality/data/airquality.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            location    TEXT NOT NULL,
            aqi         INTEGER,
            category    TEXT,
            pollutant   TEXT,
            latitude    REAL,
            longitude   REAL
        )
    """)
    conn.commit()
    conn.close()

def insert_reading(timestamp, location, aqi, category, pollutant, latitude, longitude):
    conn = get_connection()
    conn.execute("""
        INSERT INTO readings (timestamp, location, aqi, category, pollutant, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, location, aqi, category, pollutant, latitude, longitude))
    conn.commit()
    conn.close()

def get_latest_reading():
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1
    """).fetchone()
    conn.close()
    return dict(row) if row else None

def get_history(hours=72):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM readings
        WHERE timestamp >= datetime('now', ?)
        ORDER BY timestamp ASC
    """, (f"-{hours} hours",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
