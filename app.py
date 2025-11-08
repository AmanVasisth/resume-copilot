import streamlit as st
import openai

st.set_page_config(page_title="ResumeCopilot 🇮🇳", page_icon="📄")

st.title("📄 ResumeCopilot – Your AI Resume & Cover Letter Builder 🇮🇳")
st.write("Create professional, ATS-friendly resumes & cover letters instantly with AI.")

openai.api_key = st.secrets["OPENAI_API_KEY"]

job_title = st.text_input("Job Title")
skills = st.text_area("Key Skills (comma-separated)")
experience = st.text_input("Years of Experience")
education = st.text_area("Education Background")
achievements = st.text_area("Achievements (optional)")

if st.button("🚀 Generate Resume & Cover Letter"):
    with st.spinner("Creating your resume... please wait ⏳"):
        prompt = f"""
        Write an ATS-friendly resume and cover letter for the following:
        Job Title: {job_title}
        Experience: {experience} years
        Skills: {skills}
        Education: {education}
        Achievements: {achievements}
        Optimize for Indian job market and professional tone.
        """
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message.content
        st.subheader("✅ Generated Resume & Cover Letter:")
        st.write(result)
        st.download_button("📥 Download Text", result, file_name="resume.txt")

st.markdown("---")
st.markdown("**Built with ❤️ in India | ResumeCopilot.ai (Free Edition)**")
