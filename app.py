from flask import Flask, render_template, request, jsonify
from utils import extract_filters, record_and_transcribe, fetch_history, generate_elastic_query, create_advanced_search_url, transcribe
from data_analysis import  analyze_transactions_with_openai
import os


app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    user_text = request.form['user_text']
    extracted_info = extract_filters(user_text)
    extracted_info["User_Message"] = user_text
    # Generate query & fetch history
    # payload = generate_elastic_query(extracted_info)
    # history = fetch_history(payload)


    # Perform AI Analysis
    # analysis_results = analyze_transactions_with_openai(history)
    android_url = "lydia://advanced_search"
    ios_url = "com.lydia-app.preprod://advanced_search"

    query_url_android = create_advanced_search_url(android_url, extracted_info)
    query_url_ios = create_advanced_search_url(ios_url, extracted_info)

    # Return results with AI insights
    return jsonify({
        "clarification_needed": extracted_info.get("clarification_needed", []),
        "clarification_options": extracted_info.get("clarification_options", []),
        # "items": history.get("items", []),
        # "analysis": analysis_results,  # Pass AI-generated financial insights
        "filters": {
            "start_date": extracted_info.get("start_date", ""),
            "end_date": extracted_info.get("end_date", ""),
            "amount": extracted_info.get("amount", ""),
            "movement_type": extracted_info.get("movement_type", ""),
            "pfm_category": extracted_info.get("pfm-category", ""),
            "movement_scope": extracted_info.get("movement_scope", ""),
            "keywords": extracted_info.get("keywords", "")
        },
        "query_url_android": query_url_android,
        "query_url_ios": query_url_ios
    })


@app.route('/process_audio', methods=['POST'])
def process_audio():
    user_text = record_and_transcribe()
    if user_text:
        extracted_info = extract_filters(user_text)
        extracted_info["User_Message"] = user_text
        # payload = generate_elastic_query(extracted_info)
        # history = fetch_history(payload)
        # analysis_results = analyze_transactions_with_openai(history)
        android_url = "lydia://advanced_search"
        ios_url = "com.lydia-app.preprod://advanced_search"

        query_url_android = create_advanced_search_url(android_url, extracted_info)
        query_url_ios = create_advanced_search_url(ios_url, extracted_info)
      
        # Return results with AI insights
        return jsonify({
            "clarification_needed": extracted_info.get("clarification_needed", []),
            "clarification_options": extracted_info.get("clarification_options", []),
            # "items": history.get("items", []),
            # "analysis": analysis_results,  # Pass AI-generated financial insights
            "filters": {
                "start_date": extracted_info.get("start_date", ""),
                "end_date": extracted_info.get("end_date", ""),
                "amount": extracted_info.get("amount", ""),
                "movement_type": extracted_info.get("movement_type", ""),
                "pfm_category": extracted_info.get("pfm-category", ""),
                "movement_scope": extracted_info.get("movement_scope", ""),
                "keywords": extracted_info.get("keywords", "")
            },
        "query_url_android": query_url_android,
        "query_url_ios": query_url_ios
        })
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
        android_url = "lydia://advanced_search"
        ios_url = "com.lydia-app.preprod://advanced_search"

        query_url_android = create_advanced_search_url(android_url, extracted_info)
        query_url_ios = create_advanced_search_url(ios_url, extracted_info)
      
        # Return results with AI insights
        return jsonify({
            "clarification_needed": extracted_info.get("clarification_needed", []),
            "clarification_options": extracted_info.get("clarification_options", []),
            # "items": history.get("items", []),
            # "analysis": analysis_results,  # Pass AI-generated financial insights
            "filters": {
                "start_date": extracted_info.get("start_date", ""),
                "end_date": extracted_info.get("end_date", ""),
                "amount": extracted_info.get("amount", ""),
                "movement_type": extracted_info.get("movement_type", ""),
                "pfm_category": extracted_info.get("pfm-category", ""),
                "movement_scope": extracted_info.get("movement_scope", ""),
                "keywords": extracted_info.get("keywords", "")
            },
        "query_url_android": query_url_android,
        "query_url_ios": query_url_ios
        })
    except Exception as e:
        return jsonify({"error": f"Error transcribing audio: {e}"}), 500
if __name__ == '__main__':
    app.run(debug=True)
