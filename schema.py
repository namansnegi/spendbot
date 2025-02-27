reponse_format = {
  "type": "object",
  "properties": {
    "time_frame": {
      "type": "string",
      "description": "The relevant time period extracted from the user query (e.g., 'last month', 'this year'). If not found, return an empty string."
    },
    "start_date": {
      "type": "string",
      "description": "The start date of the time period in YYYY-MM-DD format. If not found, return an empty string."
    },
    "end_date": {
      "type": "string",
      "description": "The end date of the time period in YYYY-MM-DD format. If not found, return an empty string."
    },
    "movement_type": {
      "type": "string",
      "description": "The most relevant transaction category from the predefined list. If not found, return an empty string."
    },
    "pfm-category": {
      "type": "string",
      "description": "The most relevant pfm category from the predefined list. If not found, return an empty string."
    },
    "movement_scope": {
      "type": "string",
      "description": "The most relevant transaction type from the predefined list. If not found, return an empty string."
    },
    "math_operation": {
      "type": "string",
      "enum": ["SUM", "MAX", "MIN", "AVG", "COUNT"],
      "description": "The mathematical operation inferred from the query intent. Example: 'total spent' -> SUM, 'highest expense' -> MAX, 'average expense' -> AVG. If not found, return an empty string."
    },
    "amount": {
      "type": "string",
      "description": "The extracted amount from the user query, including comparison operators if present (e.g., '>50€', '<100€', '=200€'). If not found, return an empty string."
    },
    "keywords": {
      "type": "string",
      "description": "The extracted keywords from the user query. If not found, return an empty string."
    }
  },
  "required": [
    "time_frame",
    "start_date",
    "end_date",
    "movement_type",
    "pfm-category",
    "movement_scope",
    "math_operation",
    "amount",
    "keywords"
  ],
  "additionalProperties": False
}
