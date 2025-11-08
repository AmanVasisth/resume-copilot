import streamlit as st
from openai import OpenAI
from io import BytesIO
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# App configuration
st.set_page_config(page_title="ResumeCopilot 🇮🇳", page_icon="📄", layout="wide")

# Title & Description
st.title("📄 ResumeCopilot – AI Resume & Cover Letter Builder 🇮🇳")
st.write("Create **professional, ATS-friendly** resumes & cover letters instantly with AI – customized for the Indian job market 🇮🇳.")

st.markdown("---")

# --- USER INPUT FORM ---
st.subheader("🧾 Candidate Information")

col1, col2 = st.columns(2)

with col1:
    full_name = st.text_input("👤 Full Name")
    email = st.text_input("📧 Email Address")
    phone = st.text_input("📞 Contact Number")

with col2:
    linkedin = st.text_input("🔗 LinkedIn Profile URL (optional)")
    job_title = st.text_input("💼 Job Title")
    experience = st.text_input("⏳ Years of Experience")

skills = st.text_area("🧠 Key Skills (comma-separated)")
education = st.text_area("🎓 Education Background")
achievements = st.text_area("🏆 Achievements (optional)")
job_description = st.text_area("📋 Job Description (optional)", placeholder="Paste a job description here to tailor your resume...")

st.markdown("---")

# --- GENERATE RESUME ---
if st.button("🚀 Generate Resume & Cover Letter"):
    with st.spinner("Creating your personalized resume... please wait ⏳"):

        # Prompt for OpenAI
        prompt = f"""
        You are ResumeCopilot, an AI assistant that builds modern, ATS-optimized resumes and cover letters.
        Generate a professional resume and cover letter for the following candidate:
        
        Candidate Details:
        - Full Name: {full_name}
        - Email: {email}
        - Phone: {phone}
        - LinkedIn: {linkedin}
        - Job Title: {job_title}
        - Experience: {experience} years
        - Skills: {skills}
        - Education: {education}
        - Achievements: {achievements}
        
        Job Description (optional): {job_description}

        Please:
        1. Tailor the resume to the job description if provided.
        2. Format clearly with sections: Summary, Experience, Education, Skills, Achievements, Cover Letter.
        3. Keep tone professional and suitable for Indian job market.
        4. Use clean bullet points and concise wording.
        """

        try:
            # Generate Resume
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.choices[0].message.content.strip()

            # Display Preview in Card
            st.success("✅ Resume & Cover Letter Generated Successfully!")

            with st.expander("📋 Preview Resume & Cover Letter", expanded=True):
                st.markdown(
                    f"""
                    <div style='background-color:#f9f9f9; padding:20px; border-radius:10px; line-height:1.6;'>
                    <pre style='white-space:pre-wrap; font-family:Roboto, sans-serif; color:#333;'>{result}</pre>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # --- File Downloads ---
            text_bytes = result.encode('utf-8')

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

            # --- Download Buttons ---
            st.download_button("📄 Download as Text", data=text_bytes, file_name="ResumeCopilot.txt")
            st.download_button("📝 Download as Word (.docx)", data=docx_buffer, file_name="ResumeCopilot.docx")
            st.download_button("📕 Download as PDF", data=pdf_buffer, file_name="ResumeCopilot.pdf")

        except Exception as e:
            st.error(f"⚠️ Error: {e}")

st.markdown("---")
st.caption("**Built with ❤️ in India | ResumeCopilot.ai (Free Edition)**")
