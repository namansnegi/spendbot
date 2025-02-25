reponse_format = {
  "type": "object",
  "properties": {
    "time_frame": {
      "type": "string",
      "description": "The relevant time period extracted from the user query (e.g., 'last month', 'this year')."
    },
    "start_date": {
      "type": "string",
      "description": "The start date of the time period in YYYY-MM-DD format."
    },
    "end_date": {
      "type": "string",
      "description": "The end date of the time period in YYYY-MM-DD format."
    },
    "category": {
      "type": "string",
      "description": "The most relevant transaction category from the predefined list."
    },
    "pfm-category": {
      "type": "string",
      "description": "The most relevant pfm category from the predefined list."
    },
    "sub_category": {
      "type": "string",
      "description": "A more specific sub-category of the transaction."
    },
    "transaction_type": {
      "type": "string",
      "description": "The most relevant transaction type from the predefined list."
    },
    "beneficiaries": {
      "type": ["string", "null"],
      "description": "The name of the beneficiary extracted from the query, or null if none is found."
    },
    "math_operation": {
      "type": "string",
      "enum": ["SUM", "MAX", "MIN", "AVG", "COUNT", "NULL"],
      "description": "The mathematical operation inferred from the query intent. Example: 'total spent' -> SUM, 'highest expense' -> MAX, 'average expense' -> AVG."
    },
    "amount": {
      "type": ["string", "null"],
      "description": "The extracted amount from the user query, including comparison operators if present (e.g., '>50€', '<100€', '=200€'), or null if not mentioned."
    },
    "keywords": {
      "type": ["string", "null"],
      "description": "The extracted keywords from the user query."
    },
    "confidence_scores": {
      "type": "object",
      "properties": {
        "time_frame": { "type": "number"},
        "category": { "type": "number"},
        "sub_category": { "type": "number"},
        "transaction_type": { "type": "number"},
        "beneficiaries": { "type": "number"},
        "math_operation": { "type": "number"},
        "amount": { "type": "number"}
      },
      "required": ["time_frame", "category", "sub_category", "transaction_type", "beneficiaries", "math_operation", "amount"],
      "description": "Confidence scores for each extracted value, indicating how certain the AI is (range 0 to 1).",
      "additionalProperties": False
    },
    "clarification_needed": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of questions for the user when ambiguities are detected in the query (e.g., 'Does PMU refer to a beneficiary or just a location?')."
    },
    "clarification_options": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Two clarification choices the user can select from when clarification is needed."
    }
  },
  "required": [
    "time_frame",
    "start_date",
    "end_date",
    "category",
    "pfm-category",
    "sub_category",
    "transaction_type",
    "beneficiaries",
    "math_operation",
    "amount",
    "keywords",
    "confidence_scores",
    "clarification_needed",
    "clarification_options"
  ],
  "additionalProperties": False
}