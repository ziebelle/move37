import sqlite3
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from flask import Flask, jsonify, abort, request # Added request
from flask_cors import CORS # To handle Cross-Origin Resource Sharing

app = Flask(__name__)
CORS(app) # Allow requests from your React frontend development server

DATABASE_FILE = 'manuals.db' # Path relative to project root
KNOWLEDGE_JSON_FILE = 'all_manuals_knowledge.json' # Path relative to project root

# --- Vertex AI Config ---
PROJECT_ID = "bliss-hack25fra-9531"
LOCATION = "europe-central2"
MODEL_NAME = "gemini-2.0-flash" # Or your preferred model for QA
# --- End Vertex AI Config ---


def get_db_connection():
    """Connects to the specific database."""
    if not os.path.exists(DATABASE_FILE):
        print(f"FATAL ERROR: Database file '{DATABASE_FILE}' not found.")
        return None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/api/manuals', methods=['GET'])
def get_manuals_list():
    """Returns a list of available manuals."""
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500
    try:
        manuals = conn.execute('SELECT manual_id, title, source_path FROM manuals ORDER BY title').fetchall()
        conn.close()
        manuals_list = [dict(row) for row in manuals]
        return jsonify(manuals_list)
    except sqlite3.Error as e:
        print(f"Error fetching manuals list: {e}")
        if conn: conn.close()
        return jsonify({"error": "Failed to fetch manuals list"}), 500


@app.route('/api/manuals/<int:manual_id>', methods=['GET'])
def get_manual_details(manual_id):
    """Returns the structured data for a specific manual."""
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500
    try:
        manual_meta = conn.execute('SELECT * FROM manuals WHERE manual_id = ?', (manual_id,)).fetchone()
        if manual_meta is None: conn.close(); abort(404, description="Manual not found")

        output_data = dict(manual_meta)
        try: output_data['features'] = json.loads(output_data.get('features', '[]') or '[]')
        except (json.JSONDecodeError, TypeError): output_data['features'] = []
        try: output_data['special_features'] = json.loads(output_data.get('special_features', '[]') or '[]')
        except (json.JSONDecodeError, TypeError): output_data['special_features'] = []

        tabs = conn.execute("SELECT tab_id, tab_key, title, tab_order, content_type FROM tabs WHERE manual_id = ? ORDER BY tab_order", (manual_id,)).fetchall()
        output_data['tabs'] = []
        for tab_row in tabs:
            tab_data = dict(tab_row); tab_id = tab_data['tab_id']; content_type = tab_data['content_type']; tab_key = tab_data['tab_key']
            if content_type == 'list':
                items = conn.execute("SELECT item_order, text FROM tab_content_list WHERE tab_id = ? ORDER BY item_order", (tab_id,)).fetchall()
                tab_data['content'] = [{"id": f"{tab_key}_item_{item['item_order']:02d}", "text": item['text']} for item in items]
            elif content_type == 'steps':
                steps_raw = conn.execute("SELECT step_order, text, warning, note FROM tab_content_steps WHERE tab_id = ? ORDER BY step_order", (tab_id,)).fetchall()
                steps_list = [{"id": f"{tab_key}_step_{step['step_order']:02d}", "text": step['text']} for step in steps_raw]
                warning = steps_raw[0]['warning'] if steps_raw and steps_raw[0]['warning'] else None
                note = steps_raw[-1]['note'] if steps_raw and steps_raw[-1]['note'] else None
                steps_content = {"steps": steps_list}
                if warning: steps_content["warning"] = warning
                if note: steps_content["note"] = note
                tab_data['content'] = steps_content
            elif content_type == 'text':
                text_content = conn.execute("SELECT text FROM tab_content_text WHERE tab_id = ?", (tab_id,)).fetchone()
                tab_data['content'] = text_content['text'] if text_content else ""
            output_data['tabs'].append(tab_data)
        conn.close()
        return jsonify(output_data)
    except sqlite3.Error as e:
        print(f"Error fetching details for manual {manual_id}: {e}")
        if conn: conn.close()
        return jsonify({"error": f"Failed to fetch details for manual {manual_id}"}), 500 # Added return
    except Exception as e:
         print(f"Unexpected error for manual {manual_id}: {e}")
         if conn: conn.close()
         return jsonify({"error": "An unexpected error occurred"}), 500 # Added return

# --- New QA Endpoint ---
@app.route('/api/qa', methods=['POST'])
def handle_qa():
    """Handles QA requests using the full knowledge base."""
    if not request.is_json: return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    user_question = data.get('question')
    if not user_question: return jsonify({"error": "Missing 'question' in request body"}), 400

    # 1. Load the knowledge base JSON
    try:
        if not os.path.exists(KNOWLEDGE_JSON_FILE): return jsonify({"error": f"Knowledge base file '{KNOWLEDGE_JSON_FILE}' not found. Run export script."}), 500
        with open(KNOWLEDGE_JSON_FILE, 'r', encoding='utf-8') as f: knowledge_base = json.load(f)
        knowledge_text = json.dumps(knowledge_base) # Use compact JSON for prompt
    except Exception as e: print(f"Error loading knowledge base {KNOWLEDGE_JSON_FILE}: {e}"); return jsonify({"error": "Failed to load knowledge base"}), 500

    # 2. Prepare prompt for LLM
    max_knowledge_chars = 150000 # Example limit
    if len(knowledge_text) > max_knowledge_chars:
        print(f"Warning: Knowledge base text truncated to {max_knowledge_chars} chars for prompt.")
        knowledge_text = knowledge_text[:max_knowledge_chars] # Simple truncation

    combined_prompt = f"""
Context: You are a helpful assistant knowledgeable about the technical manuals provided below in JSON format. Answer the user's question based *only* on the information contained within this JSON data. If the answer cannot be found in the provided data, say "I cannot find information about that in the provided manuals."

Provided Manuals Data (JSON):
```json
{knowledge_text}
```

User Question: {user_question}

Answer:
"""

    # 3. Call Vertex AI Gemini
    try:
        print(f"Sending QA request to Gemini model ({MODEL_NAME})...")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_NAME)
        # Send simple text prompt
        response = model.generate_content(combined_prompt)

        answer = response.text.strip()
        print("Received QA answer from model.")
        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Error during QA processing or Vertex AI interaction: {e}")
        return jsonify({"error": "Failed to get answer from AI model"}), 500


if __name__ == '__main__':
    if not os.path.exists(DATABASE_FILE):
        print(f"ERROR: Database file '{DATABASE_FILE}' not found.")
        print("Please run 'python setup_database.py' first.")
    elif not os.path.exists(KNOWLEDGE_JSON_FILE):
         print(f"WARNING: Knowledge base file '{KNOWLEDGE_JSON_FILE}' not found.")
         print("QA endpoint will fail until 'python export_db_to_json.py' is run.")
         print(f"Starting Flask server anyway, serving data from {DATABASE_FILE}")
         app.run(host='0.0.0.0', port=5001, debug=True) # Run even if knowledge base missing
    else:
        print(f"Starting Flask server, serving data from {DATABASE_FILE}")
        print(f"Knowledge base loaded from: {KNOWLEDGE_JSON_FILE}")
        app.run(host='0.0.0.0', port=5001, debug=True)