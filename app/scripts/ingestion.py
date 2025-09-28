# app/scripts/ingestion.py
import os
import requests
from urllib.parse import urlparse
from app.scripts.utils import save_text_file

RAW_FOLDER = "app/data/raw/"

os.makedirs(RAW_FOLDER, exist_ok=True)

def save_file_from_url(url):
    """
    Download a file from a URL and save it to RAW_FOLDER
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            filename = "downloaded_file"
        file_path = os.path.join(RAW_FOLDER, filename)
        with open(file_path, "wb") as f:
            f.write(response.content)
        return file_path
    except Exception as e:
        return f"Error downloading {url}: {str(e)}"


def ingest_local_file(file_path):
    """
    Copy a local file to RAW_FOLDER
    """
    try:
        if not os.path.exists(file_path):
            return f"File {file_path} does not exist."
        filename = os.path.basename(file_path)
        dest_path = os.path.join(RAW_FOLDER, filename)
        with open(file_path, "rb") as src, open(dest_path, "wb") as dst:
            dst.write(src.read())
        return dest_path
    except Exception as e:
        return f"Error ingesting {file_path}: {str(e)}"


def ingest_files(file_paths):
    """
    Ingest multiple local files or URLs
    """
    results = []
    for f in file_paths:
        if f.startswith("http://") or f.startswith("https://"):
            results.append(save_file_from_url(f))
        else:
            results.append(ingest_local_file(f))
    return results
