import os
import sqlite3
import argparse
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# --- Configuration ---
PROJECT_ID = "bliss-hack25fra-9531"
LOCATION = "europe-central2"
DATABASE_FILE = 'manuals.db'
OUTPUT_DIR = 'technisat-manual/public/manual_images'
IMAGEN_MODEL_NAME = "imagegeneration@005" # Stable version
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

def generate_image(prompt, output_filename, model):
    """Generates an image using Vertex AI Imagen and saves it, using a provided model instance."""
    response = None
    enhanced_prompt = f"Technical illustration: {prompt}"
    print(f"Generating image for prompt: '{enhanced_prompt[:70]}...' -> {os.path.basename(output_filename)}")
    try:
        response = model.generate_images(prompt=enhanced_prompt, number_of_images=1)
        if response.images:
            image_bytes = response.images[0]._image_bytes
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            with open(output_filename, 'wb') as img_file: img_file.write(image_bytes)
            return True
        else:
            print(f"Warning: No image generated for prompt. Response: {response}")
            return False
    except Exception as e:
        print(f"Error generating image for prompt '{enhanced_prompt[:70]}...': {e}")
        if response: print(f"Full Response on Error: {response}")
        return False

def get_steps_to_process(conn, manual_id_filter=None): # Renamed arg for clarity
    """Fetches steps data from the database, including manual_id."""
    cursor = conn.cursor()
    # Fetch manual_id along with other details
    query = """
        SELECT t.manual_id, t.tab_key, s.step_order, s.text
        FROM tabs t
        JOIN tab_content_steps s ON t.tab_id = s.tab_id
        WHERE t.content_type = 'steps'
    """
    params = []
    if manual_id_filter:
        query += " AND t.manual_id = ?"
        params.append(manual_id_filter)
    query += " ORDER BY t.manual_id, t.tab_order, s.step_order;"

    try:
        cursor.execute(query, params)
        steps_data = cursor.fetchall()
        print(f"Found {len(steps_data)} steps in the database" + (f" for manual_id {manual_id_filter}." if manual_id_filter else "."))
        return steps_data # Returns list of tuples (manual_id, tab_key, step_order, text)
    except sqlite3.Error as e:
        print(f"Database error fetching steps: {e}")
        return []

def process_images_for_manual(db_file, output_dir, manual_id_filter=None): # Renamed arg
    """Processes image generation for a specific manual_id or all."""
    if not os.path.exists(db_file): print(f"Error: Database file '{db_file}' not found."); return

    conn = create_connection(db_file)
    if conn is None: return

    imagen_model = None
    try:
        print("Initializing Vertex AI and Imagen Model...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        imagen_model = ImageGenerationModel.from_pretrained(IMAGEN_MODEL_NAME)
        print("Vertex AI and Imagen Model initialized.")
    except Exception as e:
        print(f"Error initializing Vertex AI or Imagen Model: {e}")
        if conn: conn.close(); return

    try:
        steps_to_process = get_steps_to_process(conn, manual_id_filter)
        total_steps = len(steps_to_process)
        generated_count = 0

        if total_steps == 0: print("No steps found to generate images for."); return

        if not os.path.exists(output_dir):
            try: os.makedirs(output_dir); print(f"Created output directory: {output_dir}")
            except OSError as e: print(f"Error creating output directory {output_dir}: {e}"); return

        # Iterate through fetched data including manual_id
        for i, (manual_id, tab_key, step_order, step_text) in enumerate(steps_to_process):
            # Construct filename including manual_id
            output_filename = os.path.join(output_dir, f"manual_{manual_id}_{tab_key}_step_{step_order:02d}.png")

            if os.path.exists(output_filename):
                 print(f"Skipping existing image: {output_filename}")
                 continue

            prompt_text = f"Step {step_order + 1}: {step_text}"
            success = generate_image(prompt_text, output_filename, imagen_model)
            if success: generated_count += 1
            print(f"Progress: {i + 1}/{total_steps}")

        print(f"\nImage generation process finished. {generated_count}/{total_steps} images generated (or skipped).")

    finally:
        if conn: conn.close(); print("Database connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for manual steps stored in the database.")
    # Keep argument name consistent
    parser.add_argument("-m", "--manual_id", type=int, help="Optional: Process only steps for a specific manual_id.")
    args = parser.parse_args()

    print("--- Starting Manual Image Generation Script (DB version) ---")
    print(f"Database: {DATABASE_FILE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    if args.manual_id: print(f"Processing Manual ID: {args.manual_id}")
    else: print("Processing all manuals found in DB.")
    print("-" * 40)

    process_images_for_manual(DATABASE_FILE, OUTPUT_DIR, manual_id_filter=args.manual_id) # Pass arg correctly