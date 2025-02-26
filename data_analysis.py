import openai
import json
from datetime import datetime
import os

openai.api_key = os.getenv("OPENAI_API_KEY")


response_format = {
    "type": "object",
    "properties": {
        "total_spending": {
            "type": "number",
            "description": "The total amount spent across all transactions."
        },
        "average_spending": {
            "type": "object",
            "description": "The average spending per time unit (e.g., daily, weekly, monthly).",
            "properties": {},  # Define as an object with unspecified properties
            "additionalProperties": {
                "type": "number"
            }
        },
        "frequency": {
            "type": "object",
            "description": "The count of transactions per time unit.",
            "properties": {},  # Define as an object with unspecified properties
            "additionalProperties": {
                "type": "integer"
            }
        },
        "peak_spending_day": {
            "type": "string",
            "description": "The day or period with the highest spending."
        },
        "peak_spending_amount": {
            "type": "number",
            "description": "The amount spent on the peak spending day or period."
        },
        "spending_trend": {
            "type": "string",
            "description": "The trend of spending over time (e.g., increasing, decreasing, stable)."
        },
        "current_period_spending": {
            "type": "number",
            "description": "The total spending in the current period."
        },
        "previous_period_spending": {
            "type": "number",
            "description": "The total spending in the previous period."
        },
        "percentage_change": {
            "type": "number",
            "description": "The percentage change in spending between the current and previous periods."
        }
    },
    "required": [
        "total_spending",
        "average_spending",
        "frequency",
        "peak_spending_day",
        "peak_spending_amount",
        "spending_trend",
        "current_period_spending",
        "previous_period_spending",
        "percentage_change"
    ],
    "additionalProperties": False  # Ensure extra fields are not allowed
}
# file_path = '/Users/namannegi/Downloads/spend_bot/extrait_sumeria_tabac.json'
# with open(file_path, "r", encoding="utf-8") as file:
#     transaction_data = json.load(file)


# Example function to analyze transactions using OpenAI
def analyze_transactions_with_openai(transaction_data):

    prompt = f"""
    You are an AI financial analyst. Analyze the provided transaction data and extract only the **most important financial insights** in a **concise and factual manner**.
    {transaction_data}

    ### Analyses to Perform:
    - Group transactions by category, merchant, or location if multiple values exist.
    - Analyze and summarize the results.
    - Identify the highest transaction amount overall or within a specific group/category if available.
    - Calculate the average transaction amount overall or within a specific group/category if available. Provide ifo about the selected group/category eg per day week etc
    - Analyze spending trends over time to identify patterns such as increasing or decreasing spending.
    - Identify any seasonal trends or changes during holidays.
    - Avoid unnecessary explanations or reflections—only state the facts.
    - Keep sentences short and direct.
    - **State only the key facts** about the transactions.
    - **Do not include interpretations or assumptions.** 
    - Report **only measurable insights** (e.g., total spending, highest transaction, frequency).
    - If an insight lacks a trend or pattern, **omit it.**
    - Be **clear and specific**—for example, clarify what "average" is based on.

    - Present top 3 highlights (3 points as a one liner) as a **brief structured summary**.
    - Use your imagination to create a **concise and informative** response.
    - **No unnecessary descriptions, reflections, or trends unless critical.**
    - **Strictly state the key numbers and facts.**
    Ensure the response is **short, precise, and strictly factual.** Omit insights that are **not significant.**
    Do not include things Headings like Summary of Key Insights, or any other unnecessary information. 
    
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "Analyze financial transaction data."},
                  {"role": "user", "content": prompt}],
        temperature=0.5
    )

    analysis_results = response.choices[0].message.content


    return analysis_results
