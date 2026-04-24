import mysql.connector
from config import DB_CONFIG


def setup_database():
    connection = mysql.connector.connect(
        host=DB_CONFIG["host"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )

    cursor = connection.cursor()

    db_name = DB_CONFIG["database"]
    print("Using database:", db_name)

    # Verificar si la base existe
    cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
    result = cursor.fetchone()

    if result:
        print(f"Database '{db_name}' already exists")
    else:
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"Database '{db_name}' created")

    # Usar la base
    cursor.execute(f"USE {db_name}")

    # Crear tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            uuid VARCHAR(100) UNIQUE,
            invoice_date DATE,
            supplier VARCHAR(255),
            description TEXT,
            subtotal DECIMAL(12,2),
            taxes DECIMAL(12,2),
            total DECIMAL(12,2),
            currency VARCHAR(10),
            category VARCHAR(100),
            pdf_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("Table 'invoices' is ready")

    connection.commit()
    cursor.close()
    connection.close()


if __name__ == "__main__":
    setup_database()