import sqlite3

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def initialize_db(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scid TEXT,
        time TEXT,
        metric TEXT,
        value REAL,
        threshold REAL
    );
    """)
    conn.commit()
