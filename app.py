from flask import Flask, render_template, request, jsonify
from utils import extract_filters, record_and_transcribe, fetch_history, generate_elastic_query
from data_analysis import  analyze_transactions_with_openai


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    user_text = request.form['user_text']
    extracted_info = extract_filters(user_text)
    extracted_info["User_Message"] = user_text
    # Generate query & fetch history
    payload = generate_elastic_query(extracted_info)
    history = fetch_history(payload)


    # Perform AI Analysis
    analysis_results = analyze_transactions_with_openai(history)
    print("Query:", payload)

    # Return results with AI insights
    return jsonify({
        "clarification_needed": extracted_info.get("clarification_needed", []),
        "clarification_options": extracted_info.get("clarification_options", []),
        "items": history.get("items", []),
        "analysis": analysis_results,  # Pass AI-generated financial insights
        "filters": {
            "start_date": extracted_info.get("start_date", ""),
            "end_date": extracted_info.get("end_date", ""),
            "amount": extracted_info.get("amount", ""),
            "category": extracted_info.get("category", ""),
            "pfm_category": extracted_info.get("pfm-category", ""),
            "transaction_type": extracted_info.get("transaction_type", ""),
            "keywords": extracted_info.get("keywords", "")
        }
    })



@app.route('/process_audio', methods=['POST'])
def process_audio():
    user_text = record_and_transcribe()
    if user_text:
        extracted_info = extract_filters(user_text)
        extracted_info["User_Message"] = user_text
        print(extracted_info)
        payload = generate_elastic_query(extracted_info)
        history = fetch_history(payload)

        # Perform AI Analysis
        analysis_results = analyze_transactions_with_openai(history)
        print("Query:", payload)

        # Return results with AI insights
        return jsonify({
            "clarification_needed": extracted_info.get("clarification_needed", []),
            "clarification_options": extracted_info.get("clarification_options", []),
            "items": history.get("items", []),
            "analysis": analysis_results,  # Pass AI-generated financial insights
            "filters": {
                "start_date": extracted_info.get("start_date", ""),
                "end_date": extracted_info.get("end_date", ""),
                "amount": extracted_info.get("amount", ""),
                "category": extracted_info.get("category", ""),
                "pfm_category": extracted_info.get("pfm-category", ""),
                "transaction_type": extracted_info.get("transaction_type", ""),
                "keywords": extracted_info.get("keywords", "")
            }
        })

if __name__ == '__main__':
    app.run(debug=True)
