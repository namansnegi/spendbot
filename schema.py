reponse_format = {
  "type": "object",
  "properties": {
    "time_frame": {
      "type": "string",
      "description": "The relevant time period (e.g., 'last month', 'this year')."
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
    "sub_category": {
      "type": "string",
      "description": "The most relevant transaction sub category from the predefined list."
    },
    "transaction_type": {
      "type": "string",
      "description": "The most relevant transaction type from the predefined list."
    },
    "beneficiares": {
      "type": "string",
      "description": "The most relevant transaction type from the predefined list."
    },
    "math_operation": {
      "type": "string",
      "enum": ["SUM", "MAX", "MIN", "AVG", "COUNT", "NULL"],
      "description": "The mathematical operation based on user intent."
    },
    "amount": {
      "type": ["string", "null"],
      "description": "The extracted amount from the user query (e.g., '>50€', '<100€')."
    }
  },
  "required": ["time_frame", "start_date", "end_date", "category","sub_category", "transaction_type","beneficiares","math_operation", "amount"],
  "additionalProperties": False
}
