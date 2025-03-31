import argparse # Re-import argparse
import json
import os
import mimetypes
import sqlite3
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content

# --- Configuration ---
PROJECT_ID = "bliss-hack25fra-9531"
LOCATION = "europe-central2"
# Use a more powerful Gemini model
MODEL_NAME = "gemini-2.0-flash"
DATABASE_FILE = 'manuals.db'
# --- End Configuration ---

# --- Target JSON Schema Description (for prompting the LLM) ---
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
    }
    // ... only tabs for the core topics mentioned ...
  ]
}

// StepContent object structure (used when type='steps'):
// {
//   "warning": "string (Optional: Warning for this section - translated to English)",
//   "steps": [ { "id": "string", "text": "string (List of steps - translated to English)" } ],
//   "note": "string (Optional: Note for this section - translated to English)"
// }
// ListItem object structure (used when type='list'):
// { "id": "string", "text": "string (List item - translated to English)" }
""" # Updated schema detail in comment

def extract_text_from_txt(txt_path):
    """Extracts text content from a TXT file."""
    print(f"Reading text file: {txt_path}")
    try:
        with open(txt_path, 'r', encoding='utf-8') as f: text = f.read()
        print(f"Read {len(text)} characters.")
        return text
    except Exception as e: print(f"Error reading text file {txt_path}: {e}"); return None

def parse_manual_with_llm(manual_file_path, project_id, location, model_name):
    """Uses Vertex AI Gemini to parse a manual file (PDF/TXT) into the new JSON schema and translate to English."""
    print(f"Processing file for LLM parsing: {manual_file_path}")
    raw_response_text = ""
    response = None
    try:
        with open(manual_file_path, "rb") as f: file_bytes = f.read()
        mime_type, _ = mimetypes.guess_type(manual_file_path)
        if not mime_type:
            if manual_file_path.lower().endswith(".pdf"): mime_type = "application/pdf"
            elif manual_file_path.lower().endswith(".txt"): mime_type = "text/plain"
            else: mime_type = "text/plain"; print(f"Warning: Could not determine MIME type for {manual_file_path}. Assuming text/plain.")
        print(f"Detected MIME type: {mime_type}")

        prompt_header = f"""
Analyze the provided technical manual content (either text or PDF). Structure its content into a JSON object adhering to the NEW schema described below.
**IMPORTANT: Translate ALL extracted text content into English.**
Add the original PDF path "{manual_file_path}" to the `sourcePdfPath` field.

Target JSON Schema Description:
{NEW_TARGET_SCHEMA_DESCRIPTION}

