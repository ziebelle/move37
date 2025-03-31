import os
import sqlite3
import argparse
import vertexai
# Use the specific class for Imagen V2
from vertexai.preview.vision_models import ImageGenerationModel

# --- Configuration ---
PROJECT_ID = "bliss-hack25fra-9531"
LOCATION = "europe-central2"
DATABASE_FILE = 'manuals.db'
OUTPUT_DIR = 'technisat-manual/public/manual_images'
# Optional: Choose a specific Imagen model version if needed
IMAGEN_MODEL_NAME = "imagegeneration@005" # Reverting to stable version 005
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

def generate_image(prompt, output_filename):
    """Generates an image using Vertex AI Imagen and saves it."""
    response = None # Initialize response to None
    # Add step number prefix for better context? Or keep prompt simple?
    # Let's try adding it for now.
    enhanced_prompt = f"Technical illustration: {prompt}"
    print(f"Generating image for prompt: '{enhanced_prompt[:70]}...'")
    try:
        # Ensure Vertex AI is initialized (can be done once outside the loop too)
        # vertexai.init(project=PROJECT_ID, location=LOCATION) # Moved initialization to main
        model = ImageGenerationModel.from_pretrained(IMAGEN_MODEL_NAME)
        response = model.generate_images(
            prompt=enhanced_prompt,
            number_of_images=1,
            # aspect_ratio="16:9" # Optional: Set aspect ratio if desired
        )

        if response.images:
            image_bytes = response.images[0]._image_bytes
            # Ensure the output directory exists before saving
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'wb') as img_file:
                img_file.write(image_bytes)
            print(f"Successfully saved image to {output_filename}")
            return True
        else:
            print(f"Warning: No image generated for prompt. Response: {response}")
            return False

    except Exception as e:
        print(f"Error generating image for prompt '{enhanced_prompt[:70]}...': {e}")
        # Log response details if available and helpful
        if 'response' in locals() and response:
             print(f"Full Response on Error: {response}")
        return False

def get_steps_to_process(conn, manual_id=None):
    """Fetches steps data from the database."""
    cursor = conn.cursor()
    query = """
        SELECT t.tab_key, s.step_order, s.text
        FROM tabs t
        JOIN tab_content_steps s ON t.tab_id = s.tab_id
        WHERE t.content_type = 'steps'
    """
    params = []
    if manual_id:
        query += " AND t.manual_id = ?"
        params.append(manual_id)
    query += " ORDER BY t.manual_id, t.tab_order, s.step_order;"

    try:
        cursor.execute(query, params)
        steps_data = cursor.fetchall()
        print(f"Found {len(steps_data)} steps in the database" + (f" for manual_id {manual_id}." if manual_id else "."))
        return steps_data
    except sqlite3.Error as e:
        print(f"Database error fetching steps: {e}")
        return []

def main(manual_id=None):
    """Main function to fetch steps from DB, generate images, and save them."""
    if not os.path.exists(DATABASE_FILE):
        print(f"Error: Database file '{DATABASE_FILE}' not found. Please run setup_database.py and convert_manual_to_db.py first.")
        return

    conn = create_connection(DATABASE_FILE)
    if conn is None:
        return

    try:
        # Initialize Vertex AI (only once)
        print("Initializing Vertex AI...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        print("Vertex AI initialized.")

        steps_to_process = get_steps_to_process(conn, manual_id)
        total_steps = len(steps_to_process)
        generated_count = 0

        if total_steps == 0:
            print("No steps found to generate images for.")
            return

        # Create base output directory if it doesn't exist
        if not os.path.exists(OUTPUT_DIR):
            try:
                os.makedirs(OUTPUT_DIR)
                print(f"Created output directory: {OUTPUT_DIR}")
            except OSError as e:
                print(f"Error creating output directory {OUTPUT_DIR}: {e}")
                return # Cannot proceed without output dir

        for i, (tab_key, step_order, step_text) in enumerate(steps_to_process):
            # Use 0-based index (step_order) for filename consistency with React app
            # Pad with 2 digits
            output_filename = os.path.join(OUTPUT_DIR, f"{tab_key}_step_{step_order:02d}.png")

            # Optional: Check if image already exists to avoid regeneration
            if os.path.exists(output_filename):
                 print(f"Skipping existing image: {output_filename}")
                 continue

            # Add step number to the text for context in the prompt
            prompt_text = f"Step {step_order + 1}: {step_text}"
            success = generate_image(prompt_text, output_filename)
            if success:
                generated_count += 1
            print(f"Progress: {i + 1}/{total_steps}")

        print(f"\nImage generation process finished. {generated_count}/{total_steps} images generated (or skipped if existing).")

    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for manual steps stored in the database.")
    parser.add_argument("-m", "--manual_id", type=int, help="Optional: Process only steps for a specific manual_id.")
    args = parser.parse_args()

    print("--- Starting Manual Image Generation Script (DB version) ---")
    print(f"Database: {DATABASE_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    if args.manual_id:
        print(f"Processing Manual ID: {args.manual_id}")
    else:
        print("Processing all manuals found in DB.")
    print("-" * 40)

    main(manual_id=args.manual_id)