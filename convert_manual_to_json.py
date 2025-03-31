import argparse
import json
import os
import mimetypes # To guess MIME type
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
# Removed pypdf import

# --- Configuration ---
PROJECT_ID = "bliss-hack25fra-9531"
LOCATION = "europe-central2"
# Use a more powerful Gemini model
MODEL_NAME = "gemini-2.0-flash"

# --- File Paths (Modify these) ---
INPUT_MANUAL_PATH = "ProduktAssets/TechniSat/BDA/BDA_AUDIOMASTER_SL900.pdf" # Example path
OUTPUT_JSON_PATH = "audiomaster_sl900_manual_en_tabs_constrained.json" # Updated output name
# --- End Configuration ---

# --- Target JSON Schema Description (for prompting the LLM) ---
# Describes the NEW desired *structure*.
NEW_TARGET_SCHEMA_DESCRIPTION = """
{
  "title": "string (Main title of the manual - translated to English)",
  "features": ["string (List of key product features - translated to English, if present)"],
  "specialFeatures": ["string (List of special characteristics or highlights - translated to English, if present)"],
  "tabs": [
    // EXPECTING ONLY 3-5 TABS MAXIMUM, corresponding to the core topics below
    {
      "id": "string (Specific ID: 'systemRequirements', 'hardwareInstallation', 'driverInstallation', 'softwareInstallation', or 'usage')",
      "title": "string (Specific Title: 'System Requirements', 'Hardware Installation', 'Driver Installation', 'Software Installation', or 'Usage' - translated to English)",
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

# Removed extract_text_from_pdf function

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

def generate_json_from_manual_file(manual_file_path):
    """Uses Vertex AI Gemini to parse a manual file (PDF/TXT) into the new JSON schema and translate to English."""
    print(f"Processing file: {manual_file_path}")
    raw_response_text = "" # Initialize

    try:
        # Read file bytes
        with open(manual_file_path, "rb") as f:
            file_bytes = f.read()

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(manual_file_path)
        if not mime_type:
            if manual_file_path.lower().endswith(".pdf"):
                mime_type = "application/pdf"
            elif manual_file_path.lower().endswith(".txt"):
                 mime_type = "text/plain"
            else:
                 print(f"Warning: Could not determine MIME type for {manual_file_path}. Assuming text/plain.")
                 mime_type = "text/plain"

        print(f"Detected MIME type: {mime_type}")

        # --- Base Prompt Instructions ---
        # Updated instructions for specific tabs
        prompt_header = f"""
        Analyze the provided technical manual content (either text or PDF). Structure its content into a JSON object adhering to the NEW schema described below.
        **IMPORTANT: Translate ALL extracted text content (titles, features, steps, notes, section text, etc.) into English before placing it into the JSON structure.**

        Target JSON Schema Description:
        {NEW_TARGET_SCHEMA_DESCRIPTION}

        Detailed Instructions:
        1. Identify the main title. Translate it to English for the top-level "title" value.
        2. Extract top-level list sections like "Features" and "Special Features". Use the keys `features` and `specialFeatures`. Translate each list item to English. Omit keys if the section is absent.
        3. **Identify content specifically related to the following core topics ONLY:**
            - System Requirements
            - Hardware Installation (including any physical setup)
            - Driver Installation (software drivers for the hardware)
            - Software Installation (application software)
            - Usage / Launching the Application (how to start using it after setup)
        4. **Create a maximum of 5 tab objects** in the top-level "tabs" array, one for each core topic found above. **Do NOT create tabs for other sections** like safety, troubleshooting, technical data, etc.
        5. For each of the core topics found, create ONE corresponding tab object:
            - Use the specific `id` and `title` mentioned in the schema description (e.g., `id: 'systemRequirements'`, `title: 'System Requirements'`).
            - Determine the `type` ('list', 'steps', or 'text') based on the primary content for that topic.
            - Populate the `content` field according to the `type`, gathering all relevant information for that core topic (even if spread across multiple sub-sections in the original manual) and translating it to English. For 'steps', combine all related installation steps under the appropriate tab (e.g., all hardware steps under `hardwareInstallation`).
        6. If content for a core topic (e.g., Driver Installation) is not found, simply omit that tab object from the `tabs` array.
        7. Ensure the final output is ONLY the valid JSON object, without any introductory text, explanations, or markdown formatting like ```json ... ```. Be careful with escaping characters within JSON strings.
        """

        # --- Construct prompt_parts based on file type ---
        prompt_parts: list[str | Part] = [] # Initialize list for type hinting

        if mime_type == "text/plain":
            manual_content = extract_text_from_txt(manual_file_path)
            if not manual_content:
                return None
            prompt_parts = [
                prompt_header, # Use the defined header
                "\nManual Text:\n--- START TEXT ---\n",
                manual_content[:80000], # Limit text size if needed
                "\n--- END TEXT ---\n\nGenerate the translated English JSON object according to the NEW schema and specific tab instructions now:"
            ]
        elif mime_type == "application/pdf":
            file_part = Part.from_data(data=file_bytes, mime_type=mime_type)
            prompt_parts = [
                 file_part, # Send the file itself first
                 prompt_header, # Then the instructions
                 "\nGenerate the translated English JSON object based *only* on the provided PDF file, following the NEW schema and specific tab instructions:"
             ]
        else:
            print(f"Error: Unsupported MIME type '{mime_type}' for processing.")
            return None


        print(f"Sending request to Gemini model ({MODEL_NAME})...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)

        # Configure generation parameters
        generation_config = {
            "temperature": 0.1, # Even lower temperature for stricter adherence
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json", # Request JSON output directly
        }

        # Ensure prompt_parts is correctly typed for the API call
        response = model.generate_content(
            contents=prompt_parts, # Explicitly use 'contents' parameter
            generation_config=generation_config
            )

        # Attempt to parse the response (should be JSON directly now)
        print("Received response from model.")
        if not response.candidates or not response.candidates[0].content.parts:
             print("Error: Model response did not contain expected content parts.")
             # Log safety ratings if available
             if response.prompt_feedback:
                 print(f"Prompt Feedback: {response.prompt_feedback}")
             if response.candidates and response.candidates[0].finish_reason:
                 print(f"Finish Reason: {response.candidates[0].finish_reason}")
             if response.candidates and response.candidates[0].safety_ratings:
                 print(f"Safety Ratings: {response.candidates[0].safety_ratings}")
             return None

        raw_response_text = response.candidates[0].content.parts[0].text
        json_data = json.loads(raw_response_text)
        print("Successfully parsed response as JSON.")
        return json_data

    except FileNotFoundError:
        print(f"Error: Input file not found at {manual_file_path}")
        return None
    except json.JSONDecodeError as json_err:
        print(f"Error: Failed to parse LLM response as JSON: {json_err}")
        print("--- Raw Response Text ---")
        print(raw_response_text if 'raw_response_text' in locals() else "Raw response text not available")
        print("--- End Raw Response Text ---")
        return None
    except Exception as e:
        print(f"Error during processing or Vertex AI interaction: {e}")
        # Log response details on general errors too
        if 'response' in locals():
             print(f"Full Response on Error: {response}")
        if 'raw_response_text' in locals() and raw_response_text:
           print("--- Raw Response Text ---")
           print(raw_response_text)
           print("--- End Raw Response Text ---")
        return None

def main():
    # Use paths defined in the configuration section
    input_path = INPUT_MANUAL_PATH
    output_path = OUTPUT_JSON_PATH

    print(f"Input manual path: {input_path}")
    print(f"Output JSON path: {output_path}")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}")
        return

    # Generate JSON using LLM, passing the file path
    generated_json = generate_json_from_manual_file(input_path)

    if generated_json:
        # Save the JSON to the output file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(generated_json, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved structured and translated JSON to {output_path}")
        except Exception as e:
            print(f"Error writing JSON to file {output_path}: {e}")
    else:
        print("Failed to generate valid JSON structure.")

if __name__ == "__main__":
    main()