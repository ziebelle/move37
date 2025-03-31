import json
import os
import mimetypes # To guess MIME type
import sqlite3
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content # Keep Content import

# --- Configuration ---
PROJECT_ID = "bliss-hack25fra-9531"
LOCATION = "europe-central2"
# Use a more powerful Gemini model
MODEL_NAME = "gemini-2.0-flash"
DATABASE_FILE = 'manuals.db'

# --- File Paths (Modify these) ---
INPUT_MANUAL_PATH = "ProduktAssets/TechniSat/BDA/bda_DigiBox_1_001.pdf" # Example path
# --- End Configuration ---

# --- Target JSON Schema Description (for prompting the LLM) ---
# Describes the NEW desired *structure*.
NEW_TARGET_SCHEMA_DESCRIPTION = """
{
  "title": "string (Main title of the manual - translated to English)",
  "features": ["string (List of key product features - translated to English, if present)"],
  "specialFeatures": ["string (List of special characteristics or highlights - translated to English, if present)"],
  "sourcePdfPath": "string (Path to the original PDF used for generation)",
  "tabs": [
    // EXPECTING ONLY TABS WITH THE FOLLOWING IDs (if content exists):
    // 'systemRequirements', 'hardwareInstallation', 'driverInstallation', 'softwareInstallation', 'usage'
    {
      "id": "string (MUST be one of: 'systemRequirements', 'hardwareInstallation', 'driverInstallation', 'softwareInstallation', 'usage')",
      "title": "string (MUST be one of: 'System Requirements', 'Hardware Installation', 'Driver Installation', 'Software Installation', 'Usage' - translated to English)",
      "type": "'list' | 'steps' | 'text' (The type of content this tab holds)",
      "content": "string[] | StepContent | string (The actual content, structure depends on 'type')"
      // For type='list', content is string[] (translated to English)
      // For type='steps', content is StepContent object (all strings translated to English)
      // For type='text', content is a single string (translated to English)
    }
    // ... only tabs for the core topics mentioned ...
  ]
}

// StepContent object structure (used when type='steps'):
// {
//   "warning": "string (Optional: Warning for this section - translated to English)",
//   "steps": ["string (List of steps - translated to English)"],
//   "note": "string (Optional: Note for this section - translated to English)"
// }
"""

def extract_text_from_txt(txt_path):
    """Extracts text content from a TXT file."""
    print(f"Reading text file: {txt_path}")
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"Read {len(text)} characters.")
        return text
    except Exception as e:
        print(f"Error reading text file {txt_path}: {e}")
        return None

