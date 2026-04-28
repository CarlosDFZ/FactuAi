import os
import uuid
import random
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


OUTPUT_DIR = "invoices"
os.makedirs(OUTPUT_DIR, exist_ok=True)


suppliers = [
    "Office Depot",
    "Amazon",
    "Walmart",
    "Costco",
    "Gas Station MX",
    "Tech Store",
    "Software Solutions",
    "Paper World",
    "Digital Services",
    "Super Market MX",
]


categories = [
    "office supplies",
    "food",
    "fuel",
    "electronics",
    "software",
    "services",
]


descriptions_by_category = {
    "office supplies": [
        "Office supplies purchase",
        "Paper, pens and notebooks",
        "Printer ink and folders",
    ],
    "food": [
        "Food and beverages purchase",
        "Restaurant consumption",
        "Grocery items",
    ],
    "fuel": [
        "Fuel refill",
        "Gasoline purchase",
        "Premium fuel refill",
    ],
    "electronics": [
        "Electronics purchase",
        "Computer accessories",
        "Keyboard and mouse purchase",
    ],
    "software": [
        "Software subscription",
        "Cloud service subscription",
        "Productivity software license",
    ],
    "services": [
        "General business service",
        "Technical support service",
        "Maintenance service",
    ],
}


def random_date():
    start_date = datetime(2023, 1, 1)
    return start_date + timedelta(days=random.randint(0, 500))


def generate_invoice(index):
    file_name = f"invoice_fake_{index}.pdf"
    path = os.path.join(OUTPUT_DIR, file_name)

    invoice_uuid = str(uuid.uuid4()).upper()
    invoice_date = random_date().strftime("%Y-%m-%d")
    supplier = random.choice(suppliers)
    category = random.choice(categories)
    description = random.choice(descriptions_by_category[category])

    subtotal = round(random.uniform(100, 5000), 2)
    taxes = round(subtotal * 0.16, 2)
    total = round(subtotal + taxes, 2)

    c = canvas.Canvas(path, pagesize=letter)

    y = 750

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "INVOICE")
    y -= 40

    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Invoice UUID: {invoice_uuid}")
    y -= 20
    c.drawString(50, y, f"Invoice Date: {invoice_date}")
    y -= 20
    c.drawString(50, y, f"Supplier: {supplier}")
    y -= 20
    c.drawString(50, y, f"Description: {description}")
    y -= 20
    c.drawString(50, y, f"Category: {category}")
    y -= 20
    c.drawString(50, y, f"Subtotal: {subtotal}")
    y -= 20
    c.drawString(50, y, f"Taxes: {taxes}")
    y -= 20
    c.drawString(50, y, f"Total: {total}")
    y -= 20
    c.drawString(50, y, "Currency: MXN")

    c.save()

    print(f"Generated: {file_name}")


def generate_multiple_invoices(quantity=15):
    for index in range(1, quantity + 1):
        generate_invoice(index)


if __name__ == "__main__":
    generate_multiple_invoices(30)