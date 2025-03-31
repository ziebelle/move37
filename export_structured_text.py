import os
import sqlite3
import json
import argparse

# --- Configuration ---
DATABASE_FILE = 'manuals.db'
OUTPUT_TEXT_DIR = 'manuals_text_export' # Directory to save the .txt files
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

def format_manual_text(conn, manual_id):
    """Fetches structured data for a manual and formats it as text."""
    cursor = conn.cursor()
    output_lines = []

    try:
        # Fetch manual metadata
        cursor.execute("SELECT title, features, special_features FROM manuals WHERE manual_id = ?", (manual_id,))
        manual_meta = cursor.fetchone()
        if not manual_meta:
            print(f"Manual ID {manual_id} not found.")
            return None

        output_lines.append(f"# {manual_meta['title']}\n")

        features = json.loads(manual_meta['features'] or '[]')
        if features:
            output_lines.append("## Features\n")
            for item in features:
                output_lines.append(f"- {item}")
            output_lines.append("") # Add newline

        special_features = json.loads(manual_meta['special_features'] or '[]')
        if special_features:
            output_lines.append("## Special Features\n")
            for item in special_features:
                output_lines.append(f"- {item}")
            output_lines.append("") # Add newline

        # Fetch tabs and their content
        cursor.execute("""
            SELECT tab_id, title, content_type FROM tabs
            WHERE manual_id = ? ORDER BY tab_order
        """, (manual_id,))
        tabs = cursor.fetchall()

        for tab in tabs:
            tab_id = tab['tab_id']
            tab_title = tab['title']
            content_type = tab['content_type']

            output_lines.append(f"## {tab_title}\n") # Use tab title as heading

            if content_type == 'list':
                cursor.execute("SELECT text FROM tab_content_list WHERE tab_id = ? ORDER BY item_order", (tab_id,))
                items = cursor.fetchall()
                for item in items:
                    output_lines.append(f"- {item['text']}")
            elif content_type == 'steps':
                cursor.execute("SELECT step_order, text, warning, note FROM tab_content_steps WHERE tab_id = ? ORDER BY step_order", (tab_id,))
                steps = cursor.fetchall()
                # Check for warning on first step
                if steps and steps[0]['warning']:
                    output_lines.append(f"**Warning:** {steps[0]['warning']}\n")
                # List steps
                for i, step in enumerate(steps):
                    output_lines.append(f"{i + 1}. {step['text']}")
                # Check for note on last step
                if steps and steps[-1]['note']:
                    output_lines.append(f"\n*Note:* {steps[-1]['note']}")
            elif content_type == 'text':
                cursor.execute("SELECT text FROM tab_content_text WHERE tab_id = ?", (tab_id,))
                text_content = cursor.fetchone()
                if text_content:
                    output_lines.append(text_content['text'])

            output_lines.append("") # Add newline after each tab section

        return "\n".join(output_lines)

    except sqlite3.Error as e:
        print(f"Database error fetching data for manual {manual_id}: {e}")
        return None
    except Exception as e:
        print(f"Error formatting text for manual {manual_id}: {e}")
        return None


def export_all_manuals_structured(conn, output_dir):
    """Fetches all manual IDs, formats their text, and saves to files."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT manual_id FROM manuals ORDER BY manual_id")
        manual_ids = [row['manual_id'] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database error fetching manual IDs: {e}")
        return 0, 0

    if not manual_ids:
        print("No manuals found in the database.")
        return 0, 0

    print(f"Found {len(manual_ids)} manuals in the database.")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    success_count = 0
    error_count = 0

    for manual_id in manual_ids:
        print("-" * 20)
        print(f"Processing Manual ID: {manual_id}")
        output_filename = os.path.join(output_dir, f"manual_{manual_id}_structured.txt")

        formatted_text = format_manual_text(conn, manual_id)

        if formatted_text:
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(formatted_text)
                print(f"  Successfully saved structured text to {output_filename}")
                success_count += 1
            except IOError as e:
                print(f"  Error writing text file {output_filename}: {e}")
                error_count += 1
        else:
            print(f"  Failed to format or retrieve text for manual ID {manual_id}.")
            error_count += 1

    return success_count, error_count

if __name__ == '__main__':
    print("--- Starting Structured Text Export Script ---")
    if not os.path.exists(DATABASE_FILE):
        print(f"Error: Database file '{DATABASE_FILE}' not found.")
    else:
        conn = create_connection(DATABASE_FILE)
        if conn:
            success, errors = export_all_manuals_structured(conn, OUTPUT_TEXT_DIR)
            conn.close()
            print("\n--- Export Complete ---")
            print(f"Successfully exported: {success}")
            print(f"Errors encountered: {errors}")
        else:
            print("Database connection failed.")