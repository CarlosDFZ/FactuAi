import csv
import logging
import mysql.connector
from config import DB_CONFIG
from decimal import Decimal, InvalidOperation
import json
from modules.pdf_reader import extract_text_from_pdf
from modules.ai_extractor import extract_invoice_data
from modules.db_insert import insert_invoice, invoice_exists
from modules.uuid_extractor import extract_uuid_from_text
from flask import Flask, render_template, request, redirect, url_for, Response, flash, send_file
from setup_database import setup_database
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY") or os.urandom(24)

setup_database()

UPLOAD_FOLDER = "invoices"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LOG_FOLDER = "logs"
os.makedirs(LOG_FOLDER, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_FOLDER, "factuai.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def is_allowed_pdf(filename):
    return bool(filename) and filename.lower().endswith(".pdf")


def get_invoice_path(filename):
    safe_filename = secure_filename(filename)

    if not safe_filename or safe_filename != filename or not is_allowed_pdf(safe_filename):
        return None

    upload_folder = os.path.abspath(app.config["UPLOAD_FOLDER"])
    pdf_path = os.path.abspath(os.path.join(upload_folder, safe_filename))

    if os.path.commonpath([upload_folder, pdf_path]) != upload_folder:
        return None

    return pdf_path


def validate_invoice_data(data, filename):
    required_fields = ["uuid", "invoice_date", "supplier", "total"]

    for field in required_fields:
        if data.get(field) in (None, ""):
            return False, f"{filename} -> Missing required field: {field}"

    try:
        data["total"] = Decimal(str(data.get("total")))
    except (InvalidOperation, TypeError, ValueError):
        return False, f"{filename} -> Invalid total value"

    return True, None


def process_invoice_file(filename):
    pdf_path = get_invoice_path(filename)

    if not pdf_path or not os.path.exists(pdf_path):
        return f"{filename} -> PDF file not found or unsafe filename", False

    try:
        text = extract_text_from_pdf(pdf_path)
    except Exception:
        logging.exception("PDF extraction error for %s", filename)
        return f"{filename} -> PDF extraction error", False

    uuid = extract_uuid_from_text(text)

    try:
        if uuid and invoice_exists(uuid):
            logging.info("Duplicate skipped: %s", filename)
            return f"{filename} -> Duplicate skipped", False
    except mysql.connector.Error:
        logging.exception("Database error while checking duplicate for %s", filename)
        return f"{filename} -> Database error while checking duplicate", False

    try:
        data = extract_invoice_data(text)
    except Exception:
        logging.exception("AI extraction error for %s", filename)
        return f"{filename} -> AI extraction error", False

    if not data:
        logging.warning("AI extraction returned no data for %s", filename)
        return f"{filename} -> No data extracted", False

    if not data.get("uuid") and uuid:
        data["uuid"] = uuid

    try:
        if invoice_exists(data.get("uuid")):
            logging.info("Duplicate skipped after AI: %s", filename)
            return f"{filename} -> Duplicate skipped after AI", False
    except mysql.connector.Error:
        logging.exception("Database error while checking AI duplicate for %s", filename)
        return f"{filename} -> Database error while checking duplicate", False

    is_valid, validation_message = validate_invoice_data(data, filename)
    if not is_valid:
        logging.warning("Invalid invoice skipped: %s", validation_message)
        return validation_message, False

    json_folder = "data/json"
    os.makedirs(json_folder, exist_ok=True)

    json_filename = os.path.splitext(filename)[0] + ".json"
    json_path = os.path.join(json_folder, json_filename)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)

    try:
        insert_invoice(data, pdf_path)
    except mysql.connector.Error:
        logging.exception("Database error while inserting %s", filename)
        return f"{filename} -> Database error while saving invoice", False

    logging.info("Invoice processed successfully: %s", filename)
    return f"{filename} -> Processed successfully", True


@app.route("/")
def index():

    try:
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
    except mysql.connector.Error:
        logging.exception("Database error while loading dashboard")
        flash("Database error while loading dashboard.")
        stats = None
        categories = []

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
            if not file or not file.filename:
                continue

            safe_filename = secure_filename(file.filename)

            if not safe_filename or not is_allowed_pdf(safe_filename):
                flash(f"{file.filename} was skipped because only PDF files are allowed.")
                continue

            filepath = get_invoice_path(safe_filename)

            if not filepath:
                flash(f"{file.filename} was skipped because the filename is unsafe.")
                continue

            file.save(filepath)
            uploaded_count += 1
            logging.info("Uploaded invoice: %s", safe_filename)

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
        message, _ = process_invoice_file(filename)
        processed.append(message)

    flash("Invoices processed successfully.")
    return render_template("process.html", processed=processed)


@app.route("/invoices")
def invoices():

    search = request.args.get("search", "")

    try:
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
    except mysql.connector.Error:
        logging.exception("Database error while loading invoices")
        flash("Database error while loading invoices.")
        rows = []

    return render_template("invoices.html", invoices=rows, search=search)


@app.route("/export/csv")
def export_csv():
    try:
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
    except mysql.connector.Error:
        logging.exception("Database error while exporting CSV")
        flash("Database error while exporting CSV.")
        return redirect(url_for("invoices"))

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

    try:
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
    except mysql.connector.Error:
        logging.exception("Database error while loading invoice %s", invoice_id)
        flash("Database error while loading invoice.")
        return redirect(url_for("invoices"))

    if not row:
        flash("Invoice not found.")
        return redirect(url_for("invoices"))

    row["pdf_filename"] = os.path.basename(row["pdf_path"]) if row.get("pdf_path") else ""

    return render_template("invoice_detail.html", invoice=row)

@app.route("/invoice/delete/<int:invoice_id>", methods=["POST"])
def delete_invoice(invoice_id):

    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM invoices
            WHERE id = %s
        """, (invoice_id,))

        connection.commit()

        cursor.close()
        connection.close()
    except mysql.connector.Error:
        logging.exception("Database error while deleting invoice %s", invoice_id)
        flash("Database error while deleting invoice.")
        return redirect(url_for("invoices"))

    flash("Invoice deleted successfully.")
    return redirect(url_for("invoices"))

@app.route("/invoice/pdf/<int:invoice_id>")
def download_invoice_pdf(invoice_id):

    try:
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
    except mysql.connector.Error:
        logging.exception("Database error while loading PDF for invoice %s", invoice_id)
        flash("Database error while loading PDF.")
        return redirect(url_for("invoice_detail", invoice_id=invoice_id))

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

    message, _ = process_invoice_file(filename)
    flash(message)
    return redirect(url_for("files"))

if __name__ == "__main__":
    print("\nFactuAI is running:")
    print("Local:   http://127.0.0.1:5000")
    print("Network: http://localhost:5000")
    print("Press CTRL+C to stop.\n")

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
