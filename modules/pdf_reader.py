import fitz #PyMuPDF

def extract_text_from_pdf(pdf_path):
    text = ""
    
    with fitz.open(pdf_path) as document:
        for page in document:
            text += page.get_text()
            
    return text