import json
import os
import base64
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

# --- Configuration ---
JSON_FILE_PATH = 'technisat-manual/src/bda_en.json'
# Save images inside the public directory of the React app
OUTPUT_DIR = 'technisat-manual/public/manual_images'
PROJECT_ID = 'bliss-hack25fra-9531'
LOCATION = 'europe-central2'
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

def generate_image(prompt, output_filename):
    """Generates an image using Vertex AI Imagen and saves it."""
    enhanced_prompt = f"Technical illustration showing how to: {prompt}"
    print(f"Generating image for enhanced prompt: '{enhanced_prompt[:70]}...'")
    try:
        model = ImageGenerationModel.from_pretrained("imagegeneration@005")
        response = model.generate_images(
            prompt=enhanced_prompt,
            number_of_images=1,
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
        return False

def main():
    """Main function to load data, generate images, and save them."""
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"Error initializing Vertex AI: {e}")
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

    step_sections = {
        "install_card": "mediaFocusCardInstallation",
        "install_driver": "driverInstallation",
        "install_software": "applicationSoftwareInstallation"
    }

    image_counter = 0
    total_steps_overall = 0
    section_step_counts = {}

    # Pre-calculate total steps and steps per section
    for key, section_name in step_sections.items():
         if section_name in bda_data and 'steps' in bda_data[section_name]:
             count = len(bda_data[section_name]['steps'])
             section_step_counts[key] = count
             total_steps_overall += count
         else:
             section_step_counts[key] = 0


    print(f"\nFound {total_steps_overall} steps across {len(step_sections)} sections.")

    # Process each section
    for key, section_name in step_sections.items():
        if section_name in bda_data and 'steps' in bda_data[section_name]:
            steps = bda_data[section_name]['steps']
            print(f"\nProcessing section: {section_name} ({len(steps)} steps)")
            for i, step_text in enumerate(steps):
                image_counter += 1
                # Use simplified, predictable filename structure
                output_filename = os.path.join(OUTPUT_DIR, f"{key}_step_{i+1:02d}.png")

                # Generate the image
                success = generate_image(step_text, output_filename)
                if success:
                    print(f"Progress: {image_counter}/{total_steps_overall}")
                else:
                    print(f"Skipping image for step {i+1} in section {key} due to generation error.")
        else:
            print(f"\nWarning: Section '{section_name}' or its 'steps' not found in {JSON_FILE_PATH}.")

    print("\nImage generation process finished.")

if __name__ == "__main__":
    print("--- Starting Manual Image Generation Script ---")
    print("Requirements:")
    print("1. Google Cloud SDK configured with Application Default Credentials (run 'gcloud auth application-default login').")
    print("2. `google-cloud-aiplatform` library installed (`pip install google-cloud-aiplatform`).")
    print(f"3. '{JSON_FILE_PATH}' present.")
    print(f"4. Correct PROJECT_ID ('{PROJECT_ID}') and LOCATION ('{LOCATION}') set in this script.")
    print(f"5. Output will be saved to '{OUTPUT_DIR}'.")
    print("-" * 40)
    main()