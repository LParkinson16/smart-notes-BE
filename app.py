from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv 
import google.generativeai as genai


load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Function to create a DB connection
def get_db_connection():
    dbConn = sqlite3.connect('notes.db')
    dbConn.row_factory = sqlite3.Row
    return dbConn

# Function to create tables
def create_tables():
    dbConn = get_db_connection()
    dbConn.execute('''CREATE TABLE IF NOT EXISTS notes (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT,
                   content TEXT,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )''')

    dbConn.execute('''CREATE TABLE IF NOT EXISTS deleted_ids (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   deleted_id INTEGER NOT NULL
                   )''')

    dbConn.commit()
    dbConn.close()

# Function to get the next available ID
def get_next_available_id():
    dbConn = get_db_connection()
    deleted_id = dbConn.execute('SELECT MIN(deleted_id) FROM deleted_ids').fetchone()[0]

    if deleted_id is not None:
        dbConn.execute('DELETE FROM deleted_ids WHERE deleted_id = ?', (deleted_id,))
        dbConn.commit()
        dbConn.close()
        return deleted_id
    else:
        next_id = dbConn.execute('SELECT MAX(id) FROM notes').fetchone()[0]
        dbConn.close()
        return next_id + 1 if next_id is not None else 1

# Routes
@app.route('/notes', methods=['GET'])
def get_notes():
    dbConn = get_db_connection()
    notes = dbConn.execute('SELECT * FROM notes').fetchall()
    dbConn.close()
    return jsonify([dict(note) for note in notes])

@app.route('/notes', methods=['POST'])
def add_note():
    dbConn = get_db_connection()
    title = request.json.get("title", "UNTITLED NOTE")
    content = request.json.get("content")
    new_id = get_next_available_id()
    dbConn.execute("INSERT INTO notes (id, title, content) VALUES (?,?,?)", (new_id, title, content))
    dbConn.commit()
    dbConn.close()
    return jsonify({"message": "Note added", "id": new_id}), 201

@app.route('/notes/<int:id>', methods=['PUT'])
def update_note(id):
    dbConn = get_db_connection()
    title = request.json.get("title", "UNTITLED NOTE")
    content = request.json.get("content")
    dbConn.execute("UPDATE notes SET content = ?, title = ? WHERE id = ?", (content, title, id))
    dbConn.commit()
    dbConn.close()
    return jsonify({"message": "Note updated"}), 201

@app.route('/notes/<int:id>', methods=['DELETE'])
def delete_note(id):
    dbConn = get_db_connection()
    dbConn.execute("INSERT INTO deleted_ids (deleted_id) VALUES (?)", (id,))
    dbConn.commit()
    dbConn.execute("DELETE FROM notes WHERE id = ?", (id,))
    dbConn.commit()
    dbConn.close()
    return jsonify({"message": "Note deleted"})

@app.route("/notes/summarise", methods=["POST"])
def summariseNote():
    data = request.json
    noteContent = data.get("content")
    if not noteContent:
        return jsonify({"error": "content must be present"}), 400
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(f"Summarize the following note in 2-3 sentences:\n\n{noteContent}")
        return jsonify({"summary": response.text})
    except openai.OpenAIError as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    create_tables()
    port = int(os.environ.get("PORT", 5000)) 
    app.run(debug=True, host="0.0.0.0", port=port)
