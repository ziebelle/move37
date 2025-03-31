import os
import sqlite3
import json

# --- Configuration ---
DATABASE_FILE = 'manuals.db'
OUTPUT_JSON_FILE = 'all_manuals_knowledge.json' # Single file output
# --- End Configuration ---

def create_connection(db_file):
    """ Create a database connection to the SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        print(f"SQLite DB connection successful to {db_file}")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def fetch_all_manual_data(conn):
    """Fetches and structures data for all manuals from the DB."""
    cursor = conn.cursor()
    all_manuals_data = []

    try:
        # Fetch all manuals
        cursor.execute("SELECT * FROM manuals ORDER BY manual_id")
        manuals = cursor.fetchall()

        if not manuals:
            print("No manuals found in the database.")
            return []

        print(f"Found {len(manuals)} manuals. Fetching details...")

        for manual_row in manuals:
            manual_data = dict(manual_row)
            manual_id = manual_data['manual_id']

            # Safely parse JSON fields from DB
            try: manual_data['features'] = json.loads(manual_data.get('features', '[]') or '[]')
            except (json.JSONDecodeError, TypeError): manual_data['features'] = []
            try: manual_data['special_features'] = json.loads(manual_data.get('special_features', '[]') or '[]')
            except (json.JSONDecodeError, TypeError): manual_data['special_features'] = []

            # Fetch tabs for this manual
            cursor.execute("""
                SELECT tab_id, tab_key, title, tab_order, content_type
                FROM tabs WHERE manual_id = ? ORDER BY tab_order
            """, (manual_id,))
            tabs = cursor.fetchall()

            manual_data['tabs'] = [] # Use the key expected by frontend

            for tab_row in tabs:
                tab_data = dict(tab_row)
                tab_id = tab_data['tab_id']
                content_type = tab_data['content_type']
                tab_key = tab_data['tab_key'] # Get tab_key for generating item/step IDs

                # Fetch content based on type
                if content_type == 'list':
                    cursor.execute("SELECT item_order, text FROM tab_content_list WHERE tab_id = ? ORDER BY item_order", (tab_id,))
                    items = cursor.fetchall()
                    # Generate list item objects with IDs
                    tab_data['content'] = [{"id": f"{tab_key}_item_{item['item_order']:02d}", "text": item['text']} for item in items]
                elif content_type == 'steps':
                    cursor.execute("SELECT step_order, text, warning, note FROM tab_content_steps WHERE tab_id = ? ORDER BY step_order", (tab_id,))
                    steps_raw = cursor.fetchall()
                    steps_list = [{"id": f"{tab_key}_step_{step['step_order']:02d}", "text": step['text']} for step in steps_raw]
                    # Get warning/note from first/last step if they exist
                    warning = steps_raw[0]['warning'] if steps_raw and steps_raw[0]['warning'] else None
                    note = steps_raw[-1]['note'] if steps_raw and steps_raw[-1]['note'] else None
                    steps_content = {"steps": steps_list}
                    if warning: steps_content["warning"] = warning
                    if note: steps_content["note"] = note
                    tab_data['content'] = steps_content
                elif content_type == 'text':
                    cursor.execute("SELECT text FROM tab_content_text WHERE tab_id = ?", (tab_id,))
                    text_content = cursor.fetchone()
                    tab_data['content'] = text_content['text'] if text_content else ""
                else:
                    tab_data['content'] = None # Or handle unknown type

                # Use the correct key 'id' for the tab identifier
                tab_data['id'] = tab_key
                # Remove redundant keys fetched from DB if needed
                # del tab_data['tab_key']
                # del tab_data['tab_id']

                manual_data['tabs'].append(tab_data)

            all_manuals_data.append(manual_data)

        return all_manuals_data

    except sqlite3.Error as e:
        print(f"Database error fetching data: {e}")
        return None
    except Exception as e:
        print(f"Error structuring data: {e}")
        return None


if __name__ == '__main__':
    print("--- Starting Database to JSON Export Script ---")
    if not os.path.exists(DATABASE_FILE):
        print(f"Error: Database file '{DATABASE_FILE}' not found.")
    else:
        conn = create_connection(DATABASE_FILE)
        if conn:
            all_data = fetch_all_manual_data(conn)
            conn.close()
            print("Database connection closed.")

            if all_data is not None:
                try:
                    # Ensure output directory exists (optional, saves in current dir)
                    # os.makedirs(os.path.dirname(OUTPUT_JSON_FILE), exist_ok=True)
                    with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                        json.dump(all_data, f, indent=2, ensure_ascii=False)
                    print(f"Successfully exported all manual data to {OUTPUT_JSON_FILE}")
                except IOError as e:
                    print(f"Error writing JSON to file {OUTPUT_JSON_FILE}: {e}")
                except Exception as e:
                    print(f"Unexpected error during JSON writing: {e}")
            else:
                print("Failed to fetch or structure data from database.")
        else:
            print("Database connection failed.")