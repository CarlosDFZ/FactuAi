import os
import json

from modules.pdf_reader import extract_text_from_pdf
from modules.ai_extractor import extract_invoice_data
from modules.db_insert import insert_invoice, invoice_exists
from modules.uuid_extractor import extract_uuid_from_text
from setup_database import setup_database


setup_database()

invoices_folder = "invoices"

pdf_files = sorted([
    filename for filename in os.listdir(invoices_folder)
    if filename.lower().endswith(".pdf")
])

for filename in pdf_files:
    pdf_path = os.path.join(invoices_folder, filename)

    print("\nProcessing invoice:")
    print(pdf_path)
    print("-" * 50)

    text = extract_text_from_pdf(pdf_path)

    uuid = extract_uuid_from_text(text)

    if uuid:
        print(f"UUID found: {uuid}")

        if invoice_exists(uuid):
            print("Duplicate invoice detected before AI. Skipping.")
            continue
    else:
        print("UUID not found before AI. Sending to AI.")

    data = extract_invoice_data(text)

    print("Extracted JSON:")
    print(data)

    if not data:
        print("No data extracted. Skipping file.")
        continue

    if not data.get("uuid") and uuid:
        data["uuid"] = uuid

    if invoice_exists(data.get("uuid")):
        print("Duplicate invoice detected after AI. Skipping.")
        continue

    required_fields = ["uuid", "invoice_date", "supplier", "total"]

    for field in required_fields:
        if data.get(field) is None:
            print(f"Missing required field: {field}. Skipping file.")
            break
    else:
        json_folder = "data/json"
        os.makedirs(json_folder, exist_ok=True)

        json_filename = os.path.splitext(filename)[0] + ".json"
        json_path = os.path.join(json_folder, json_filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"JSON saved: {json_path}")

        insert_invoice(data, pdf_path)

print("\nAll invoices processed.")