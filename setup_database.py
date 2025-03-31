import sqlite3
import os

DATABASE_FILE = 'manuals.db'

def create_connection(db_file):
    """ Create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite DB connection successful to {db_file}")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def execute_sql(conn, sql_statement):
    """ Execute a single SQL statement """
    try:
        c = conn.cursor()
        c.execute(sql_statement)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error executing SQL: {e}\nStatement: {sql_statement}")

def setup_database(conn):
    """ Create tables in the SQLite database """
    print("Setting up database tables...")

    sql_create_manuals_table = """
    CREATE TABLE IF NOT EXISTS manuals (
        manual_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        source_path TEXT UNIQUE NOT NULL,
        language TEXT DEFAULT 'en',
        features TEXT, -- Store as JSON array string
        special_features TEXT, -- Store as JSON array string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    sql_create_tabs_table = """
    CREATE TABLE IF NOT EXISTS tabs (
        tab_id INTEGER PRIMARY KEY AUTOINCREMENT,
        manual_id INTEGER NOT NULL,
        tab_key TEXT NOT NULL, -- e.g., 'hardwareInstallation'
        title TEXT NOT NULL, -- e.g., 'Hardware Installation'
        tab_order INTEGER NOT NULL,
        content_type TEXT NOT NULL CHECK(content_type IN ('list', 'steps', 'text')),
        FOREIGN KEY (manual_id) REFERENCES manuals (manual_id) ON DELETE CASCADE
    );
    """
    # Index for faster lookup by manual_id and order
    sql_create_tabs_index = """
    CREATE INDEX IF NOT EXISTS idx_tabs_manual_order ON tabs (manual_id, tab_order);
    """

    sql_create_tab_content_list_table = """
    CREATE TABLE IF NOT EXISTS tab_content_list (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tab_id INTEGER NOT NULL,
        item_order INTEGER NOT NULL,
        text TEXT NOT NULL,
        FOREIGN KEY (tab_id) REFERENCES tabs (tab_id) ON DELETE CASCADE
    );
    """
    sql_create_list_index = """
    CREATE INDEX IF NOT EXISTS idx_list_tab_order ON tab_content_list (tab_id, item_order);
    """

    sql_create_tab_content_steps_table = """
    CREATE TABLE IF NOT EXISTS tab_content_steps (
        step_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tab_id INTEGER NOT NULL,
        step_order INTEGER NOT NULL,
        text TEXT NOT NULL,
        warning TEXT, -- Optional: Store only with first step? Or separate table? Simpler here for now.
        note TEXT, -- Optional: Store only with last step? Simpler here for now.
        FOREIGN KEY (tab_id) REFERENCES tabs (tab_id) ON DELETE CASCADE
    );
    """
    sql_create_steps_index = """
    CREATE INDEX IF NOT EXISTS idx_steps_tab_order ON tab_content_steps (tab_id, step_order);
    """

    sql_create_tab_content_text_table = """
    CREATE TABLE IF NOT EXISTS tab_content_text (
        text_content_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tab_id INTEGER NOT NULL UNIQUE, -- Assuming one text block per text tab
        text TEXT NOT NULL,
        FOREIGN KEY (tab_id) REFERENCES tabs (tab_id) ON DELETE CASCADE
    );
    """

    # Execute table creation
    execute_sql(conn, sql_create_manuals_table)
    execute_sql(conn, sql_create_tabs_table)
    execute_sql(conn, sql_create_tabs_index)
    execute_sql(conn, sql_create_tab_content_list_table)
    execute_sql(conn, sql_create_list_index)
    execute_sql(conn, sql_create_tab_content_steps_table)
    execute_sql(conn, sql_create_steps_index)
    execute_sql(conn, sql_create_tab_content_text_table)

    print("Database tables checked/created.")

if __name__ == '__main__':
    if os.path.exists(DATABASE_FILE):
        print(f"Database file '{DATABASE_FILE}' already exists.")
        # Optionally add logic here to ask if user wants to proceed/recreate
        # For now, we just connect and ensure tables exist

    conn = create_connection(DATABASE_FILE)
    if conn is not None:
        setup_database(conn)
        conn.close()
        print("Database setup complete. Connection closed.")
    else:
        print("Error! cannot create the database connection.")