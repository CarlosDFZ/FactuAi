from db import get_connection
import mysql.connector

def invoice_exists(uuid):
    if not uuid:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT id FROM invoices WHERE uuid = %s LIMIT 1"
    try:
        cursor.execute(query, (uuid,))
        result = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    return result is not None

def insert_invoice(data, pdf_path):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
    INSERT INTO invoices 
    (uuid, invoice_date, supplier, description, subtotal, taxes, total, currency, category, pdf_path)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        data.get("uuid"),
        data.get("invoice_date"),
        data.get("supplier"),
        data.get("description"),
        data.get("subtotal"),
        data.get("taxes"),
        data.get("total"),
        data.get("currency"),
        data.get("category"),
        pdf_path
    )

    try:
        cursor.execute(query, values)
        connection.commit()
        print("Saved to database")
    except mysql.connector.Error:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
