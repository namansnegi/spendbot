import openai
import speech_recognition as sr
import json
from datetime import datetime
from schema import reponse_format
import requests
import os
import pandas as pd
import re


openai.api_key = os.getenv("OPENAI_API_KEY")

if openai.api_key is None:
    raise ValueError("❌ OPENAI_API_KEY is not set. Make sure to add it to Heroku.")


AVAILABLE_CATEGORIES = [
    "Rechargement par carte", "Compte courant rémunéré", "Virements", "Paiements",
    "Prélèvements", "Investissement Sumeria", "Prêts Sumeria", "Livret d'épargne",
    "Gains Sumeria", "Dons", "Cartes cadeaux", "Retraits distributeurs", "Frais"
]
TRANSACTION_TYPES = ["Entrées d'argent", "Sorties d'argent", "Inter-comptes"]

pfm_categories = [
    "atm",
    "auto_insurance",
    "bakeries",
    "neutral_for_information",
    "benefits",
    "betting",
    "bio_markets",
    "cafes_bars",
    "car_rental",
    "car_wash_repair",
    "children_care",
    "clothing",
    "commodities",
    "commuting",
    "credit_conso",
    "cosmetics",
    "opera_theatre_concerts_standup_museum_cinema",
    "dating",
    "debt_collection",
    "diy",
    "education_degrees",
    "electronics_it_stores",
    "entertainment",
    "fintechs",
    "fintechs_suspicious",
    "food_delivery",
    "food_retail",
    "18_plus",
    "furniture",
    "gaming",
    "gifts",
    "give",
    "hairdresser",
    "hard_bank_fees",
    "hardest_bank_fees",
    "health_insurance",
    "insurance",
    "internal",
    "jewelry",
    "laundromat_pressing",
    "leasing",
    "legal_finance",
    "loans",
    "marketplace",
    "medical",
    "misc",
    "multimedia",
    "newspapers_magasines",
    "new_means_of_transportation",
    "online_courses",
    "optical_hearing",
    "other_income",
    "other_passive_activities",
    "others_housing",
    "parking",
    "pet_stuff",
    "pharmacies",
    "phone_internet_plan",
    "photography_art",
    "playful_culture",
    "prepaid_cards",
    "professional_expenses",
    "refund",
    "rent",
    "restaurants",
    "retro_bank_fees",
    "salary_revenues",
    "savings_investments",
    "security",
    "self_care",
    "mailing_printing_delivery",
    "shopping_center",
    "snacking",
    "soft_bank_fees",
    "software",
    "sports_activities",
    "sports_equipment",
    "supermarkets",
    "tabac_presse",
    "taxes",
    "taxis",
    "tolls_gas_stations",
    "trading",
    "travel_accomodation",
    "travelling_platforms",
    "travel_means",
    "uncategorizable",
    "vpns",
    "transportation",
    "online_content",
    "groceries",
    "restaurants_bars_cafes"
]


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
        - **PFM Categories:**
        {pfm_categories}
        ---

        ### **Your Task:**
        Extract the following structured details from the user’s query:

        - **`time_frame`**: Identify the relevant time period (e.g., "last month", "this year", "this week").
        - **`start_date` & `end_date`**: Convert the identified time frame into **YYYY-MM-DD** format.
        - **`category`**: Choose the **most relevant** category from the given list. There can be more than one category
        - **`pfm_category`**: Choose all the **most relevant** PFM category from the given list. Can have more than one category.
        - **`sub_category`**: Extract a **detailed sub-category** that better explains the user intent. Should be in french  
        *(e.g., "drinks" → "bars & cafés", "grec" → "restaurant")*.
        - **`transaction_type`**: Choose the **most relevant** transaction type from the given list. There can be more than one transaction type
        - **`beneficiaries`**: Identify the beneficiary (if explicitly mentioned).  
        - **If a word could be BOTH a sub-category and a beneficiary, ask for clarification.**  
        - **Example:**  
            - *"Combien ai-je dépensé au Grec ?"* → `"grec"` could mean **"restaurant"** (sub-category) or a **specific kebab shop** (beneficiary).  
            - **Ask:** *"Voulez-vous dire un restaurant grec en général ou un établissement spécifique ?"*

        - **`amount`**: Extract any numerical amount mentioned (e.g., `">50€"`, `"<100€"`).
        - **`math_operation`**: Identify the mathematical operation implied by the query (e.g., "total spent" → `SUM`, "highest expense" → `MAX`).
        - **`keywords`**: Extract any relevant keywords that could help filter transactions.
          -Extract **ONLY specific and relevant terms** as keywords that can be matched in transaction records.
            - **DO NOT return generic words** like "dépenses", "transactions", "paiements".
            - **DO extract** keywords that indicate a merchant, category, or user-provided label.
            - **DO extract** financial terms from the query that will help filter transactions.
            - The extracted keywords should be useful when matching fields like:
            - `title`
            - `description`
            - `pfm.paymentRecipient.value`
            - `pfm.paymentPurpose.value`
            - `pfm.paymentLabelShortened.value`
            - `userLabel`
            ### **Examples:**
                **User Input:** `"Dépenses McDo 2025"`
                **Keywords:** `["McDo"]` ✅ (NOT "dépenses", NOT "2025")
                
                **User Input:** `"Combien j’ai dépensé chez FNAC en janvier?"`
                **Keywords:** `["FNAC"]` ✅ (NOT "dépensé", NOT "janvier")
                
                **User Input:** `"Paiements au PMU la semaine dernière"`
                **Keywords:** `["PMU"]` ✅ (NOT "paiements", NOT "semaine dernière")

                **User Input:** `"Retrait distributeur janvier"`
                **Keywords:** `["distributeur"]` ✅ (NOT "retrait", NOT "janvier")

                **User Input:** `"2025 dépenses"`
                **Keywords:** `[]` ❌ (NO keywords should be extracted)
        - **`confidence_scores`**: Assign a **confidence score (0 to 1)** for each extracted value.
        - **`clarification_needed`**: If ambiguity is detected, **ask for clarification instead of making an uncertain assumption**.
        - **`clarification_options`**: If a clarification is needed, provide **two possible choices** the user can select from.


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
            "pfm_category": "cafes_bars",
            "sub_category": "Drinks",
            "transaction_type": "Sorties d'argent",
            "beneficiaries": "PMU",
            "math_operation": "NULL",
            "amount": ">50€",
            "keywords": "PMU",
            "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiaries": 0.3,
                "amount": 0.2
            }},
            "clarification_needed": ["PMU peut être un lieu de paris ou un simple bar. À quoi faites-vous référence ?"],
            "clarification_options": ["lieu de paris", "un simple bar"],
        }}
            **Example 2**
            User Input: "All withdrawals over 100€ this week."
            Response:
            {{
                "time_frame": "this week",
                "start_date": "2025-02-10",
                "end_date": "2025-02-17",
                "category": "Retraits distributeurs",
                "pfm_category": "atm",
                "sub_category": NULL,
                "transaction_type": "Sorties d'argent",
                "beneficiares": NULL,
                "math_operation": NULL,
                "amount": ">100€",
                "keywords": "",
                "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiary": 0.3,
                "amount": 0.2
                }},
                "clarification_needed": NULL,
                "clarification_options": ["lieu de paris", "un simple bar"],

            }}

            **Example 3**
            User Input: "Listez toutes les dépenses en nourriture et boissons du mois dernier."
            Response:
            {{
                "time_frame": "last month",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "category": "Paiements",
                "pfm_category": "restaurants",
                "sub_category": "Nourriture et boissons",
                "transaction_type": "Sorties d'argent",
                "beneficiares": NULL,
                "math_operation": NULL,
                "amount": "NULL",
                "keywords": "nourriture","boissons",
                "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiary": 0.3,
                "amount": 0.2
                }},
                "clarification_needed": NULL,
                "clarification_options": ["lieu de paris", "un simple bar"],
            }}
            **Example 4**
            User Input: "How much did I spend a Baoina last month."
            Response:
            {{
                "time_frame": "last month",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "category": "Paiements",
                "pfm_category": "cafes_bars",
                "sub_category": "Nourriture et boissons",
                "transaction_type": "Sorties d'argent",
                "beneficiares": Baoina,
                "math_operation": NULL,
                "amount": "NULL",
                "keywords": "Baoina",
                "confidence_scores": {{
                "time_frame": 1.0,
                "category": 0.9,
                "sub_category": 1.0,
                "transaction_type": 0.95,
                "beneficiary": 0.3,
                "amount": 0.2
                }},
                "clarification_needed": NULL,
                "clarification_options": ["lieu de paris", "un simple bar"],
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

def fetch_history(payload):
    url = "https://preprod.api.lydia-app.com/history/_search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer TESTHISTORYAI3"
    }
    payload = payload

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}", "details": response.text}
    
