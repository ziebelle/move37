import os
import sqlite3
import argparse
from google.cloud import texttospeech

# --- Configuration ---
PROJECT_ID = 'bliss-hack25fra-9531'
LOCATION = "europe-central2"
DATABASE_FILE = 'manuals.db'
OUTPUT_DIR = 'technisat-manual/public/manual_audio'
VOICE_LANGUAGE_CODE = 'en-US'
VOICE_NAME = 'en-US-Standard-J'
AUDIO_ENCODING = texttospeech.AudioEncoding.LINEAR16 # WAV format
# --- End Configuration ---

def create_connection(db_file):
    """ Create a database connection to the SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"SQLite DB connection successful to {db_file}")
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def synthesize_speech(text, output_filename, client):
    """Synthesizes speech from text and saves to a file using a provided client."""
    clean_text = text.replace('<', '').replace('>', '')
    if not clean_text.strip():
        print(f"Skipping empty text for {output_filename}")
        return False
    try:
        synthesis_input = texttospeech.SynthesisInput(text=clean_text)
        voice = texttospeech.VoiceSelectionParams(language_code=VOICE_LANGUAGE_CODE, name=VOICE_NAME)
        audio_config = texttospeech.AudioConfig(audio_encoding=AUDIO_ENCODING)

        print(f"Synthesizing audio for: '{clean_text[:60]}...' -> {os.path.basename(output_filename)}")
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, "wb") as out:
            out.write(response.audio_content)
        return True
    except Exception as e:
        print(f"Error synthesizing speech for '{clean_text[:60]}...': {e}")
        return False

def get_content_to_process(conn, manual_id_filter=None): # Renamed arg
    """Fetches all relevant text content from the database, including manual_id."""
    cursor = conn.cursor()
    # List to hold tuples: (manual_id, tab_key, type, order/index, text, item_db_id)
    content_items = []

    # Fetch manual_id along with tab info
    tab_query = "SELECT manual_id, tab_id, tab_key, content_type FROM tabs"
    tab_params = []
    if manual_id_filter:
        tab_query += " WHERE manual_id = ?"
        tab_params.append(manual_id_filter)
    tab_query += " ORDER BY manual_id, tab_order;"

    try:
        cursor.execute(tab_query, tab_params)
        tabs = cursor.fetchall()
        print(f"Found {len(tabs)} tabs to process for audio.")

        for manual_id, tab_id, tab_key, content_type in tabs:
            if content_type == 'steps':
                cursor.execute("SELECT step_order, text FROM tab_content_steps WHERE tab_id = ? ORDER BY step_order", (tab_id,))
                steps = cursor.fetchall()
                for step_order, text in steps:
                    audio_text = f"Step {step_order + 1}. {text}"
                    item_db_id = f"{tab_key}_step_{step_order:02d}" # ID used for linking
                    content_items.append((manual_id, tab_key, 'step', step_order, audio_text, item_db_id))
            elif content_type == 'list':
                 cursor.execute("SELECT item_order, text FROM tab_content_list WHERE tab_id = ? ORDER BY item_order", (tab_id,))
                 items = cursor.fetchall()
                 for item_order, text in items:
                     item_db_id = f"{tab_key}_item_{item_order:02d}" # ID used for linking
                     content_items.append((manual_id, tab_key, 'item', item_order, text, item_db_id))
            elif content_type == 'text':
                 cursor.execute("SELECT text FROM tab_content_text WHERE tab_id = ?", (tab_id,))
                 result = cursor.fetchone()
                 if result:
                     item_db_id = f"{tab_key}_main" # ID used for linking
                     content_items.append((manual_id, tab_key, 'main', 0, result[0], item_db_id))

        print(f"Found {len(content_items)} total text items to synthesize.")
        return content_items
    except sqlite3.Error as e:
        print(f"Database error fetching content: {e}")
        return []


def process_audio_for_manual(db_file, output_dir, manual_id_filter=None): # Renamed arg
    """Processes audio generation for a specific manual_id or all."""
    if not os.path.exists(db_file): print(f"Error: Database file '{db_file}' not found."); return

    conn = create_connection(db_file)
    if conn is None: return

    tts_client = None
    try:
        print("Initializing Google Cloud Text-to-Speech client...")
        tts_client = texttospeech.TextToSpeechClient()
        print("Text-to-Speech client initialized.")
    except Exception as e:
        print(f"Error initializing TTS client: {e}");
        if conn: conn.close(); return

    try:
        content_to_process = get_content_to_process(conn, manual_id_filter)
        total_items = len(content_to_process)
        generated_count = 0

        if total_items == 0: print("No text content found."); return

        if not os.path.exists(output_dir):
            try: os.makedirs(output_dir); print(f"Created output directory: {output_dir}")
            except OSError as e: print(f"Error creating output directory {output_dir}: {e}"); return

        # Iterate through fetched data including manual_id and item_db_id
        for i, (manual_id, tab_key, item_type, item_order, text, item_db_id) in enumerate(content_to_process):
            # Construct filename including manual_id and the item's specific ID
            filename = f"manual_{manual_id}_{item_db_id}.wav"
            output_filename = os.path.join(output_dir, filename)

            if os.path.exists(output_filename):
                 print(f"Skipping existing audio: {output_filename}")
                 continue

            success = synthesize_speech(text, output_filename, tts_client)
            if success: generated_count += 1
            print(f"Progress: {i + 1}/{total_items}")

        print(f"\nAudio generation process finished. {generated_count}/{total_items} files generated (or skipped).")

    finally:
        if conn: conn.close(); print("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate audio for manual content stored in the database.")
    # Keep argument name consistent
    parser.add_argument("-m", "--manual_id", type=int, help="Optional: Process only content for a specific manual_id.")
    args = parser.parse_args()

    print("--- Starting Manual Audio Generation Script (DB version) ---")
    print(f"Database: {DATABASE_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    if args.manual_id: print(f"Processing Manual ID: {args.manual_id}")
    else: print("Processing all manuals found in DB.")
    print("-" * 40)

    process_audio_for_manual(DATABASE_FILE, OUTPUT_DIR, manual_id_filter=args.manual_id) # Pass arg correctly