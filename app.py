import mysql.connector
from config import DB_CONFIG
import json
from modules.pdf_reader import extract_text_from_pdf
from modules.ai_extractor import extract_invoice_data
from modules.db_insert import insert_invoice, invoice_exists
from modules.uuid_extractor import extract_uuid_from_text
from flask import Flask, render_template, request, redirect, url_for
from setup_database import setup_database
import os

app = Flask(__name__)

setup_database()

UPLOAD_FOLDER = "invoices"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files["file"]

        if file and file.filename.endswith(".pdf"):
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            return redirect(url_for("upload"))

    return render_template("upload.html")


@app.route("/process")
def process():

    invoices_folder = "invoices"
    processed = []

    pdf_files = sorted([
        file for file in os.listdir(invoices_folder)
        if file.lower().endswith(".pdf")
    ])

    for filename in pdf_files:

        pdf_path = os.path.join(invoices_folder, filename)

        text = extract_text_from_pdf(pdf_path)

        uuid = extract_uuid_from_text(text)

        if uuid and invoice_exists(uuid):
            processed.append(f"{filename} → Duplicate skipped")
            continue

        data = extract_invoice_data(text)

        if not data:
            processed.append(f"{filename} → No data extracted")
            continue

        processed.append(f"{filename} → Processed successfully")

    return render_template("process.html", processed=processed)


@app.route("/invoices")
def invoices():

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, uuid, invoice_date, supplier, total, category
        FROM invoices
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("invoices.html", invoices=rows)


@app.route("/process")
def process_invoices():
    ...


if __name__ == "__main__":
    app.run(debug=True)