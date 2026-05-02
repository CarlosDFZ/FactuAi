import csv
import mysql.connector
from config import DB_CONFIG
import json
from modules.pdf_reader import extract_text_from_pdf
from modules.ai_extractor import extract_invoice_data
from modules.db_insert import insert_invoice, invoice_exists
from modules.uuid_extractor import extract_uuid_from_text
from flask import Flask, render_template, request, redirect, url_for, Response, flash, send_file
from setup_database import setup_database
import os

app = Flask(__name__)

app.secret_key = "factuai_secret_key"

setup_database()

UPLOAD_FOLDER = "invoices"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            COUNT(*) AS total_invoices,
            COALESCE(SUM(total), 0) AS total_expenses,
            COALESCE(AVG(total), 0) AS average_invoice,
            COALESCE(SUM(taxes), 0) AS total_taxes
        FROM invoices
    """)

    stats = cursor.fetchone()

    cursor.execute("""
        SELECT category, COUNT(*) AS qty
        FROM invoices
        GROUP BY category
        ORDER BY qty DESC
        LIMIT 5
    """)

    categories = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "index.html",
        stats=stats,
        categories=categories
    )


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        files = request.files.getlist("files")

        uploaded_count = 0

        for file in files:
            if file and file.filename.lower().endswith(".pdf"):
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                file.save(filepath)
                uploaded_count += 1

        if uploaded_count > 0:
            flash(f"{uploaded_count} invoice PDF(s) uploaded successfully.")
        else:
            flash("No valid PDF files were uploaded.")

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

        if not data.get("uuid") and uuid:
            data["uuid"] = uuid

        if invoice_exists(data.get("uuid")):
            processed.append(f"{filename} → Duplicate skipped after AI")
            continue

        required_fields = ["uuid", "invoice_date", "supplier", "total"]

        missing = False
        for field in required_fields:
            if data.get(field) is None:
                processed.append(f"{filename} → Missing {field}")
                missing = True
                break

        if missing:
            continue

        json_folder = "data/json"
        os.makedirs(json_folder, exist_ok=True)

        json_filename = os.path.splitext(filename)[0] + ".json"
        json_path = os.path.join(json_folder, json_filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        insert_invoice(data, pdf_path)

        processed.append(f"{filename} → Processed successfully")

    flash("Invoices processed successfully.")
    return render_template("process.html", processed=processed)


@app.route("/invoices")
def invoices():

    search = request.args.get("search", "")

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT id, uuid, invoice_date, supplier, total, category
        FROM invoices
        WHERE supplier LIKE %s
           OR category LIKE %s
           OR uuid LIKE %s
        ORDER BY id DESC
    """

    value = f"%{search}%"

    cursor.execute(query, (value, value, value))

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("invoices.html", invoices=rows, search=search)


@app.route("/export/csv")
def export_csv():
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, uuid, invoice_date, supplier, description, subtotal, taxes, total, currency, category, pdf_path, created_at
        FROM invoices
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    def generate():
        header = [
            "id", "uuid", "invoice_date", "supplier", "description",
            "subtotal", "taxes", "total", "currency", "category",
            "pdf_path", "created_at"
        ]

        yield ",".join(header) + "\n"

        for row in rows:
            clean_row = [str(value).replace(",", " ") if value is not None else "" for value in row]
            yield ",".join(clean_row) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=factuai_invoices.csv"}
    )

@app.route("/invoice/<int:invoice_id>")
def invoice_detail(invoice_id):

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM invoices
        WHERE id = %s
    """, (invoice_id,))

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    return render_template("invoice_detail.html", invoice=row)

@app.route("/invoice/delete/<int:invoice_id>", methods=["POST"])
def delete_invoice(invoice_id):

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM invoices
        WHERE id = %s
    """, (invoice_id,))

    connection.commit()

    cursor.close()
    connection.close()

    flash("Invoice deleted successfully.")
    return redirect(url_for("invoices"))

@app.route("/invoice/pdf/<int:invoice_id>")
def download_invoice_pdf(invoice_id):

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT pdf_path
        FROM invoices
        WHERE id = %s
    """, (invoice_id,))

    row = cursor.fetchone()

    cursor.close()
    connection.close()

    if row and os.path.exists(row["pdf_path"]):
        return send_file(row["pdf_path"], as_attachment=True)

    flash("PDF file not found.")
    return redirect(url_for("invoice_detail", invoice_id=invoice_id))

@app.route("/files")
def files():
    invoices_folder = "invoices"

    pdf_files = sorted([
        file for file in os.listdir(invoices_folder)
        if file.lower().endswith(".pdf")
    ])

    return render_template("files.html", files=pdf_files)

@app.route("/process/<filename>")
def process_single_invoice(filename):

    invoices_folder = "invoices"
    pdf_path = os.path.join(invoices_folder, filename)

    if not os.path.exists(pdf_path):
        flash("PDF file not found.")
        return redirect(url_for("files"))

    text = extract_text_from_pdf(pdf_path)

    uuid = extract_uuid_from_text(text)

    if uuid and invoice_exists(uuid):
        flash("Duplicate invoice detected. Skipping.")
        return redirect(url_for("files"))

    data = extract_invoice_data(text)

    if not data:
        flash("No data extracted.")
        return redirect(url_for("files"))

    if not data.get("uuid") and uuid:
        data["uuid"] = uuid

    if invoice_exists(data.get("uuid")):
        flash("Duplicate invoice detected after AI. Skipping.")
        return redirect(url_for("files"))

    required_fields = ["uuid", "invoice_date", "supplier", "total"]

    for field in required_fields:
        if data.get(field) is None:
            flash(f"Missing required field: {field}.")
            return redirect(url_for("files"))

    json_folder = "data/json"
    os.makedirs(json_folder, exist_ok=True)

    json_filename = os.path.splitext(filename)[0] + ".json"
    json_path = os.path.join(json_folder, json_filename)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    insert_invoice(data, pdf_path)

    flash(f"{filename} processed successfully.")
    return redirect(url_for("files"))

if __name__ == "__main__":
    app.run(debug=True)