from flask import Flask, render_template, request, jsonify
from utils import extract_filters,transcribe
import os
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app = Flask(__name__)

# Load test messages (if needed)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    user_text = request.form['user_text']
    extracted_info = extract_filters(user_text)
    extracted_info["User_Message"] = user_text
    return jsonify(dict(extracted_info))

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Receives uploaded audio file, saves it, and transcribes it."""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file found"}), 400

    audio_file = request.files["audio"]
    file_path = os.path.join(UPLOAD_FOLDER, "recorded_audio.wav")
    audio_file.save(file_path)

    try:
        transcription = transcribe(file_path)
        extracted_info = extract_filters(transcription)
        extracted_info["User_Message"] = transcription
        return jsonify(extracted_info)
    except Exception as e:
        return jsonify({"error": f"Error transcribing audio: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
