import openai
import speech_recognition as sr
import json
from datetime import datetime
from schema import reponse_format
import requests
import os
import pandas as pd
import re
from constants import MOUVEMENT_SCOPES, MOUVEMENT_TYPES, PFM_CATEGORIES


openai.api_key = os.getenv("OPENAI_API_KEY")


if openai.api_key is None:
    raise ValueError("❌ OPENAI_API_KEY is not set. Make sure to add it to Heroku.")



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
        - **Avoid extracting generic finance-related terms** like "dépenses", "transactions", "paiements".
        - **Colloquial expressions & merchant abbreviations should be mapped correctly** (e.g., *McDo → McDonald’s*, *Décat → Decathlon*).
        - **Refund-related queries should differentiate between actual refunds and bank transfers.**
        - **Temporal logic should be precise**:
          - If a month is mentioned but hasn’t arrived yet, **default to the previous year**.
          - If no date is specified, default to **the last complete month**.

        ### Given Data:
        - **movement_type:**  
        {MOUVEMENT_TYPES}
        - **movement_scope:**  
        {MOUVEMENT_SCOPES}
        - **pfm_category:**
        {PFM_CATEGORIES}
        ---

        ### **Your Task:**
        Extract the following structured details from the user’s query:

        - **`time_frame`**: Identify the relevant time period (e.g., "last month", "this year", "this week").
        - **`start_date` & `end_date`**: Convert the identified time frame into **YYYY-MM-DD** format.
        - **`movement_type`**: Choose the **most relevant** category from the given list. There can be more than one category. Only select from this list {MOUVEMENT_TYPES}. Dont invent or select from any other list
            - NEVER infer movement_type from pfm_category values.
            - If the user mentions a term that exists ONLY in pfm_category (like "remboursement"), DO NOT set movement_type to it.
            - If the user mentions receiving money (e.g., "j’ai reçu un remboursement"), select:
                - "user_gain" if it’s personal income.
                - "bank_transfer" if it’s a known financial transaction.
            - If the refund is from an external source (e.g., "remboursement de mutuelle" or "remboursement Sécu"), select:
                - "bank_transfer" (since it's an inbound payment from an institution).
                - "user_gain" (if it's uncertain).

        - **`pfm_category`**: Choose all the **most relevant** PFM category from the given list. Can have more than one category.
            Choose ALL relevant categories from {PFM_CATEGORIES}.
            If a transaction logically belongs to multiple categories, return all of them.
            DO NOT limit to only one category if others apply.
            Examples of multi-category assignments:
                "remboursement de mutuelle" → ["refund", "health_insurance"]
                "remboursement de l’assurance auto" → ["refund", "auto_insurance"]
                "remboursement sur un voyage annulé" → ["refund", "travel_accomodation"]
                "remboursement médical" → ["refund", "medical"]
                "J’ai payé mon abonnement Netflix" → ["online_content", "entertainment"]
                "J’ai commandé un Uber hier soir" → ["transportation", "taxis"]
                "J’ai acheté un MacBook à la FNAC" → ["electronics_it_stores", "multimedia"]
                "J’ai pris un hôtel et un billet de train pour mes vacances" → ["travel_accomodation", "travel_means"]
                "J’ai acheté une perceuse chez Castorama" → ["diy", "electronics_it_stores"]
                "J’ai payé mon loyer et mes charges" → ["rent", "others_housing"]
                "J’ai envoyé de l’argent à un ami sur Lydia" → ["lydia_with_contacts", "bank_transfer"]
                "J’ai commandé un burger sur Uber Eats" → ["food_delivery", "restaurants"]
                "J’ai acheté des lunettes chez Afflelou" → ["optical_hearing", "medical"]
                "J’ai mis de l’essence et payé un péage" → ["tolls_gas_stations", "commuting"]
                "J’ai acheté des vêtements et des chaussures" → ["clothing", "shopping_center"]
                "J’ai souscrit à un VPN et un abonnement à un site d’actualités" → ["vpns", "newspapers_magasines"]
            DO NOT invent categories that are not in {PFM_CATEGORIES}.
            If multiple categories are applicable, always return them all.
        - **`movement_scope`**: Choose the **most relevant** movement scope from the given list. There can be more than one movement scope. Only select from this list {MOUVEMENT_SCOPES}.Dont invent or select from any other list
        - **`amount`**: Extract any numerical amount mentioned (e.g., `">50€"`, `"<100€"`). The is the amount value of money paid or received for a transaction
        - **`math_operation`**: Identify the mathematical operation implied by the query (e.g., "total spent" → `SUM`, "highest expense" → `MAX`). 
        - **`keywords`**: Extract only transaction-relevant keywords.
          -Extract **ONLY specific and relevant terms** as keywords that can be matched in transaction records.
            - **DO NOT return generic words** like "dépenses", "transactions", "paiements".
            - **DO NOT return generic terms** like "bar", "tabac" "supermache" etc. The keywords should be proper nouns(names) and not common nouns.
            - Keywords should be proper nouns (names of people, businesses, institutions, brands, or cities).
            - DO NOT extract generic words like "bar du coin," "proprio," "marché local," "duty-free," "garagiste," etc.
            - Only include proper names of businesses, places, or known entities that can be matched in transaction records.
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

                **User Input:** `"2025 dépenses"`
                **Keywords:** `[]` ❌ (NO keywords should be extracted)

                **User Input:** `"Mes transactions en 2025 pour tabac au Baiona plus de 10 euros"`
                **Keywords:** `[Baiona]` ✅ (NOT "transactions", NOT "tabac" NOT "supermarché" NOT "2025", NOT "10 euros")
        ---
        ### **Handling Merchant Names & Colloquial Expressions**
        - Maintain a **mapping** of common abbreviations:
          - *McDo* → *McDonald’s*
          - *Décat* → *Decathlon*
          - Sécu → Sécurité sociale
          - Prime → Amazon Prime
          - *Tabac* → **Should NOT be extracted as a keyword** (generic term)

        ### **Handling Edge Cases:**
        ### **When a Word Can have different pfm_category**
        - Some words refer to **types of businesses** (category) **AND** **specific places** (beneficiary).  
        - **Example:**  
            - *"J’ai claqué au PMU"* → **PMU could be:**
            - **A betting shop** (pfm_category = "betting)
            - **A bar visit** (pfm_category = "cafes_bars")
            - In this case return all the possible pfm_category and ask for clarification.
            - **Clarify:**  
            *"PMU peut être un lieu de paris ou un simple bar. À quoi faites-vous référence ?"*

        - **Implicit Date Ranges:**  
        - `"last week"` → Convert to the appropriate date range.
        - `"January"` → Assume the most recent January unless context suggests otherwise.
        - Do not return any dates after the present date of {today}

        - **Handling Currency & Amounts:**  
        - Extract numerical values along with their operators (`>`, `<`, `=`) and currency if mentioned.

        ---
        ### **Understanding Argot & Casual French**
        - Recognize **French slang and casual phrases** to correctly categorize spending:
            - *"J’ai claqué en soirée"* → `"Bars & Cafés"` or `"Nightclubs & Entertainment"`  
            - *"J’ai mis combien au casino ?"* → **Could be "Gambling" or "Drinks at a casino"**  
            - *"J’ai filé 50 balles à Thomas"* → **Personal payment, likely a money transfer**
            - *"J’ai tout cramé à la FNAC"* → **Shopping, likely books/electronics**

        Return a **JSON object** with the extracted values.

        ---

        #### **Example 1**
        **User Input:** `"Show my payments at PMU last month over 50€."`
        Response:
        {{
            "time_frame": "last month",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "movement_type": "payments",
            "pfm_category": "cafes_bars, betting",
            "movement_scope": "Sorties d'argent",
            "math_operation": "",
            "amount": ">50€",
            "keywords": "PMU"
        }}
            **Example 2**
            User Input: "All withdrawals over 100€ this week."
            Response:
            {{
                "time_frame": "this week",
                "start_date": "2025-02-10",
                "end_date": "2025-02-17",
                "movement_type": "atm",
                "pfm_category": "atm",
                "movement_scope": "Sorties d'argent",
                "math_operation": "",
                "amount": ">100€",
                "keywords": ""
            }}

            **Example 3**
            User Input: "Listez toutes les dépenses en nourriture et boissons du mois dernier."
            Response:
            {{
                "time_frame": "last month",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "movement_type": "payment",
                "pfm_category": "restaurants",
                "movement_scope": "Sorties d'argent",
                "math_operation": "",
                "amount": "",
                "keywords": ""
            }}
            **Example 4**
            User Input: "How much did I spend a Baoina last month."
            Response:
            {{
                "time_frame": "last month",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "movement_type": "payment",
                "pfm_category": "cafes_bars, restaurants",
                "movement_scope": "Sorties d'argent",
                "math_operation": "",
                "amount": "",
                "keywords": "Baoina"
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
def create_advanced_search_url(base_url, filters):

    url = f"{base_url}?advanced_search"
    movement_scope_map = {
        "Entrées d'argent": "debit",
        "Sorties d'argent": "credit",
        "Inter-comptes": "inter"
    }

    movement_scope = movement_scope_map.get(filters["movement_scope"], None)

    # Add filters to the URL
    if 'start_date' in filters and filters['start_date']:
        url += f"&date_after={filters['start_date']}T00:00:00Z"
    if 'end_date' in filters and filters['end_date']:
        url += f"&date_before={filters['end_date']}T23:59:59Z"

    # Handle amount filters
    if 'amount' in filters and filters['amount']:
        operator, value = clean_amount(filters['amount'])
        if operator and value is not None:
            url += f"&amount={int(value * 100)}"
            if operator == ">":
                q_operator = "gte"
            elif operator == "<":
                q_operator = "lte"
            elif operator == "=":
                q_operator = "eq"
               
            url += f"&amount_equal={q_operator}"
            url += f"&amount_approximate={str(filters.get('amount_approximate', True)).lower()}"

    if 'movement_type' in filters and filters['movement_type'] and filters['movement_type'] != "NULL":
        url += f"&movement_type={filters['movement_type']}"
    if 'movement_scope' in filters and filters['movement_scope'] and filters['movement_scope'] != "NULL":
        url += f"&movement_scope={movement_scope}"
    if 'keywords' in filters and filters['keywords'] and filters['keywords'] != "NULL":
        url += f"&q={filters['keywords'].replace(' ', '%20').replace(',', '%20')}"
    if 'pfm_category' in filters and filters['pfm_category'] and filters['pfm_category'] != "NULL":
        url += f"&movement_scope={filters['pfm_category']}"

    return url