# scripts/extraction.py
import docx2txt
import pdfplumber
from app.scripts.utils import save_text_file
import os

def extract_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def extract_docx(file_path):
    return docx2txt.process(file_path)

def extract_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def extract_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        return extract_txt(file_path)
    elif ext == ".docx":
        return extract_docx(file_path)
    elif ext == ".pdf":
        return extract_pdf(file_path)
    else:
        return ""
