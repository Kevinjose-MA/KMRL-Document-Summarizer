import os
import re
import time
import fitz  # PyMuPDF for PDFs
import docx
import google.generativeai as genai

# =========================
# Gemini API Keys (Primary + Fallbacks)
# =========================
GEMINI_API_KEYS = [
    "AIzaSyCEscXcGhwjkfAAApGDqj93JlMrnBzvWow",
    "AIzaSyDSDBgtVi0GxXMYh0o48aJJkoNc3dlibXs",
    "AIzaSyBpeVnD4pVLYsv3AiAK_vAYrhjU06dR3AY"
]

current_key_index = 0
genai.configure(api_key=GEMINI_API_KEYS[current_key_index])
gemini_model = genai.GenerativeModel("models/gemini-2.5-flash")


# =========================
# File reading utilities
# =========================
def read_pdf(path: str) -> str:
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text


def read_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_document(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return read_pdf(path)
    elif ext in [".docx", ".doc"]:
        return read_docx(path)
    elif ext == ".txt":
        return read_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# =========================
# Hybrid Section Detection
# =========================
def split_into_sections(text: str) -> list:
    """
    Split text into sections using headings or spacing.
    """
    pattern = re.compile(r'(^[A-Z][A-Z\s]{2,}:?$)', re.MULTILINE)
    splits = pattern.split(text)
    
    sections = []
    if splits:
        current_heading = "Introduction"
        buffer = ""
        for part in splits:
            part = part.strip()
            if pattern.match(part):
                if buffer:
                    sections.append((current_heading, buffer.strip()))
                current_heading = part
                buffer = ""
            else:
                buffer += part + "\n"
        if buffer:
            sections.append((current_heading, buffer.strip()))
    else:
        raw_sections = text.split("\n\n")
        sections = [(f"Section {i+1}", sec.strip()) for i, sec in enumerate(raw_sections)]
    return sections


# =========================
# Gemini summarization with retry + fallback
# =========================
def switch_to_next_key():
    global current_key_index, gemini_model
    if current_key_index + 1 < len(GEMINI_API_KEYS):
        current_key_index += 1
        print(f"🔑 Switching to fallback API key #{current_key_index + 1}")
        genai.configure(api_key=GEMINI_API_KEYS[current_key_index])
        gemini_model = genai.GenerativeModel("models/gemini-2.5-flash")
        return True
    return False


def summarize_section(section_text: str, retries: int = 3, delay: int = 5) -> str:
    
    if len(section_text.strip().split()) < 10:
        return ""
    
    prompt = f"""
You are an expert summarizer. Summarize the following document or section clearly and professionally:
- Highlight key points, actions, responsibilities, deadlines, and important details.
- Include concise bullet points where appropriate.
- Preserve context and meaning; do not invent facts.
- Adapt style to the type of document (resume, HR, technical, or general business).
- Keep the summary readable and structured.

Document/Section content:
{section_text}
"""
    for attempt in range(retries):
        try:
            response = gemini_model.generate_content(
                contents=[{"role": "user", "parts": [prompt]}],
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "max_output_tokens": 500
                }
            )
            summary = ""
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if candidate.content.parts:
                    summary = candidate.content.parts[0].text.strip()
            if summary:
                return summary
            print(f"⚠️ LLM returned empty summary. Retrying {attempt+1}/{retries}...")
        except Exception as e:
            if "quota" in str(e).lower() and switch_to_next_key():
                continue
            print(f"❌ Error in summarize_section: {e}")
        time.sleep(delay)
    return "⚠️ Summary failed after retries."


# =========================
# Hybrid Section-aware Summarization
# =========================
def summarize_text_by_sections(text: str) -> str:
    sections = split_into_sections(text)
    section_summaries = []
    for heading, content in sections:
        print(f"📝 Summarizing section: {heading}")
        summary = summarize_section(content)
        section_summaries.append(f"## {heading}\n{summary}\n")
    
    merged_summary = "\n".join(section_summaries)

    final_prompt = f"""
You are an expert summarizer. Using the section-wise summaries provided below,
create a professional, concise, and well-structured final summary in approximately 200 words.

Guidelines:
- Read all section summaries carefully.
- Preserve the logical flow and order of sections.
- Include key points, actions, responsibilities, deadlines, and incentives.
- Highlight important inclusions, exclusions, claim limits, benefits, and preventive care.
- Merge redundant points and remove trivial information for clarity.
- Maintain a precise, professional, and readable style suitable for an official report.
- Avoid introducing incorrect facts; clearly indicate assumptions only if necessary.
- Produce a cohesive summary that captures the essence of the entire document, not just bullet points.

Section-wise summaries:
{merged_summary}
"""
    try:
        final_response = gemini_model.generate_content(
            contents=[{"role": "user", "parts": [final_prompt]}],
            generation_config={"temperature":0.3, "top_p":0.8, "max_output_tokens":800}
        )
        final_summary = ""
        if hasattr(final_response, "candidates") and final_response.candidates:
            candidate = final_response.candidates[0]
            if candidate.content.parts:
                final_summary = candidate.content.parts[0].text.strip()
        if final_summary:
            return final_summary
    except Exception as e:
        print(f"❌ Final merge summarization failed: {e}")

    return merged_summary


# =========================
# Summarize Document
# =========================
def summarize_document(path: str) -> str:
    text = read_document(path)
    return summarize_text_by_sections(text)


# =========================
# Save Summary
# =========================
def save_summary(summary_text: str, base_filename: str, output_folder: str) -> str:
    os.makedirs(output_folder, exist_ok=True)
    summary_path = os.path.join(output_folder, f"{base_filename}_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary_text)
    return summary_path
