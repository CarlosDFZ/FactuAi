# FactuAI
AI-powered invoice processing and data extraction system

FactuAI is a Python project that processes invoice PDF files, extracts key information with AI, and stores the structured results in a MySQL database. It is designed to automate invoice handling, reduce manual data entry, and avoid duplicate records by validating invoice UUIDs before and after AI extraction.

## Overview

The project follows a simple pipeline:

1. Read PDF invoices from the `invoices/` folder
2. Extract raw text from each PDF
3. Detect the invoice UUID for deduplication
4. Send invoice text to the OpenAI API for structured JSON extraction
5. Save the extracted JSON locally
6. Insert validated invoice data into MySQL

## Use Case

FactuAI helps automate invoice processing for workflows that would otherwise require repetitive manual review and data entry. By extracting structured invoice data from PDF files and storing it in MySQL, the project makes it easier to organize invoice records, support reporting, and prepare financial data for further analysis.

## Features

- Extract text from PDF invoices using PyMuPDF
- Convert invoice content into structured JSON using the OpenAI API
- Store processed invoice data in MySQL
- Prevent duplicate invoices using UUID-based deduplication
- Save processed JSON files locally in `data/json/`
- Use environment variables for configuration with `.env`
- Automatically create the database and invoices table if they do not exist

## Deduplication Strategy

- The system attempts to extract the invoice UUID directly from the PDF text before calling the OpenAI API
- If the UUID is found and already exists in MySQL, the invoice is skipped immediately
- If the UUID is not found before AI extraction, the system validates the UUID again after structured data is returned by the API
- This approach reduces unnecessary API usage and helps prevent duplicate invoice records in the database

## Tech Stack

- Python
- MySQL
- OpenAI API
- VS Code
- PyMuPDF
- `mysql-connector-python`
- `python-dotenv`

## Requirements

Dependencies can be installed manually with:

```bash
pip install openai python-dotenv pymupdf mysql-connector-python
```

## Project Structure

```text
FactuAI/
├── config.py
├── db.py
├── main.py
├── setup_database.py
├── .env.example
├── .gitignore
├── invoices/
├── data/
│   └── json/
└── modules/
    ├── __init__.py
    ├── ai_extractor.py
    ├── db_insert.py
    ├── pdf_reader.py
    └── uuid_extractor.py
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/factuai.git
cd factuai
```

### 2. (Optional but recommended) Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

On Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install openai python-dotenv pymupdf mysql-connector-python
```

## Environment Setup

Create a `.env` file in the project root based on `.env.example`. The `.env` file is not committed to GitHub, and `.env.example` is included as a safe template for local setup.

```bash
cp .env.example .env
```

Example:

```env
OPENAI_API_KEY=your_openai_api_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=factuai_db
```

## How To Run

### 1. Add invoice PDFs

Place the invoice files you want to process inside the `invoices/` folder.

### 2. Run the project

```bash
python main.py
```

### 3. What happens during execution

- The database setup runs automatically
- Each PDF in `invoices/` is processed
- UUIDs are checked to prevent duplicates
- Extracted JSON files are saved to `data/json/`
- Valid invoice data is inserted into MySQL

## Database Schema

The project creates an `invoices` table with fields such as:

- `uuid`
- `invoice_date`
- `supplier`
- `description`
- `subtotal`
- `taxes`
- `total`
- `currency`
- `category`
- `pdf_path`
- `created_at`

## Example Output

Example structured JSON generated from an invoice:

```json
{
  "uuid": "123E4567-E89B-12D3-A456-426614174000",
  "invoice_date": "2026-04-24",
  "supplier": "office depot",
  "description": "office supplies purchase",
  "subtotal": 1000.00,
  "taxes": 160.00,
  "total": 1160.00,
  "currency": "MXN",
  "category": "office supplies"
}
```

Example console flow:

```text
Processing invoice:
invoices/sample_invoice.pdf
--------------------------------------------------
UUID found: 123E4567-E89B-12D3-A456-426614174000
Extracted JSON:
{...}
JSON saved: data/json/sample_invoice.json
Saved to database

All invoices processed.
```

## Notes

- The project expects PDF invoices inside the `invoices/` directory
- Processed JSON files are stored in `data/json/`
- Duplicate invoices are skipped when the UUID already exists in the database
- If required fields are missing, the invoice is skipped

## .gitignore

This repository is configured to exclude local and generated files from version control, including:

- `.env`
- `invoices/`
- `data/json/*.json`
- virtual environments
- Python cache files
- VS Code settings

This keeps sensitive data, raw invoice files, and generated JSON outputs out of GitHub. No real API keys, passwords, invoice data, or other sensitive information should be committed.

## Future Improvements

- Add a `requirements.txt` file for dependency management
- Add logging and error reporting
- Add unit tests
- Add Docker support
- Support batch monitoring for newly added invoices

## License

This project is available for personal or commercial use. Add a license file if you plan to publish it publicly on GitHub.
