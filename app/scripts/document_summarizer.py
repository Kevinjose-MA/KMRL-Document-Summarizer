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
You are an expert summarizer with domain knowledge across HR, legal, technical, and business documents. 
Your task is to generate a clear, professional, and structured summary of the given document or section. 

Guidelines:
- Identify and highlight the most important information: key points, responsibilities, actions, deadlines, 
  decisions, or achievements.
- Use concise bullet points where appropriate, but also provide short cohesive paragraphs for context.
- Adapt writing style based on the content type:
  • Resume → emphasize skills, experience, and accomplishments. 
  • HR/Policy → highlight policies, roles, procedures, compliance details, and responsibilities.
  • Technical → capture processes, methods, results, limitations, and recommendations.
  • General/Business → focus on goals, outcomes, benefits, and next steps.
- Do not invent or assume facts that are not explicitly stated in the text.
- Preserve the logical flow of the original content but remove redundancy and filler.
- Keep the summary professional, precise, and easy to read for stakeholders.

Document/Section content:
{section_text}
"""
    for attempt in range(retries):
        try:
            response = gemini_model.generate_content(
                contents=[{"role": "user", "parts": [prompt]}],
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.7,
                    "max_output_tokens": 800
                }
            )
            summary = ""
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if candidate.content.parts:
                    summary = candidate.content.parts[0].text.strip()
            if summary:
                return summary
            print(f"⚠ LLM returned empty summary. Retrying {attempt+1}/{retries}...")
        except Exception as e:
            if "quota" in str(e).lower() and switch_to_next_key():
                continue
            print(f"❌ Error in summarize_section: {e}")
        time.sleep(delay)
    return "⚠ Summary failed after retries."


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
You are an expert summarizer with strong domain knowledge across HR, legal, technical, 
business, and professional documents. Your task is to generate a cohesive, professional, 
and highly detailed final summary of the entire document based on the section-wise summaries provided. 

⚠ Important Handling:
- If any section contains an error message such as "⚠ Summary failed after retries." 
  or incomplete text, ignore that section completely in the final summary. 
- Only use valid and meaningful content.

Word Count Requirements:
- HR-related documents → Aim for ~4000 words.
- Resume-related documents → Aim for ~2000 words.
- Business or general corporate documents → Aim for ~5000 words.
- If document type is unclear → Default to ~200 words.

Guidelines for the Final Summary:
- Carefully read all section summaries and preserve their logical order and flow.
- Consolidate overlapping information and eliminate trivial or repetitive details.
- Highlight essential elements such as key points, responsibilities, actions, 
  deadlines, incentives, inclusions, exclusions, claim limits, benefits, 
  preventive care, and strategic insights (if relevant).
- Structure the output in a professional and readable format:
  • Use concise bullet points for actionable items, responsibilities, or conditions.
  • Use short, well-structured paragraphs for context, background, and takeaways.
- Maintain a professional, precise, and stakeholder-friendly tone, 
  as if writing an official report or executive-level summary.
- Adapt language naturally to the type of document (HR policy, resume, 
  business strategy, technical manual, or general policy).
- Do not fabricate or assume facts beyond the provided content; 
  if assumptions must be noted, explicitly label them as "Assumptions".
- Ensure the result is cohesive, comprehensive, and aligned with the required word count.

Section-wise summaries (cleaned input):
{merged_summary}
"""
    try:
        final_response = gemini_model.generate_content(
            contents=[{"role": "user", "parts": [final_prompt]}],
            generation_config={"temperature":0.3, "top_p":0.8, "max_output_tokens":800 ,"candidate_count": 1}
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
