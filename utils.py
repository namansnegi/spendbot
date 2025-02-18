import openai
import speech_recognition as sr
import json
from datetime import datetime
from schema import reponse_format
import os

# Get API key from Heroku environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

if openai.api_key is None:
    raise ValueError("❌ OPENAI_API_KEY is not set. Make sure to add it to Heroku.")


AVAILABLE_CATEGORIES = [
    "Rechargement par carte", "Compte courant rémunéré", "Virements", "Paiements",
    "Prélèvements", "Investissement Sumeria", "Prêts Sumeria", "Livret d'épargne",
    "Gains Sumeria", "Dons", "Cartes cadeaux", "Retraits distributeurs", "Frais"
]
TRANSACTION_TYPES = ["Entrées d'argent", "Sorties d'argent", "Inter-comptes"]

# Function to extract filters using OpenAI
def extract_filters(user_input):
    """
    Extracts relevant filters from user input using OpenAI.
    """
        # Get today's date dynamically
    today = datetime.today().strftime("%Y-%m-%d")

    prompt = f"""
    You are an AI assistant that extracts structured information from user queries 
    to autofill a transaction filter form.

    Today's date is **{today}**. Use this date as a reference to calculate time frames correctly.


    Given the following available transaction categories:
    {AVAILABLE_CATEGORIES}

    And the following transaction types:
    {TRANSACTION_TYPES}

    Your task is to extract:
    - `time_frame`: Identify the relevant time period (e.g., "last month", "this year", "this week").
    - `start_date`: Convert the time frame into YYYY-MM-DD format.
    - `end_date`: Convert the time frame into YYYY-MM-DD format.
    - `category`: Choose the **most relevant** category from the given list.
    - `sub_category`: Extract a **detailed sub-category** that better explains the user intent as in what exact type of transactions is the user interested in.
    - `transaction_type`: Choose the **most relevant** transaction type from the given list.
    - `beneficiares`: Extract the name of the beneficiary if mentioned.
    - `amount`: Extract any numerical amount mentioned (e.g., ">50€", "<100€").

    Return a JSON object with extracted values.

    **Example 1**
    User Input: "Show my payments from last month over 50€."
    Response:
    {{
        "time_frame": "last month",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "category": "Paiements",
        "sub_category": NULL,
        "transaction_type": "Sorties d'argent",
        "beneficiares": NULL,
        "math_operation": NULL,
        "amount": ">50€"
    }}

    **Example 2**
    User Input: "All withdrawals over 100€ this week."
    Response:
    {{
        "time_frame": "this week",
        "start_date": "2025-02-10",
        "end_date": "2025-02-17",
        "category": "Retraits distributeurs",
        "sub_category": NULL,
        "transaction_type": "Sorties d'argent",
        "beneficiares": NULL,
        "math_operation": NULL,
        "amount": ">100€"
    }}

    **Example 3**
    User Input: "Listez toutes les dépenses en nourriture et boissons du mois dernier."
    Response:
    {{
        "time_frame": "last month",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "category": "Paiements",
        "sub_category": "Nourriture et boissons",
        "transaction_type": "Sorties d'argent",
        "beneficiares": NULL,
        "math_operation": NULL,
        "amount": "NULL"
    }}
    **Example 4**
    User Input: "How much did I spend a Baoina last month."
    Response:
    {{
        "time_frame": "last month",
        "start_date": "2025-01-01",
        "end_date": "2025-01-31",
        "category": "Paiements",
        "sub_category": "Nourriture et boissons",
        "transaction_type": "Sorties d'argent",
        "beneficiares": Baoina,
        "math_operation": NULL,
        "amount": "NULL"
    }}

    User Input: "{user_input}"
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Extract structured data for transaction filtering."},
                  {"role": "user", "content": prompt}],
        response_format= {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema":reponse_format,
                    "strict": True
                }},
        temperature=0
    )

    extracted_data = response.choices[0].message.content

    try:
        extracted_data = json.loads(extracted_data)  # Convert response into JSON format
    except json.JSONDecodeError:
        extracted_data = {"error": "Invalid JSON response format"}

    return extracted_data

def record_and_transcribe():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("🎤 Recording... Speak now!")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        print("Processing audio...")

        # Save the audio as a WAV file
        audio_filename = "recorded_audio.wav"
        with open(audio_filename, "wb") as f:
            f.write(audio.get_wav_data())  # Convert and save audio

        try:
            # Use OpenAI Whisper API to transcribe
            with open(audio_filename, "rb") as audio_file:
                transcription = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                print(f"📝 Transcribed Text: {transcription}")
                return transcription
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            return None

async def is_transaction_query_openai(user_input):
    """Uses OpenAI to check if the query is transaction-related."""
    prompt = f"""
    You are an AI assistant that determines whether a given user query is related to personal financial transactions.

    **Transaction-related queries include:**
    - Checking balance
    - Payments, expenses, and spending
    - Deposits and withdrawals
    - Bank transfers and transactions
    - Loan payments and financial statements

    **Non-transaction queries include:**
    - Questions about weather, news, general knowledge
    - Queries unrelated to finance or banking
    - Conversations that do not involve money movement

    **Example 1**
    User: "How much did I spend last month?"
    AI Response: "Yes"

    **Example 2**
    User: "What's the weather like today?"
    AI Response: "No"

    **Example 3**
    User: "Show me my last 5 transactions."
    AI Response: "Yes"

    **Example 4**
    User: "Tell me a joke."
    AI Response: "No"

    **Now classify this user input:**
    User: "{user_input}"
    AI Response:
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Classify whether a query is related to transactions."},
                  {"role": "user", "content": prompt}],
        temperature=0
    )

    # Extract AI response
    ai_response = response.choices[0].message.content.strip().lower()
    
    return "yes" in ai_response 

def transcribe(audio_file_path):
    try:
        # Use OpenAI Whisper API to transcribe
        with open(audio_file_path, "rb") as audio_file:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            print(f"📝 Transcribed Text: {transcription}")
            return transcription
    except Exception as e:
        print(f"❌ Error transcribing audio: {e}")
        return None