def clean_amount(amount_str):
    """
    Cleans the amount string by extracting only numeric values and converting to float.
    """
    if not amount_str or amount_str == "NULL":
        return None, None  # No amount provided

    operator = amount_str[0] if amount_str[0] in [">", "<", "="] else "="  # Default to "=" if no operator
    numeric_part = re.sub(r"[^\d.]", "", amount_str)  # Remove everything except numbers and decimal point

    try:
        value = float(numeric_part)
    except ValueError:
        return None, None  # Handle cases where parsing fails

    return operator, value
def generate_elastic_query(transaction_data):
    """
    Converts extracted transaction details into an ElasticSearch Query with multiple multi_match queries.

    :param transaction_data: Extracted transaction filter dictionary
    :return: JSON query for ElasticSearch
    """

    # Helper function to check if a field is valid (not NULL, not empty)
    def is_valid(value):
        return value and value != "NULL"

    # Date Range Filter
    date_range_filter = (
        {
            "range": {
                "createdAt": {
                    "gte": f"{transaction_data['start_date']}T00:00:00Z",
                    "lte": f"{transaction_data['end_date']}T23:59:59Z"
                }
            }
        }
        if is_valid(transaction_data['start_date']) and is_valid(transaction_data['end_date'])
        else None
    )

    # Amount Filter
    amount_filter = None
    amount_str = transaction_data.get('amount', None)
    operator, value = clean_amount(amount_str)

    if value is not None:
        # Determine the range based on the operator
        if operator == ">":
            amount_filter = {
                "bool": {
                    "should": [
                        {
                            "range": {
                                "amount.value": {
                                    "gte": value
                                }
                            }
                        },
                        {
                            "range": {
                                "amount.value": {
                                    "lte": -value
                                }
                            }
                        }
                    ]
                }
            }
        elif operator == "<":
            amount_filter = {
                "bool": {
                    "should": [
                        {
                            "range": {
                                "amount.value": {
                                    "gte": 0.0,
                                    "lte": value
                                }
                            }
                        },
                        {
                            "range": {
                                "amount.value": {
                                    "gte": -value,
                                    "lte": 0.0
                                }
                            }
                        }
                    ]
                }
            }
        elif operator == "=":
            amount_filter = {
                "range": {
                    "amount.value": {
                        "gte": value,
                        "lte": value
                    }
                }
            }

    # Create multiple `multi_match` queries
    multi_match_queries = []
    for key in ["keywords"]:
        if is_valid(transaction_data.get(key)):
            multi_match_queries.append({
                "multi_match": {
                    "query": transaction_data[key],
                    "fields": [
                        "title",
                        "description",
                        "pfm.paymentRecipient.value",
                        "pfm.paymentPurpose.value",
                        "pfm.paymentLabelShortened.value",
                        "userLabel"
                    ],
                    "operator": "or"
                }
            })

    # Constructing Query
    must_clauses = [date_range_filter, amount_filter] + multi_match_queries
    must_clauses = [clause for clause in must_clauses if clause]  # Remove None values

    elastic_query = {
        "from": 0,
        "size": 60,
        "sort": [{"createdAt": "desc"}],
        "query": {
            "bool": {
                "must": must_clauses
            }
        }
    }

    return elastic_query

def format_transaction_data(transaction_data):
    """
    Formats transaction data into a DataFrame for clear tabular display.
    """
    rows = []
    
    for item in transaction_data.get("items", []):
        row = {
            "Date": item.get("created_at", "N/A"),
            "Amount (€)": item.get("amount", "N/A"),
            "Title": item.get("title", "N/A"),
            "Description": item.get("description", "N/A"),
            "Payment Purpose": item.get("pfm.paymentPurpose.value", "N/A"),
            "User Label": item.get("userLabel", "N/A"),
            "Receiver": item.get("receiver", {}).get("name", "N/A"),
            "Payer": item.get("payer", {}).get("name", "N/A"),
            "Category": item.get("pfm_category", "N/A"),
            "Status": item.get("status", "N/A"),
            "Image": item.get("main_picture", "N/A")
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    return df
