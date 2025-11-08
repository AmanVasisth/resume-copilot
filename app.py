import streamlit as st
from io import BytesIO
from docx import Document
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from huggingface_hub import InferenceClient
import traceback

DEBUG = True  # Turn False before public deployment

# ----------------------------
# 🧠 Model Setup with Auto Fallback
# ----------------------------
def get_hf_client(model_name):
    return InferenceClient(model_name, token=st.secrets["HUGGINGFACE_API_TOKEN"])

# Primary model (Falcon)
try:
    client = get_hf_client("tiiuae/falcon-7b-instruct")
    client.text_generation("Hello", max_new_tokens=1)
    MODEL_TYPE = "text-generation"
    CURRENT_MODEL = "Falcon-7B"
except Exception:
    st.warning("⚠️ Falcon-7B unavailable — switching to Flan-T5 (free fallback).")
    client = get_hf_client("google/flan-t5-large")
    MODEL_TYPE = "text2text-generation"
    CURRENT_MODEL = "Flan-T5"

# ----------------------------
# 🎨 Streamlit Page Setup
# ----------------------------
st.set_page_config(page_title="ResumeCopilot 🇮🇳", page_icon="📄", layout="wide")
st.title("📄 ResumeCopilot – AI Resume & Cover Letter Builder 🇮🇳")
st.write("Create or update your **ATS-friendly resume & cover letter** instantly using Hugging Face models.")
st.markdown("---")

# ----------------------------
# 🧾 Candidate Details
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
# 📤 Upload Old Resume
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
# 🚀 Generate Resume & Cover Letter
# ----------------------------
if st.button("🚀 Generate New Resume & Cover Letter"):
    with st.spinner("Creating your new AI-optimized resume... please wait ⏳"):
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
        1. Create a new, modern, ATS-friendly resume.
        2. Include Summary, Experience, Education, Skills, Achievements.
        3. Write a short professional cover letter at the end.
        """

        try:
            # ---------- MAIN MODEL ----------
            if MODEL_TYPE == "text-generation":
                response = client.text_generation(prompt, max_new_tokens=800, temperature=0.7, top_p=0.9)
                result = response
            else:
                response = client.text2text_generation(prompt)
                result = response[0]["generated_text"] if isinstance(response, list) else response

        except Exception as e1:
            st.warning("⚠️ Primary model failed. Retrying with Flan-T5 (text2text-generation)...")
            try:
                flan_client = get_hf_client("google/flan-t5-large")
                response = flan_client.text2text_generation(prompt)
                result = response[0]["generated_text"] if isinstance(response, list) else response
                CURRENT_MODEL = "Flan-T5"
            except Exception as e2:
                st.warning("⚠️ Flan-T5 failed. Retrying with Mistral-7B (text-generation)...")
                mistral_client = get_hf_client("mistralai/Mistral-7B-v0.1")
                response = mistral_client.text_generation(prompt, max_new_tokens=700)
                result = response
                CURRENT_MODEL = "Mistral-7B"

        # ----------------------------
        # ✅ Display Output
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
        # 💾 Download Options
        # ----------------------------
        text_bytes = result.encode("utf-8")

        # Word File
        docx_buffer = BytesIO()
        doc = Document()
        doc.add_heading("Resume & Cover Letter", 0)
        for line in result.split("\n"):
            doc.add_paragraph(line)
        doc.save(docx_buffer)
        docx_buffer.seek(0)

        # PDF File
        pdf_buffer = BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter
        y = height - 50
        for line in result.split("\n"):
            pdf.drawString(50, y, line)
            y -= 15
            if y < 50:
                pdf.showPage()
                y = height - 50
        pdf.save()
        pdf_buffer.seek(0)

        st.download_button("📄 Download as Text", data=text_bytes, file_name="ResumeCopilot.txt")
        st.download_button("📝 Download as Word (.docx)", data=docx_buffer, file_name="ResumeCopilot.docx")
        st.download_button("📕 Download as PDF", data=pdf_buffer, file_name="ResumeCopilot.pdf")

        if DEBUG:
            st.info(f"Model Used → {CURRENT_MODEL}")

    st.markdown("---")

st.caption("✨ Built with ❤️ in India | ResumeCopilot.ai (Free Hugging Face Edition)")
