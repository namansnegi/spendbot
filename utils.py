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
        You are an AI assistant that extracts structured information from user queries to autofill a transaction filter form.

        ### Context:

        - Today’s date is **{today}**. Use this to interpret time-related queries.  
        - The user may inquire about past transactions using **formal French, slang (argot), or casual speech**.  
        - Certain words in French can refer to **either a spending category or a specific merchant**. **Your job is to resolve these cases intelligently or request clarification if necessary.**  

        ### Given Data:
        - **Transaction Categories:**  
        {AVAILABLE_CATEGORIES}
        - **Transaction Types:**  
        {TRANSACTION_TYPES}

        ---

        ### **Your Task:**
        Extract the following structured details from the user’s query:

        - **`time_frame`**: Identify the relevant time period (e.g., "last month", "this year", "this week").
        - **`start_date` & `end_date`**: Convert the identified time frame into **YYYY-MM-DD** format.
        - **`category`**: Choose the **most relevant** category from the given list.
        - **`sub_category`**: Extract a **detailed sub-category** that better explains the user intent  
        *(e.g., "drinks" → "bars & cafés", "grec" → "restaurant")*.
        - **`transaction_type`**: Choose the **most relevant** transaction type from the given list.
        - **`beneficiaries`**: Identify the beneficiary (if explicitly mentioned).  
        - **If a word could be BOTH a sub-category and a beneficiary, ask for clarification.**  
        - **Example:**  
            - *"Combien ai-je dépensé au Grec ?"* → `"grec"` could mean **"restaurant"** (sub-category) or a **specific kebab shop** (beneficiary).  
            - **Ask:** *"Voulez-vous dire un restaurant grec en général ou un établissement spécifique ?"*

        - **`amount`**: Extract any numerical amount mentioned (e.g., `">50€"`, `"<100€"`).
        - **`confidence_scores`**: Assign a **confidence score (0 to 1)** for each extracted value.
        - **`clarification_needed`**: If ambiguity is detected, **ask for clarification instead of making an uncertain assumption**.

        ---

        ### **Handling Edge Cases:**
        ### **When a Word Can Be a Category or a Beneficiary**
        - Some words refer to **types of businesses** (category) **AND** **specific places** (beneficiary).  
        - **Example:**  
            - *"J’ai claqué au PMU"* → **PMU could be:**
            - **A betting shop** (merchant)
            - **A bar visit** (category = "Bars & Cafés")
            - **Clarify:**  
            *"PMU peut être un lieu de paris ou un simple bar. À quoi faites-vous référence ?"*

        - **Common Cases to Clarify:**
            - **"Grec"** → Is it a generic kebab shop (sub-category) or a named restaurant (beneficiary)?
            - **"McDo"** → Is it the global fast-food chain (beneficiary) or just a type of food expense?
            - **"La boulangerie"** → Is it a category (bakery expenses) or a specific place?

        - **Ambiguous Beneficiaries vs. Sub-categories:**  
        - If a term can have **multiple meanings**, assess the context to determine its intent.  
        - Example:  
            - *"Combien ai-je dépensé au Grec la semaine dernière ?"* → `"grec"` likely refers to `"restaurant"` (sub-category), **not** a specific beneficiary.  
            - *"How much did I spend at PMU last week?"* → `"PMU"` could be a beneficiary or **just a location** where a transaction happened (e.g., for drinks). **Ask for validation if uncertain.**

        - **Implicit Date Ranges:**  
        - `"last week"` → Convert to the appropriate date range.
        - `"January"` → Assume the most recent January unless context suggests otherwise.

        - **Handling Currency & Amounts:**  
        - Extract numerical values along with their operators (`>`, `<`, `=`) and currency if mentioned.

        ---
        ### **Understanding Argot & Casual French**
        - Recognize **French slang and casual phrases** to correctly categorize spending:
            - *"J’ai claqué en soirée"* → `"Bars & Cafés"` or `"Nightclubs & Entertainment"`  
            - *"J’ai mis combien au casino ?"* → **Could be "Gambling" or "Drinks at a casino"**  
            - *"J’ai filé 50 balles à Thomas"* → **Personal payment, likely a money transfer**
            - *"J’ai tout cramé à la FNAC"* → **Shopping, likely books/electronics**

- **If unsure, ask the user for clarification.**

        ### **Return Format:**
        Return a **JSON object** with the extracted values.

        ---

        ### **Example Responses**

        #### **Example 1**
        **User Input:** `"Show my payments at PMU last month over 50€."`
        Response:
        {{
            "time_frame": "last month",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "category": "Paiements",
            "sub_category": "Drinks",
            "transaction_type": "Sorties d'argent",
            "beneficiaries": "PMU",
            "math_operation": "NULL",
            "amount": ">50€",
            "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiaries": 0.3,
                "amount": 0.2
            }},
            "clarification_needed": ["PMU peut être un lieu de paris ou un simple bar. À quoi faites-vous référence ?"],
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
                "amount": ">100€",
                "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiary": 0.3,
                "amount": 0.2
                }},
                "clarification_needed": NULL

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
                "amount": "NULL",
                "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiary": 0.3,
                "amount": 0.2
                }},
                "clarification_needed": NULL
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
                "amount": "NULL",
                "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiary": 0.3,
                "amount": 0.2
                }},
                "clarification_needed": NULL
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