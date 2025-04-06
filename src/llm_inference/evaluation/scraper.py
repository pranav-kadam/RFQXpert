import os
import sys
import json
import logging
import asyncio
import re
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from fpdf import FPDF

# --- Helper to remove emojis and non-latin characters ---
def remove_emojis(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(_name_)

# --- Load ENV ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("Missing GEMINI_API_KEY in environment.")
    sys.exit(1)
genai.configure(api_key=GEMINI_API_KEY)

# --- Model ---
model = genai.GenerativeModel("gemini-2.0-flash")

# --- Load Company Profile ---
project_root = os.path.abspath(os.path.join(os.path.dirname(_file_), "../../../"))
company_data_path = os.path.join(project_root, "data", "companydata.json")
try:
    with open(company_data_path, "r") as f:
        company_data = json.load(f)
        company_data_str = json.dumps(company_data, indent=2)
except Exception as e:
    logger.error(f"Error loading company profile: {e}")
    sys.exit(1)

# --- PDF Generator ---
def generate_pdf_report(matching, filename="relevant_tenders_report.pdf"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(200, 10, txt="Relevant Tender Report", ln=True, align="C")
    pdf.ln(10)

    for i, r in enumerate(matching, start=1):
        t = r["tender"]
        pdf.set_font("Arial", style='B', size=12)
        pdf.cell(200, 10, txt=f"[{i}] {remove_emojis(t['title'])} ({t['ref_no']})", ln=True)

        pdf.set_font("Arial", size=11)
        pdf.cell(200, 10, txt=f"Organization : {remove_emojis(t['organization'])}", ln=True)
        pdf.cell(200, 10, txt=f"Due Date     : {t['due_date']}", ln=True)
        pdf.cell(200, 10, txt=f"Relevance Score : {r.get('score', 'N/A')}", ln=True)
        pdf.multi_cell(0, 10, txt=f"Reason           : {remove_emojis(r.get('reason', 'No reason provided.'))}")

        pdf.cell(200, 10, txt=f"Recommendations:", ln=True)
        for rec in r.get("recommendations", []):
            pdf.multi_cell(0, 10, txt=f"    - {remove_emojis(rec)}")  # Updated bullet to be ASCII-safe
        pdf.ln(5)

    pdf.output(filename)
    logger.info(f"PDF report generated: {filename}")

# --- Tender Table Detector ---
def find_real_tender_table(soup):
    tables = soup.find_all("table")
    for idx, table in enumerate(tables):
        rows = table.find_all("tr")
        for row in rows[:2]:
            text = row.get_text(" ", strip=True).lower()
            if (
                "tender title" in text
                and "organisation" in text
                and ("closing date" in text or "due date" in text)
            ):
                logger.info(f"Detected Tender Table #{idx}")
                return table
    return None

# --- Scrape Tender Data ---
def scrape_tenders(limit=10):
    try:
        url = "https://eprocure.gov.in/eprocure/app?action=latestActiveTenders"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")

        table = find_real_tender_table(soup)
        if not table:
            logger.warning("Could not find tender table.")
            return []

        tenders = []
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 6:
                tender = {
                    "organization": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "ref_no": cols[2].get_text(strip=True),
                    "due_date": cols[5].get_text(strip=True),
                }
                tenders.append(tender)
                if len(tenders) >= limit:
                    break

        return tenders
    except Exception as e:
        logger.error(f"Error scraping tenders: {e}")
        return []

# --- Prompt Builder ---
def build_prompt(company: str, tender: dict) -> str:
    return f"""
You are TenderScout, an expert tender evaluation assistant.

Company Profile:
{company}

Evaluate the following tender:

Organization: {tender['organization']}
Title: {tender['title']}
Reference No: {tender['ref_no']}
Due Date: {tender['due_date']}

Is this relevant to the company? Reply in JSON:
{{
  "is_relevant": true/false,
  "score": float between 0 and 1,
  "reason": string,
  "recommendations": [string]
}}
"""

# --- Parse Gemini JSON ---
def parse_json_response(text: str) -> dict:
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(match.group()) if match else {"error": "Invalid format"}
    except Exception as e:
        return {"error": str(e)}

def send_pdf_to_server(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            # Replace this with your actual frontend domain
            response = requests.post('http://localhost:3000/api/upload-pdf', files=files)
            if response.status_code == 200:
                logger.info("✅ PDF successfully sent to frontend")
            else:
                logger.error(f"❌ Failed to send PDF. Status: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Error sending PDF: {e}")


# --- Main Runner ---
async def run_evaluation():
    tenders = scrape_tenders(limit=10)
    if not tenders:
        logger.warning("No tenders to evaluate.")
        return

    results = []
    for tender in tenders:
        prompt = build_prompt(company_data_str, tender)
        try:
            response = model.generate_content(prompt)
            result = parse_json_response(response.text)
            result["tender"] = tender
            results.append(result)
        except Exception as e:
            results.append({"error": str(e), "tender": tender})

    matching = [r for r in results if r.get("is_relevant", False)]

    if not matching:
        print("\n🚫 No relevant tenders found.\n")
        return

    print("\n📌 Relevant Tenders:\n")
    for i, r in enumerate(matching, start=1):
        t = r["tender"]
        print(f"🔹 [{i}] {t['title']} ({t['ref_no']})")
        print(f"    🏢 Organization : {t['organization']}")
        print(f"    📅 Due Date     : {t['due_date']}")
        print(f"    ✅ Relevance Score : {r.get('score', 'N/A')}")
        print(f"    📝 Reason           : {r.get('reason', 'No reason provided.')}")
        print(f"    💡 Recommendations  :")
        for rec in r.get("recommendations", []):
            print(f"       ➤ {rec}")
        print("-" * 70)

    pdf_filename = "relevant_tenders_report.pdf"
    generate_pdf_report(matching, pdf_filename)
    send_pdf_to_server(pdf_filename)

if _name_ == "_main_":
    asyncio.run(run_evaluation())