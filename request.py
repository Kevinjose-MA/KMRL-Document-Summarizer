import requests

# URL of your FastAPI upload endpoint
url = "http://127.0.0.1:8000/upload/"

# Path to the PDF file
file_path = r"D:\llm\KMRL_DocSummarizer\HR Policy Manual 2023-1-100.pdf"

# Open the file in binary mode and send it
with open(file_path, "rb") as f:
    files = {"file": (file_path.split("\\")[-1], f, "application/pdf")}
    response = requests.post(url, files=files)

# Print response from server
print("Status Code:", response.status_code)
print("Response:", response.text)
