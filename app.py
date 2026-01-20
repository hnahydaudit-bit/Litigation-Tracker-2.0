import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import google.generativeai as genai
import tempfile
import os
import json
import re

# ===============================
# 🔑 GEMINI CONFIG (STABLE MODEL)
# ===============================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

MODEL_NAME = "models/gemini-1.5-flash"  # ✅ STREAMLIT SAFE

# ===============================
# 🎨 PAGE SETUP
# ===============================
st.set_page_config(page_title="GST Litigation Tracker", page_icon="📂", layout="wide")
st.title("📂 GST Litigation Tracker (Prototype)")

# ===============================
# 📄 PDF TEXT EXTRACTION
# ===============================
def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text")
    return text.strip()

# ===============================
# 🤖 AI EXTRACTION
# ===============================
def extract_notice_details(text, source_name):
    prompt = f"""
You are a GST litigation expert.

Extract information ONLY from the document text provided.
Do NOT guess. Do NOT create dummy data.

Return ONE JSON object with the following keys:

- Entity Name
- GSTIN
- Type of Notice / Order (System Update)
- Description
- Issues & Tax Amounts
- Ref ID
- Date Of Issuance
- Due Date
- Case ID
- Notice Type (ASMT-10 / ADT-01 / SCN / Appeal etc.)
- Financial Year
- Total Demand Amount as per Notice
- DIN No
- Officer Name
- Designation
- Area Division
- Tax Amount
- Interest
- Penalty
- Source

### IMPORTANT RULES FOR "Issues & Tax Amounts":
- Capture ALL issues mentioned in the notice
- Each issue should be a short line
- Mention ONLY the TAX amount per issue
- Ignore interest, penalty, para refs
- Format like:
  Issue 1 – ₹xxxxx
  Issue 2 – ₹xxxxx
  Issue 3 – ₹xxxxx
- If amounts are not issue-wise, mention "Amount not bifurcated"

If a field is not found, keep it blank.
Return ONLY valid JSON. No explanation.

Document Text:
{text}
"""

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)

    raw_text = response.text.strip()

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return None

    data = json.loads(match.group(0))
    data["Source"] = source_name
    return data

# ===============================
# 📤 FILE UPLOAD
# ===============================
uploaded_files = st.file_uploader(
    "📤 Upload GST Notice PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

# ===============================
# 🚀 PROCESS
# ===============================
if uploaded_files:
    st.info("⏳ Extracting notice details… Please wait")

    results = []

    for file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        text = extract_text_from_pdf(tmp_path)
        os.remove(tmp_path)

        if text.strip():
            # HARD LIMIT → avoids quota & timeout
            extracted = extract_notice_details(text[:6000], file.name)
            if extracted:
                results.append(extracted)

    if not results:
        st.error("❌ No data could be extracted.")
    else:
        # ===============================
        # 📊 DATAFRAME
        # ===============================
        columns = [
            "Entity Name",
            "GSTIN",
            "Type of Notice / Order (System Update)",
            "Description",
            "Issues & Tax Amounts",
            "Ref ID",
            "Date Of Issuance",
            "Due Date",
            "Case ID",
            "Notice Type (ASMT-10 / ADT-01 / SCN / Appeal etc.)",
            "Financial Year",
            "Total Demand Amount as per Notice",
            "DIN No",
            "Officer Name",
            "Designation",
            "Area Division",
            "Tax Amount",
            "Interest",
            "Penalty",
            "Source"
        ]

        df = pd.DataFrame(results)
        df = df.reindex(columns=columns)

        st.success("✅ Extraction completed successfully!")
        st.dataframe(df, use_container_width=True)

        # ===============================
        # 📥 EXCEL DOWNLOAD
        # ===============================
        output_file = "GST_Litigation_Tracker_Output.xlsx"
        df.to_excel(output_file, index=False)

        with open(output_file, "rb") as f:
            st.download_button(
                label="📥 Download Excel",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
