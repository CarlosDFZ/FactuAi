from db import get_connection

def invoice_exists(uuid):
    if not uuid:
        return False

    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT id FROM invoices WHERE uuid = %s LIMIT 1"
    cursor.execute(query, (uuid,))

    result = cursor.fetchone()

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

    except Exception as e:
        if "Duplicate entry" in str(e):
            print("Duplicate invoice detected")
        else:
            print("Database error:", e)

    cursor.close()
    connection.close()