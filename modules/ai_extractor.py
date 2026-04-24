from openai import OpenAI
from config import OPENAI_API_KEY
import json

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_invoice_data(text):
    prompt = f"""
    You are an expert in invoice data extraction.

    Extract the following fields from the invoice text and return ONLY a valid JSON object.

    Required fields:
    - uuid (invoice unique identifier / folio fiscal if available)
    - invoice_date (format: YYYY-MM-DD)
    - supplier (lowercase, no punctuation)
    - description
    - subtotal (number)
    - taxes (number)
    - total (number)
    - currency (MXN, USD, EUR, etc.)
    - category (infer a simple category)

    Rules:
    - If a value is missing, use null
    - Do NOT return explanations
    - Do NOT return text outside JSON
    - Return ONLY valid JSON
    - Do NOT wrap the JSON in markdown code blocks.
    - Do NOT use ```json.
    - Return raw JSON only.

    Invoice text:
    {text}
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are an expert in invoice data extraction."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    content = response.choices[0].message.content

    print("Raw AI response:")
    print(content)

    content = content.replace("```json", "")
    content = content.replace("```", "")
    content = content.strip()

    try:
        return json.loads(content)
    except Exception as e:
        print("Error parsing JSON")
        print(e)
        return None