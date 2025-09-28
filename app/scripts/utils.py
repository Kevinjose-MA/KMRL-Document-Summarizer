# app/scripts/utils.py
import os

def list_files(folder, extensions=None):
    files = []
    for f in os.listdir(folder):
        if extensions is None or os.path.splitext(f)[1].lower() in extensions:
            files.append(os.path.join(folder, f))
    return files

def save_text_file(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
