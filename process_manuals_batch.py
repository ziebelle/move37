import os
import glob
import argparse
import sqlite3 # Needed to potentially get manual_id if conversion skipped but assets needed

# Import functions from the other scripts
# Ensure these scripts are in the same directory or accessible via PYTHONPATH
from convert_manual_to_db import process_single_manual, DATABASE_FILE as CONVERT_DB_FILE
# Import the refactored function for image generation
from generate_manual_images import process_images_for_manual, DATABASE_FILE as IMG_DB_FILE, OUTPUT_DIR as IMG_OUT_DIR
from generate_manual_audio import process_audio_for_manual, DATABASE_FILE as AUDIO_DB_FILE, OUTPUT_DIR as AUDIO_OUT_DIR

# --- Configuration ---
MANUALS_SOURCE_DIR = "ProduktAssets/TechniSat/BDA/"
FILE_PATTERN = "*.pdf" # Process only PDF files
MAX_FILES_TO_PROCESS = 10 # Limit the number of files processed in one run
# --- End Configuration ---

def get_manual_id_by_source(conn, source_path):
    """Gets the manual_id for a given source_path if it exists."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT manual_id FROM manuals WHERE source_path = ?", (source_path,))
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Error querying manual_id for {source_path}: {e}")
        return None

def main(limit):
    """Finds PDFs and processes them."""
    source_pattern = os.path.join(MANUALS_SOURCE_DIR, FILE_PATTERN)
    pdf_files = glob.glob(source_pattern)

    if not pdf_files:
        print(f"No files found matching pattern: {source_pattern}")
        return

    print(f"Found {len(pdf_files)} files matching pattern.")
    files_to_process = pdf_files[:limit]
    print(f"Processing the first {len(files_to_process)} files...")

    processed_count = 0
    error_count = 0
    skipped_count = 0 # Count skipped due to already existing

    # Ensure database exists before starting batch
    if not os.path.exists(CONVERT_DB_FILE):
         print(f"Error: Database file '{CONVERT_DB_FILE}' not found. Please run setup_database.py first.")
         return

    for pdf_path in files_to_process:
        print(f"\n===== Processing: {os.path.basename(pdf_path)} =====")
        manual_id = None
        try:
            # 1. Convert PDF to DB entry
            # process_single_manual returns the manual_id (new or existing) or None on failure
            manual_id = process_single_manual(pdf_path, CONVERT_DB_FILE)

            if manual_id is not None:
                # Manual was newly inserted or already existed and ID was returned
                # 2. Generate Images for this manual_id
                print(f"\n--- Generating images for manual_id: {manual_id} ---")
                # Call the refactored image generation function using correct arg name
                process_images_for_manual(IMG_DB_FILE, IMG_OUT_DIR, manual_id_filter=manual_id)

                # 3. Generate Audio for this manual_id
                print(f"\n--- Generating audio for manual_id: {manual_id} ---")
                process_audio_for_manual(AUDIO_DB_FILE, AUDIO_OUT_DIR, manual_id_filter=manual_id)

                # Increment count only if it was newly processed (not just assets for existing)
                # We need process_single_manual to better indicate if it was new vs existing skip
                # For now, let's assume if manual_id is returned, it's "processed" in some way
                processed_count += 1
            else:
                # This case means process_single_manual failed (returned None)
                print(f"Skipping asset generation for {pdf_path} due to conversion/parsing failure.")
                error_count += 1

        except Exception as e:
            print(f"!! Unexpected error processing {pdf_path}: {e}")
            error_count += 1

    print(f"\n===== Batch Processing Complete =====")
    print(f"Manuals processed (conversion attempted/assets generated): {processed_count}")
    print(f"Errors encountered during processing: {error_count}")
    # Note: The logic doesn't explicitly track skipped-due-to-existing anymore,
    # as process_single_manual now returns the existing ID.


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Batch process PDF manuals from {MANUALS_SOURCE_DIR}.")
    parser.add_argument("-n", "--limit", type=int, default=MAX_FILES_TO_PROCESS,
                        help=f"Maximum number of PDF files to process (default: {MAX_FILES_TO_PROCESS}).")
    args = parser.parse_args()

    main(limit=args.limit)