Detailed Instructions:
1. Identify the main title (English).
2. Extract top-level `features` and `specialFeatures` lists (English).
3. **Identify content for ONLY these core topics:** System Requirements, Hardware Installation/Setup, Driver Installation, Software Installation/Application Setup, Usage/Operation.
4. **Create a maximum of 5 tab objects** in the `tabs` array for these core topics. Group related content logically. Do NOT create tabs for other sections.
5. For each core topic tab, use the specific `id` and `title` (e.g., `id: 'systemRequirements'`, `title: 'System Requirements'`). Determine `type` ('list', 'steps', 'text') and populate `content` (translated English). For 'steps', the `steps` array within content should contain objects like `{{"id": "hardwareInstallation_step_0", "text": "Step text..."}}`. Generate the step `id` using the tab `id` and the 0-based index. For 'list', the `content` array should contain objects like `{{"id": "systemRequirements_item_0", "text": "Item text..."}}`.
6. Omit tabs for missing core topics.
7. Ensure the final output is ONLY the valid JSON object.
"""
        # The API expects a list containing Part objects
        prompt_parts: list[Part] = []

        if mime_type == "text/plain":
            manual_content = extract_text_from_txt(manual_file_path)
            if not manual_content: return None
            full_prompt_text = (prompt_header + "\nManual Text:\n--- START TEXT ---\n" + manual_content[:100000] + "\n--- END TEXT ---\n\nGenerate the JSON object:")
            prompt_parts.append(Part.from_text(full_prompt_text)) # Create Part from text
        elif mime_type == "application/pdf":
            file_part = Part.from_data(data=file_bytes, mime_type=mime_type)
            instruction_part_text = (prompt_header + "\nGenerate the JSON object based *only* on the provided PDF file:")
            prompt_parts = [file_part, Part.from_text(instruction_part_text)] # List of Part objects
        else: print(f"Error: Unsupported MIME type '{mime_type}'."); return None

        print(f"Sending request to Gemini model ({model_name})...")
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel(model_name)
        generation_config = {"temperature": 0.1, "top_p": 0.95, "top_k": 40, "max_output_tokens": 8192, "response_mime_type": "application/json"}

        # Pass the list of Part objects
        response = model.generate_content(contents=prompt_parts, generation_config=generation_config) # Pass list of Parts

        print("Received response from model.")
        if not response.candidates or not response.candidates[0].content.parts:
             print("Error: Model response did not contain expected content parts."); # Log details if needed
             return None
        raw_response_text = response.candidates[0].content.parts[0].text
        json_data = json.loads(raw_response_text)
        print("Successfully parsed response as JSON.")
        if "sourcePdfPath" not in json_data: json_data["sourcePdfPath"] = manual_file_path
        return json_data

    except FileNotFoundError: print(f"Error: Input file not found at {manual_file_path}"); return None
    except json.JSONDecodeError as json_err: print(f"Error: Failed to parse LLM response as JSON: {json_err}\n--- Raw Response Text ---\n{raw_response_text if 'raw_response_text' in locals() else 'N/A'}\n--- End Raw Response Text ---"); return None
    except Exception as e: print(f"Error during processing or Vertex AI interaction: {e}"); return None


def insert_manual_data(conn, data):
    """Inserts parsed manual data into the SQLite database. Returns manual_id if successful or existing, None on error."""
    cursor = conn.cursor()
    source_path = data.get("sourcePdfPath")
    title = data.get("title", "Untitled Manual")
    manual_id = None

    if not source_path: print("Error: Parsed data missing 'sourcePdfPath'."); return None

    cursor.execute("SELECT manual_id FROM manuals WHERE source_path = ?", (source_path,))
    existing = cursor.fetchone()
    if existing: print(f"Manual '{source_path}' already exists (ID: {existing[0]}). Skipping insertion."); return existing[0]

    try:
        features_json = json.dumps(data.get("features", []))
        special_features_json = json.dumps(data.get("specialFeatures", []))
        cursor.execute("INSERT INTO manuals (title, source_path, features, special_features) VALUES (?, ?, ?, ?)",
                       (title, source_path, features_json, special_features_json))
        manual_id = cursor.lastrowid
        print(f"Inserted into manuals table, ID: {manual_id}")

        tabs_data = data.get("tabs", [])
        for i, tab in enumerate(tabs_data):
            tab_key, tab_title, tab_type, tab_content = tab.get("id"), tab.get("title"), tab.get("type"), tab.get("content")
            if not all([tab_key, tab_title, tab_type]) or tab_content is None: print(f"Warning: Skipping tab due to missing data: {tab}"); continue

            cursor.execute("INSERT INTO tabs (manual_id, tab_key, title, tab_order, content_type) VALUES (?, ?, ?, ?, ?)",
                           (manual_id, tab_key, tab_title, i, tab_type))
            tab_id = cursor.lastrowid

            if tab_type == 'list' and isinstance(tab_content, list):
                for j, item in enumerate(tab_content): # Expecting objects {id, text}
                    item_id_from_json = item.get("id") # We don't store this specific ID in DB
                    item_text = item.get("text")
                    if isinstance(item_text, str): cursor.execute("INSERT INTO tab_content_list (tab_id, item_order, text) VALUES (?, ?, ?)", (tab_id, j, item_text))
                    else: print(f"Warning: Skipping list item in tab '{tab_title}' due to missing/invalid data: {item}")
            elif tab_type == 'steps' and isinstance(tab_content, dict):
                warning, note, steps = tab_content.get("warning"), tab_content.get("note"), tab_content.get("steps", [])
                if isinstance(steps, list):
                    for j, step in enumerate(steps): # Expecting objects {id, text}
                        step_id_from_json = step.get("id") # We don't store this specific ID in DB
                        step_text = step.get("text")
                        if isinstance(step_text, str): cursor.execute("INSERT INTO tab_content_steps (tab_id, step_order, text, warning, note) VALUES (?, ?, ?, ?, ?)", (tab_id, j, step_text, warning if j == 0 else None, note if j == len(steps) - 1 else None))
                        else: print(f"Warning: Skipping step in tab '{tab_title}' due to missing/invalid data: {step}")
                else: print(f"Warning: 'steps' content in tab '{tab_title}' is not a list.")
            elif tab_type == 'text' and isinstance(tab_content, str):
                 cursor.execute("INSERT INTO tab_content_text (tab_id, text) VALUES (?, ?)", (tab_id, tab_content))
            else: print(f"Warning: Skipping content for tab '{tab_title}' due to unexpected type/structure: Type={tab_type}, Content Type={type(tab_content)}")

        conn.commit()
        print(f"Successfully inserted data for manual '{title}' (ID: {manual_id})")
        return manual_id # Return the new ID

    except sqlite3.Error as e: print(f"Database error during insertion: {e}"); conn.rollback(); return None
    except Exception as e: print(f"Unexpected error during insertion: {e}"); conn.rollback(); return None

def process_single_manual(input_path, db_file):
    """Processes a single manual file and inserts data into the database. Returns the manual_id."""
    print("-" * 40)
    print(f"Processing Manual: {input_path}")

    if not os.path.exists(input_path): print(f"Error: Input file not found at {input_path}"); return None
    if not os.path.exists(db_file): print(f"Error: Database file '{db_file}' not found."); return None

    parsed_data = parse_manual_with_llm(input_path, PROJECT_ID, LOCATION, MODEL_NAME)

    manual_id = None
    if parsed_data:
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            manual_id = insert_manual_data(conn, parsed_data)
        except sqlite3.Error as e: print(f"Database connection error: {e}")
        finally:
            if conn: conn.close(); print("Database connection closed.")
    else: print(f"Failed to parse manual content into valid structure for {input_path}.")
    return manual_id

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert a single manual file (PDF/TXT) into structured data in the SQLite DB.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input manual file (PDF or TXT).")
    # Removed output path argument as it goes to DB
    args = parser.parse_args()

    process_single_manual(args.input, DATABASE_FILE)