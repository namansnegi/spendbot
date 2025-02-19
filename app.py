from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime
from utils import extract_filters, record_and_transcribe,transcribe
import os
from collections import OrderedDict
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
    print(extracted_info)
    column_order = ["User_Message", "time_frame", "start_date", "end_date", "category", "sub_category", "transaction_type","beneficiaries","math_operation", "amount"]
    extracted_info_ordered = OrderedDict((col, extracted_info.get(col, None)) for col in column_order)

    return jsonify(dict(extracted_info))
@app.route('/process_audio', methods=['POST'])
def process_audio():
    column_order = ["User_Message", "time_frame", "start_date", "end_date", "category", "sub_category", "transaction_type","beneficiaries","math_operation", "amount"]
    user_text = record_and_transcribe()
    if user_text:
        extracted_info = extract_filters(user_text)
        extracted_info["User_Message"] = user_text
        extracted_info_ordered = {col: extracted_info.get(col, None) for col in column_order}
        return jsonify(extracted_info)
    return jsonify({"error": "Could not transcribe audio"})

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

        column_order = ["User_Message", "time_frame", "start_date", "end_date", 
                        "category", "sub_category", "transaction_type", "beneficiares",
                        "math_operation", "amount"]
        extracted_info_ordered = {col: extracted_info.get(col, None) for col in column_order}
        
        return jsonify(extracted_info)
    except Exception as e:
        return jsonify({"error": f"Error transcribing audio: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
