import os
import sqlite3
import argparse
from google.cloud import texttospeech

# --- Configuration ---
PROJECT_ID = 'bliss-hack25fra-9531'
LOCATION = "europe-central2" # Not strictly needed for TTS, but good practice
DATABASE_FILE = 'manuals.db'
OUTPUT_DIR = 'technisat-manual/public/manual_audio'
# Optional: Customize voice settings
VOICE_LANGUAGE_CODE = 'en-US'
VOICE_NAME = 'en-US-Standard-J' # Example voice
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
    # Basic text cleaning (remove potential SSML-like tags if not intended)
    clean_text = text.replace('<', '').replace('>', '')
    if not clean_text.strip():
        print(f"Skipping empty text for {output_filename}")
        return False

    try:
        synthesis_input = texttospeech.SynthesisInput(text=clean_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=VOICE_LANGUAGE_CODE, name=VOICE_NAME
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=AUDIO_ENCODING # WAV
        )

        print(f"Synthesizing audio for: '{clean_text[:60]}...' -> {os.path.basename(output_filename)}")
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)

        # Write the response to the output file.
        with open(output_filename, "wb") as out:
            out.write(response.audio_content)
            # print(f'Audio content written to file "{output_filename}"') # Reduce verbosity
        return True

    except Exception as e:
        print(f"Error synthesizing speech for '{clean_text[:60]}...': {e}")
        return False

def get_content_to_process(conn, manual_id=None):
    """Fetches all relevant text content from the database."""
    cursor = conn.cursor()
    content_items = [] # List to hold tuples: (tab_key, type, order, text)

    # Base query for tabs
    tab_query = "SELECT tab_id, tab_key, content_type FROM tabs"
    tab_params = []
    if manual_id:
        tab_query += " WHERE manual_id = ?"
        tab_params.append(manual_id)
    tab_query += " ORDER BY manual_id, tab_order;"

    try:
        cursor.execute(tab_query, tab_params)
        tabs = cursor.fetchall()
        print(f"Found {len(tabs)} tabs to process.")

        for tab_id, tab_key, content_type in tabs:
            if content_type == 'steps':
                cursor.execute("""
                    SELECT step_order, text FROM tab_content_steps
                    WHERE tab_id = ? ORDER BY step_order
                """, (tab_id,))
                steps = cursor.fetchall()
                for step_order, text in steps:
                    # Add step number prefix for clarity in audio
                    audio_text = f"Step {step_order + 1}. {text}"
                    content_items.append((tab_key, 'step', step_order, audio_text))
            elif content_type == 'list':
                 cursor.execute("""
                     SELECT item_order, text FROM tab_content_list
                     WHERE tab_id = ? ORDER BY item_order
                 """, (tab_id,))
                 items = cursor.fetchall()
                 for item_order, text in items:
                     content_items.append((tab_key, 'item', item_order, text))
            elif content_type == 'text':
                 cursor.execute("SELECT text FROM tab_content_text WHERE tab_id = ?", (tab_id,))
                 result = cursor.fetchone()
                 if result:
                     content_items.append((tab_key, 'main', 0, result[0])) # Use 0 for order/index

        print(f"Found {len(content_items)} total text items to synthesize.")
        return content_items

    except sqlite3.Error as e:
        print(f"Database error fetching content: {e}")
        return []


def main(manual_id=None):
    """Main function to fetch text from DB, generate audio, and save them."""
    if not os.path.exists(DATABASE_FILE):
        print(f"Error: Database file '{DATABASE_FILE}' not found. Please run setup_database.py and convert_manual_to_db.py first.")
        return

    conn = create_connection(DATABASE_FILE)
    if conn is None: return

    # Initialize TTS Client once
    try:
        print("Initializing Google Cloud Text-to-Speech client...")
        tts_client = texttospeech.TextToSpeechClient()
        print("Text-to-Speech client initialized.")
    except Exception as e:
        print(f"Error initializing Google Cloud Text-to-Speech client: {e}")
        print("Please ensure credentials (ADC) are configured correctly and the API is enabled.")
        if conn: conn.close()
        return

    try:
        content_to_process = get_content_to_process(conn, manual_id)
        total_items = len(content_to_process)
        generated_count = 0

        if total_items == 0:
            print("No text content found to generate audio for.")
            return

        # Create base output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            try:
                os.makedirs(OUTPUT_DIR)
                print(f"Created output directory: {OUTPUT_DIR}")
            except OSError as e:
                print(f"Error creating output directory {OUTPUT_DIR}: {e}")
                return # Cannot proceed

        for i, (tab_key, item_type, item_order, text) in enumerate(content_to_process):
            # Construct filename based on type and order/index
            if item_type == 'step':
                filename = f"{tab_key}_step_{item_order:02d}.wav"
            elif item_type == 'item':
                filename = f"{tab_key}_item_{item_order:02d}.wav"
            elif item_type == 'main':
                filename = f"{tab_key}_main.wav"
            else:
                print(f"Warning: Unknown item type '{item_type}'. Skipping.")
                continue

            output_filename = os.path.join(OUTPUT_DIR, filename)

            # Optional: Check if audio already exists
            if os.path.exists(output_filename):
                 print(f"Skipping existing audio: {output_filename}")
                 continue

            success = synthesize_speech(text, output_filename, tts_client)
            if success:
                generated_count += 1
            print(f"Progress: {i + 1}/{total_items}")

        print(f"\nAudio generation process finished. {generated_count}/{total_items} files generated (or skipped if existing).")

    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate audio for manual content stored in the database.")
    parser.add_argument("-m", "--manual_id", type=int, help="Optional: Process only content for a specific manual_id.")
    args = parser.parse_args()

    print("--- Starting Manual Audio Generation Script (DB version) ---")
    print(f"Database: {DATABASE_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    if args.manual_id:
        print(f"Processing Manual ID: {args.manual_id}")
    else:
        print("Processing all manuals found in DB.")
    print("-" * 40)

    main(manual_id=args.manual_id)