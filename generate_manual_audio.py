import json
import os
import re
from google.cloud import texttospeech

# --- Configuration ---
JSON_FILE_PATH = 'technisat-manual/src/bda_en.json'
# Save audio inside the public directory of the React app
OUTPUT_DIR = 'technisat-manual/public/manual_audio'
PROJECT_ID = 'bliss-hack25fra-9531' # Make sure this is correct
# Optional: Customize voice settings
VOICE_LANGUAGE_CODE = 'en-US'
VOICE_NAME = 'en-US-Standard-J' # Example voice, choose one you like: https://cloud.google.com/text-to-speech/docs/voices
AUDIO_ENCODING = texttospeech.AudioEncoding.LINEAR16 # WAV format
# --- End Configuration ---

def load_json(filepath):
    """Loads JSON data from the specified file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return None

def synthesize_speech(text, output_filename):
    """Synthesizes speech from text and saves to a file."""
    try:
        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=VOICE_LANGUAGE_CODE, name=VOICE_NAME
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=AUDIO_ENCODING # WAV
        )

        print(f"Synthesizing audio for: '{text[:60]}...'")
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)

        # Write the response to the output file.
        with open(output_filename, "wb") as out:
            out.write(response.audio_content)
            print(f'Audio content written to file "{output_filename}"')
        return True

    except Exception as e:
        print(f"Error synthesizing speech for '{text[:60]}...': {e}")
        return False

def sanitize_filename(text, max_len=40):
    """Creates a safe filename part from text."""
    # Remove non-alphanumeric characters (except spaces, hyphens, underscores)
    text = re.sub(r'[^\w\s-]', '', text)
    # Replace spaces/hyphens with underscores
    text = re.sub(r'[-\s]+', '_', text).strip('_')
    # Truncate
    return text[:max_len]

def main():
    """Main function to load data, generate audio, and save them."""
    # Initialize client (implicitly uses ADC)
    try:
        # Test client initialization early
         texttospeech.TextToSpeechClient()
         print("Google Cloud Text-to-Speech client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Google Cloud Text-to-Speech client: {e}")
        print("Please ensure credentials (ADC) are configured correctly and the API is enabled.")
        return

    bda_data = load_json(JSON_FILE_PATH)
    if not bda_data:
        return

    # Create base output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
            print(f"Created output directory: {OUTPUT_DIR}")
        except OSError as e:
            print(f"Error creating output directory {OUTPUT_DIR}: {e}")
            return

    # Define sections corresponding to the React app structure
    sections_to_process = [
      {'id': 'sysReq', 'key': 'systemRequirements', 'hasSubSteps': False},
      {'id': 'hwInstall', 'key': 'mediaFocusCardInstallation', 'hasSubSteps': True},
      {'id': 'driverInstall', 'key': 'driverInstallation', 'hasSubSteps': True},
      {'id': 'swInstall', 'key': 'applicationSoftwareInstallation', 'hasSubSteps': True},
      {'id': 'launch', 'key': 'launchingApplicationPrograms', 'hasSubSteps': False, 'isSingleText': True},
    ]

    total_files_generated = 0
    total_files_attempted = 0

    for section in sections_to_process:
        section_id = section['id']
        data_key = section['key']
        content = bda_data.get(data_key)

        if not content:
            print(f"\nWarning: Key '{data_key}' not found in JSON data for section '{section_id}'. Skipping.")
            continue

        print(f"\nProcessing section: {section_id}")

        if section['hasSubSteps'] and isinstance(content, dict) and 'steps' in content:
            # Process sections with multiple steps (like installations)
            steps = content['steps']
            for i, step_text in enumerate(steps):
                total_files_attempted += 1
                # Add step number prefix for clarity in audio
                audio_text = f"Step {i + 1}. {step_text}"
                # Use simple index for filename
                output_filename = os.path.join(OUTPUT_DIR, f"{section_id}_step_{i:02d}.wav")
                if synthesize_speech(audio_text, output_filename):
                    total_files_generated += 1

        elif not section['hasSubSteps'] and isinstance(content, list):
             # Process list-based sections (like system requirements)
             for i, item_text in enumerate(content):
                 total_files_attempted += 1
                 # Use simple index for filename
                 output_filename = os.path.join(OUTPUT_DIR, f"{section_id}_item_{i:02d}.wav")
                 if synthesize_speech(item_text, output_filename):
                     total_files_generated += 1

        elif section.get('isSingleText', False) and isinstance(content, str):
             # Process single text sections (like launch app)
             total_files_attempted += 1
             output_filename = os.path.join(OUTPUT_DIR, f"{section_id}_main.wav")
             if synthesize_speech(content, output_filename):
                 total_files_generated += 1
        else:
            print(f"Warning: Content format for section '{section_id}' not recognized or empty. Skipping.")


    print(f"\nAudio generation process finished. {total_files_generated}/{total_files_attempted} files generated.")

if __name__ == "__main__":
    print("--- Starting Manual Audio Generation Script ---")
    print("Requirements:")
    print("1. Google Cloud SDK configured with Application Default Credentials (run 'gcloud auth application-default login').")
    print("2. Google Cloud Text-to-Speech API enabled for your project.")
    print("3. `google-cloud-texttospeech` library installed (`pip install google-cloud-texttospeech`).")
    print(f"4. '{JSON_FILE_PATH}' present.")
    print(f"5. Correct PROJECT_ID ('{PROJECT_ID}') set in this script.")
    print(f"6. Output will be saved to '{OUTPUT_DIR}'.")
    print("-" * 40)
    main()