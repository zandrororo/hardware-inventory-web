import sqlite3
import psycopg2

# Ilalagay natin dito ang URL mamaya kapag nakagawa na tayo ng Supabase account
SUPABASE_URL = "ILALAGAY_NATIN_TO_MAMAYA"
SQLITE_DB = "hardware_inventory_midterm.db"

def migrate_data():
    print("Connecting to local database...")
    sl_conn = sqlite3.connect(SQLITE_DB)
    sl_cur = sl_conn.cursor()

    try:
        print("Connecting to Supabase...")
        pg_conn = psycopg2.connect(SUPABASE_URL)
        pg_cur = pg_conn.cursor()
        
        print("Creating tables in Supabase...")
        # Users Table
        pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            is_locked INTEGER DEFAULT 0
        )
        """)
        # Password Requests
        pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS password_requests (
            req_id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
        """)
        # Hardware
        pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware (
            item_id SERIAL PRIMARY KEY,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            status TEXT NOT NULL
        )
        """)
        # Borrow Logs
        pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS borrow_logs (
            log_id SERIAL PRIMARY KEY,
            item_id INTEGER,
            item_name TEXT NOT NULL,
            username TEXT NOT NULL,
            borrowed_qty INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT DEFAULT 'Borrowed'
        )
        """)
        pg_conn.commit()

        print("Tables created successfully. We will transfer data later!")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Baka hindi pa naka-set ang Supabase URL natin.")
    finally:
        if sl_conn: sl_conn.close()
        try:
            if pg_conn: pg_conn.close()
        except:
            pass

if __name__ == "__main__":
    migrate_data()