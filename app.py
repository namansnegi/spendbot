from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime
from utils import extract_filters, record_and_transcribe
import os
from collections import OrderedDict


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
    column_order = ["User_Message", "time_frame", "start_date", "end_date", "category", "sub_category", "transaction_type","beneficiares","math_operation", "amount"]
    extracted_info_ordered = OrderedDict((col, extracted_info.get(col, None)) for col in column_order)

    return jsonify(dict(extracted_info_ordered))
@app.route('/process_audio', methods=['POST'])
def process_audio():
    column_order = ["User_Message", "time_frame", "start_date", "end_date", "category", "sub_category", "transaction_type","beneficiares","math_operation", "amount"]
    user_text = record_and_transcribe()
    if user_text:
        extracted_info = extract_filters(user_text)
        extracted_info["User_Message"] = user_text
        extracted_info_ordered = {col: extracted_info.get(col, None) for col in column_order}
        return jsonify(extracted_info_ordered)
    return jsonify({"error": "Could not transcribe audio"})

if __name__ == '__main__':
    app.run(debug=True)