def parse_manual_with_llm(manual_file_path):
    """Uses Vertex AI Gemini to parse a manual file (PDF/TXT) into the new JSON schema and translate to English."""
    print(f"Processing file for LLM parsing: {manual_file_path}")
    raw_response_text = "" # Initialize
    response = None # Initialize response

    try:
        # Read file bytes
        with open(manual_file_path, "rb") as f:
            file_bytes = f.read()

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(manual_file_path)
        if not mime_type:
            if manual_file_path.lower().endswith(".pdf"): mime_type = "application/pdf"
            elif manual_file_path.lower().endswith(".txt"): mime_type = "text/plain"
            else: mime_type = "text/plain"; print(f"Warning: Could not determine MIME type for {manual_file_path}. Assuming text/plain.")

        print(f"Detected MIME type: {mime_type}")

        # --- Base Prompt Instructions ---
        prompt_header = f"""
Analyze the provided technical manual content (either text or PDF). Structure its content into a JSON object adhering to the NEW schema described below.
**IMPORTANT: Translate ALL extracted text content (titles, features, steps, notes, section text, etc.) into English before placing it into the JSON structure.**
Add the original PDF path "{manual_file_path}" to the `sourcePdfPath` field.

Target JSON Schema Description:
{NEW_TARGET_SCHEMA_DESCRIPTION}

Detailed Instructions:
1. Identify the main title. Translate it to English for the top-level "title" value.
2. Extract top-level list sections like "Features" and "Special Features". Use the keys `features` and `specialFeatures`. Translate each list item to English. Omit keys if the section is absent.
3. **Identify content specifically related to the following core topics ONLY:** System Requirements, Hardware Installation/Setup, Driver Installation, Software Installation/Application Setup, Usage/Operation.
4. **Create a maximum of 5 tab objects** in the top-level "tabs" array, one for each core topic found above. **Group related content logically under these specific tabs.** Do NOT create tabs for other sections like safety, troubleshooting, etc.
5. For each core topic found, create ONE corresponding tab object using the specific `id` and `title` from the schema description (e.g., `id: 'systemRequirements'`, `title: 'System Requirements'`). Determine the `type` ('list', 'steps', or 'text') and populate `content` accordingly, translating all text to English. For 'steps', combine related steps and extract associated warnings/notes.
6. If content for a core topic is not found, omit that tab object.
7. Ensure the final output is ONLY the valid JSON object, without any introductory text, explanations, or markdown formatting.
"""

        # --- Construct prompt_parts based on file type ---
        # The API expects a list containing Part objects for multimodal input
        prompt_parts: list[Part] = [] # Explicitly list of Part

        if mime_type == "text/plain":
            manual_content = extract_text_from_txt(manual_file_path)
            if not manual_content: return None
            full_prompt_text = (
                prompt_header +
                "\nManual Text:\n--- START TEXT ---\n" +
                manual_content[:100000] + # Limit text size
                "\n--- END TEXT ---\n\nGenerate the translated English JSON object according to the NEW schema and specific tab instructions now:"
            )
            # Create a Part object from the text
            prompt_parts.append(Part.from_text(full_prompt_text))
        elif mime_type == "application/pdf":
            file_part = Part.from_data(data=file_bytes, mime_type=mime_type)
            instruction_part_text = (
                prompt_header +
                "\nGenerate the translated English JSON object based *only* on the provided PDF file, following the NEW schema and specific tab instructions:"
            )
            # Create Part objects for both file and text instructions
            prompt_parts = [file_part, Part.from_text(instruction_part_text)]
        else:
            print(f"Error: Unsupported MIME type '{mime_type}' for processing.")
            return None


        print(f"Sending request to Gemini model ({MODEL_NAME})...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)

        generation_config = {
            "temperature": 0.1, "top_p": 0.95, "top_k": 40,
            "max_output_tokens": 8192, "response_mime_type": "application/json",
        }

        # Pass the list of Part objects
        response = model.generate_content(
            contents=prompt_parts, # Pass the list of Parts here
            generation_config=generation_config
            )

        print("Received response from model.")
        if not response.candidates or not response.candidates[0].content.parts:
             print("Error: Model response did not contain expected content parts.")
             if hasattr(response, 'prompt_feedback'): print(f"Prompt Feedback: {response.prompt_feedback}")
             if response.candidates and hasattr(response.candidates[0], 'finish_reason'): print(f"Finish Reason: {response.candidates[0].finish_reason}")
             if response.candidates and hasattr(response.candidates[0], 'safety_ratings'): print(f"Safety Ratings: {response.candidates[0].safety_ratings}")
             return None

        raw_response_text = response.candidates[0].content.parts[0].text
        json_data = json.loads(raw_response_text)
        print("Successfully parsed response as JSON.")
        # Ensure source path is in the final data
        if "sourcePdfPath" not in json_data:
             json_data["sourcePdfPath"] = manual_file_path
        return json_data

    except FileNotFoundError: print(f"Error: Input file not found at {manual_file_path}"); return None
    except json.JSONDecodeError as json_err:
        print(f"Error: Failed to parse LLM response as JSON: {json_err}")
        print("--- Raw Response Text ---\n", raw_response_text if 'raw_response_text' in locals() else "N/A", "\n--- End Raw Response Text ---")
        return None
    except Exception as e:
        print(f"Error during processing or Vertex AI interaction: {e}")
        if response and hasattr(response, 'prompt_feedback'): print(f"Prompt Feedback: {response.prompt_feedback}")
        if response and response.candidates and hasattr(response.candidates[0], 'finish_reason'): print(f"Finish Reason: {response.candidates[0].finish_reason}")
        if response and response.candidates and hasattr(response.candidates[0], 'safety_ratings'): print(f"Safety Ratings: {response.candidates[0].safety_ratings}")
        if 'raw_response_text' in locals() and raw_response_text: print("--- Raw Response Text ---\n", raw_response_text, "\n--- End Raw Response Text ---")
        return None

def insert_manual_data(conn, data):
    """Inserts parsed manual data into the SQLite database."""
    cursor = conn.cursor()
    source_path = data.get("sourcePdfPath")
    title = data.get("title", "Untitled Manual")

    if not source_path:
        print("Error: Parsed data is missing the 'sourcePdfPath'. Cannot proceed.")
        return False

    # Check if manual already exists
    cursor.execute("SELECT manual_id FROM manuals WHERE source_path = ?", (source_path,))
    existing = cursor.fetchone()
    if existing:
        print(f"Manual with source path '{source_path}' already exists (ID: {existing[0]}). Skipping insertion.")
        return False # Indicate skipped

    try:
        # Insert into manuals table
        features_json = json.dumps(data.get("features", []))
        special_features_json = json.dumps(data.get("specialFeatures", []))
        cursor.execute("""
            INSERT INTO manuals (title, source_path, features, special_features)
            VALUES (?, ?, ?, ?)
        """, (title, source_path, features_json, special_features_json))
        manual_id = cursor.lastrowid
        print(f"Inserted into manuals table, ID: {manual_id}")

        # Insert tabs and content
        tabs_data = data.get("tabs", [])
        for i, tab in enumerate(tabs_data):
            tab_key = tab.get("id")
            tab_title = tab.get("title")
            tab_type = tab.get("type")
            tab_content = tab.get("content")

            if not all([tab_key, tab_title, tab_type]) or tab_content is None: # Check content exists
                print(f"Warning: Skipping tab due to missing id, title, type, or content: {tab}")
                continue

            cursor.execute("""
                INSERT INTO tabs (manual_id, tab_key, title, tab_order, content_type)
                VALUES (?, ?, ?, ?, ?)
            """, (manual_id, tab_key, tab_title, i, tab_type))
            tab_id = cursor.lastrowid

            # Insert content based on type
            if tab_type == 'list' and isinstance(tab_content, list):
                for j, item_text in enumerate(tab_content):
                    if isinstance(item_text, str): # Basic validation
                         cursor.execute("INSERT INTO tab_content_list (tab_id, item_order, text) VALUES (?, ?, ?)", (tab_id, j, item_text))
                    else:
                         print(f"Warning: Skipping list item in tab '{tab_title}' due to non-string content: {item_text}")
            elif tab_type == 'steps' and isinstance(tab_content, dict):
                warning = tab_content.get("warning")
                note = tab_content.get("note")
                steps = tab_content.get("steps", [])
                if isinstance(steps, list):
                    for j, step_text in enumerate(steps):
                         if isinstance(step_text, str): # Basic validation
                            cursor.execute("""
                                INSERT INTO tab_content_steps (tab_id, step_order, text, warning, note)
                                VALUES (?, ?, ?, ?, ?)
                            """, (tab_id, j, step_text, warning if j == 0 else None, note if j == len(steps) - 1 else None))
                         else:
                             print(f"Warning: Skipping step in tab '{tab_title}' due to non-string content: {step_text}")
                else:
                     print(f"Warning: 'steps' content in tab '{tab_title}' is not a list.")
            elif tab_type == 'text' and isinstance(tab_content, str):
                 cursor.execute("INSERT INTO tab_content_text (tab_id, text) VALUES (?, ?)", (tab_id, tab_content))
            else:
                 print(f"Warning: Skipping content for tab '{tab_title}' due to unexpected type/structure: Type={tab_type}, Content Type={type(tab_content)}")

        conn.commit()
        print(f"Successfully inserted data for manual '{title}' (ID: {manual_id})")
        return True # Indicate success

    except sqlite3.Error as e:
        print(f"Database error during insertion: {e}")
        conn.rollback() # Roll back changes on error
        return False # Indicate failure
    except Exception as e:
        print(f"Unexpected error during insertion: {e}")
        conn.rollback()
        return False

def main():
    input_path = INPUT_MANUAL_PATH
    print(f"Input manual path: {input_path}")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return
    if not os.path.exists(DATABASE_FILE):
         print(f"Error: Database file '{DATABASE_FILE}' not found. Please run setup_database.py first.")
         return

    # Generate structured data using LLM
    parsed_data = parse_manual_with_llm(input_path)

    if parsed_data:
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            insert_manual_data(conn, parsed_data)
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
        finally:
            if conn:
                conn.close()
                print("Database connection closed.")
    else:
        print("Failed to parse manual content into valid structure.")

if __name__ == "__main__":
    main()