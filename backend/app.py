import sqlite3
import json
import os # <-- Import the os module
from flask import Flask, jsonify, abort
from flask_cors import CORS # To handle Cross-Origin Resource Sharing

app = Flask(__name__)
CORS(app) # Allow requests from your React frontend development server

DATABASE_FILE = 'manuals.db' # Path relative to project root (where script is run from)

def get_db_connection():
    """Connects to the specific database."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/api/manuals', methods=['GET'])
def get_manuals_list():
    """Returns a list of available manuals."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    try:
        manuals = conn.execute('SELECT manual_id, title, source_path FROM manuals ORDER BY title').fetchall()
        conn.close()
        # Convert Row objects to dictionaries
        manuals_list = [dict(row) for row in manuals]
        return jsonify(manuals_list)
    except sqlite3.Error as e:
        print(f"Error fetching manuals list: {e}")
        if conn: conn.close()
        return jsonify({"error": "Failed to fetch manuals list"}), 500


@app.route('/api/manuals/<int:manual_id>', methods=['GET'])
def get_manual_details(manual_id):
    """Returns the structured data for a specific manual."""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Fetch manual metadata
        manual_meta = conn.execute('SELECT * FROM manuals WHERE manual_id = ?', (manual_id,)).fetchone()
        if manual_meta is None:
            conn.close()
            abort(404, description="Manual not found")

        output_data = dict(manual_meta) # Start with manual metadata
        # Safely parse JSON fields
        try:
            output_data['features'] = json.loads(output_data.get('features', '[]') or '[]')
        except (json.JSONDecodeError, TypeError):
             output_data['features'] = []
        try:
            output_data['special_features'] = json.loads(output_data.get('special_features', '[]') or '[]')
        except (json.JSONDecodeError, TypeError):
             output_data['special_features'] = []


        # Fetch tabs
        tabs = conn.execute("""
            SELECT tab_id, tab_key, title, tab_order, content_type
            FROM tabs WHERE manual_id = ? ORDER BY tab_order
        """, (manual_id,)).fetchall()

        output_data['tabs'] = []

        for tab_row in tabs:
            tab_data = dict(tab_row)
            tab_id = tab_data['tab_id']
            content_type = tab_data['content_type']

            # Fetch content based on type
            if content_type == 'list':
                items = conn.execute("""
                    SELECT item_order, text FROM tab_content_list
                    WHERE tab_id = ? ORDER BY item_order
                """, (tab_id,)).fetchall()
                # Structure items with id (using tab_key and order) and text
                tab_data['content'] = [
                    {"id": f"{tab_data['tab_key']}_item_{item['item_order']:02d}", "text": item['text']}
                    for item in items
                ]
            elif content_type == 'steps':
                steps_raw = conn.execute("""
                    SELECT step_order, text, warning, note FROM tab_content_steps
                    WHERE tab_id = ? ORDER BY step_order
                """, (tab_id,)).fetchall()
                steps_content = {
                    "warning": steps_raw[0]['warning'] if steps_raw and steps_raw[0]['warning'] else None,
                    "steps": [
                        {"id": f"{tab_data['tab_key']}_step_{step['step_order']:02d}", "text": step['text']}
                        for step in steps_raw
                    ],
                    "note": steps_raw[-1]['note'] if steps_raw and steps_raw[-1]['note'] else None
                }
                # Remove warning/note if they are None
                if steps_content["warning"] is None: del steps_content["warning"]
                if steps_content["note"] is None: del steps_content["note"]
                tab_data['content'] = steps_content

            elif content_type == 'text':
                text_content = conn.execute("SELECT text FROM tab_content_text WHERE tab_id = ?", (tab_id,)).fetchone()
                tab_data['content'] = text_content['text'] if text_content else ""

            output_data['tabs'].append(tab_data)

        conn.close()
        return jsonify(output_data)

    except sqlite3.Error as e:
        print(f"Error fetching details for manual {manual_id}: {e}")
        if conn: conn.close()
        return jsonify({"error": f"Failed to fetch details for manual {manual_id}"}), 500
    except Exception as e:
         print(f"Unexpected error for manual {manual_id}: {e}")
         if conn: conn.close()
         return jsonify({"error": "An unexpected error occurred"}), 500


if __name__ == '__main__':
    # Check if database exists before starting
    if not os.path.exists(DATABASE_FILE):
        print(f"ERROR: Database file '{DATABASE_FILE}' not found.")
        print("Please run 'python setup_database.py' first.")
    else:
        print(f"Starting Flask server, serving data from {DATABASE_FILE}")
        # Host='0.0.0.0' makes it accessible on your network
        # Debug=True enables auto-reloading and debug messages
        app.run(host='0.0.0.0', port=5001, debug=True)