import openai
import json
from datetime import datetime
from schema import reponse_format
import os
from constants import AVAILABLE_CATEGORIES, TRANSACTION_TYPES, PFM_CATEGORIES

openai.api_key = os.getenv("OPENAI_API_KEY")

if openai.api_key is None:
    raise ValueError("❌ OPENAI_API_KEY is not set. Make sure to add it to Heroku.")

def construct_prompt(user_input: str) -> str:

    today = datetime.today().strftime("%Y-%m-%d")
    prompt = f"""
        You are an AI assistant that extracts structured information from user queries to autofill a transaction filter form.

        ### Context:
        - Today’s date is {today}. Use this to interpret time-related queries.  
        - The user may inquire about past transactions using **formal French, slang (argot), or casual speech**.  
        - Certain words in French can refer to **either a spending category or a specific merchant**. **Your job is to resolve these cases intelligently or request clarification if necessary.**  

        ### Given Data:
        - Transaction Categories:{AVAILABLE_CATEGORIES}
        - Transaction Types:{TRANSACTION_TYPES}
        - PFM Categories:{PFM_CATEGORIES}
        ---

        ### **Your Task:**
        Extract the following structured details from the user’s query:

        - **`time_frame`**: Identify the relevant time period (e.g., "last month", "this year", "this week").
        - **`start_date` & `end_date`**: Convert the identified time frame into **YYYY-MM-DD** format.
        - **`category`**: Choose the **most relevant** category from the given list.
        - **`pfm_category`**: Choose all the **most relevant** PFM category from the given list. Can have more than one category.
        - **`sub_category`**: Extract a **detailed sub-category** that better explains the user intent. Should be in french  
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
    return prompt

def extract_filters(user_input):
    prompt = construct_prompt(user_input)   

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