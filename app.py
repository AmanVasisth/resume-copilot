import streamlit as st
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from huggingface_hub import InferenceClient
import json

# ----------------------------
# 🌟 Page Config
# ----------------------------
st.set_page_config(page_title="ResumeCopilot 🇮🇳", page_icon="📄", layout="wide")
st.title("📄 ResumeCopilot – AI Resume & Cover Letter Builder 🇮🇳")
st.write("Create or update your **ATS-friendly resume & cover letter** instantly using Hugging Face free models.")
st.markdown("---")

# ----------------------------
# ⚙️ Universal Safe Model Caller
# ----------------------------
def safe_generate(model_name, prompt):
    """Universal Hugging Face text generator for all models."""
    try:
        client = InferenceClient(token=st.secrets["HUGGINGFACE_API_TOKEN"])
        response = client.post_json(
            f"https://api-inference.huggingface.co/models/{model_name}",
            {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 700,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            },
        )
        # Handle both list and dict responses
        if isinstance(response, list) and len(response) > 0:
            return response[0].get("generated_text", str(response))
        elif isinstance(response, dict):
            return response.get("generated_text", str(response))
        else:
            return str(response)
    except Exception as e:
        raise RuntimeError(f"Model {model_name} failed: {str(e)}")

# ----------------------------
# 🧾 Candidate Information
# ----------------------------
st.subheader("🧾 Candidate Details")

col1, col2 = st.columns(2)
with col1:
    full_name = st.text_input("👤 Full Name")
    email = st.text_input("📧 Email Address")
    phone = st.text_input("📞 Phone Number")

with col2:
    linkedin = st.text_input("🔗 LinkedIn Profile (optional)")
    job_title = st.text_input("💼 Job Title")
    experience = st.text_input("⏳ Years of Experience")

skills = st.text_area("🧠 Key Skills (comma-separated)")
education = st.text_area("🎓 Education Background")
achievements = st.text_area("🏆 Achievements (optional)")
job_description = st.text_area("📋 Job Description (optional)", placeholder="Paste a job description here to tailor your resume...")

st.markdown("---")

# ----------------------------
# 📤 Upload Past Resume
# ----------------------------
st.subheader("📤 Upload Your Old Resume (optional)")
uploaded_file = st.file_uploader("Upload your previous resume (PDF or DOCX)", type=["pdf", "docx"])
past_resume_text = ""

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            past_resume_text += page.extract_text() + "\n"
    else:
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            past_resume_text += para.text + "\n"
    st.success("✅ Resume uploaded successfully!")

st.markdown("---")

# ----------------------------
# 🚀 Generate Resume
# ----------------------------
if st.button("🚀 Generate Resume & Cover Letter"):
    with st.spinner("Crafting your perfect resume with AI ✨... please wait ⏳"):

        prompt = f"""
        You are ResumeCopilot, an AI resume and cover letter expert.

        Candidate Details:
        Name: {full_name}
        Email: {email}
        Phone: {phone}
        LinkedIn: {linkedin}
        Job Title: {job_title}
        Experience: {experience} years
        Skills: {skills}
        Education: {education}
        Achievements: {achievements}

        Job Description: {job_description}

        Past Resume (if any): {past_resume_text}

        Task:
        1. Create a new, modern, ATS-friendly resume tailored to the job description.
        2. Include sections: Summary, Experience, Education, Skills, Achievements.
        3. Write a short professional cover letter at the end.
        4. Keep tone professional and optimized for Indian recruiters.
        """

        try:
            st.info("🦅 Using Falcon-7B model...")
            result = safe_generate("tiiuae/falcon-7b-instruct", prompt)
            CURRENT_MODEL = "Falcon-7B"
        except Exception:
            st.warning("⚠️ Falcon-7B failed. Retrying with Flan-T5...")
            try:
                result = safe_generate("google/flan-t5-large", prompt)
                CURRENT_MODEL = "Flan-T5"
            except Exception:
                st.warning("⚠️ Flan-T5 failed. Retrying with Mistral-7B...")
                result = safe_generate("mistralai/Mistral-7B-v0.1", prompt)
                CURRENT_MODEL = "Mistral-7B"

        # ----------------------------
        # ✅ Display Result
        # ----------------------------
        st.success(f"✅ Resume & Cover Letter Generated Successfully! (Model Used: {CURRENT_MODEL})")

        with st.expander("📋 Preview Resume & Cover Letter", expanded=True):
            st.markdown(
                f"""
                <div style='background-color:#f9f9f9; padding:20px; border-radius:10px; line-height:1.6;'>
                <pre style='white-space:pre-wrap; font-family:Roboto, sans-serif; color:#333;'>{result}</pre>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ----------------------------
        # 💾 Downloads (PDF, DOCX, TXT)
        # ----------------------------
        text_bytes = result.encode("utf-8")

        # Word
        docx_buffer = BytesIO()
        doc = Document()
        doc.add_heading("Resume & Cover Letter", 0)
        for line in result.split("\n"):
            doc.add_paragraph(line)
        doc.save(docx_buffer)
        docx_buffer.seek(0)

        # PDF
        pdf_buffer = BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter
        y = height - 50
        for line in result.split("\n"):
            pdf.drawString(50, y, line[:1000])
            y -= 15
            if y < 50:
                pdf.showPage()
                y = height - 50
        pdf.save()
        pdf_buffer.seek(0)

        # Buttons
        st.download_button("📄 Download as Text", data=text_bytes, file_name="ResumeCopilot.txt")
        st.download_button("📝 Download as Word (.docx)", data=docx_buffer, file_name="ResumeCopilot.docx")
        st.download_button("📕 Download as PDF", data=pdf_buffer, file_name="ResumeCopilot.pdf")

st.caption("✨ Built with ❤️ in India | ResumeCopilot.ai (Free Hugging Face Edition)")
