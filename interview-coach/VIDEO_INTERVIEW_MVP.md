# Webcam Interview MVP

This is an early portfolio-first webcam workflow added alongside the existing CareerCoach AI interview experience.

## What works in this MVP
- Creates role-specific interview questions using the existing FastAPI interview-plan endpoint.
- Enables the user's webcam and microphone after explicit permission.
- Records each answer in the browser using MediaRecorder; a recording can be downloaded locally.
- Uses browser speech recognition when available to create an editable transcript.
- Sends the reviewed transcript to the existing AI answer-evaluation endpoint.
- Uses the existing adaptive next-question endpoint and displays answer scores, strengths, and weaknesses.
- Provides a simple completion snapshot.

## Run locally
Start the backend from the existing project environment:

```powershell
cd C:\Users\admin\resume-copilot\interview-coach
python -m uvicorn api.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd C:\Users\admin\resume-copilot\interview-coach\web
npm run dev
```

Open http://localhost:3000/video-interview. The homepage also includes a **Video mock interview** link.

## Browser requirements
- Use a recent Chrome or Edge browser.
- Camera and microphone access requires localhost or HTTPS.
- Browser speech recognition support varies by browser, operating system, and language settings. If unavailable, type or paste the answer into the transcript box.
- The page requests camera/microphone permission only after the user clicks **Enable camera & mic**.

## Privacy and limitations
- This prototype does not upload webcam video to the backend. Recordings are held in browser memory and can be downloaded by the user.
- The transcript is sent to the existing answer-evaluation API only when the user selects **Evaluate my answer**.
- Speech-to-text is a browser capability, not a guaranteed cross-browser service. The transcript should be reviewed for errors before evaluation.
- This is not a real-time talking avatar or a live AI voice conversation. The AI provides text questions and feedback; the candidate answers on camera.
- The completion snapshot is an MVP summary, not a hiring prediction or a formal assessment.
- Before a public SaaS launch, add authentication, per-user authorization, consent/retention controls, secure persistence, rate limits, error monitoring, tests, and deployment configuration.

## Suggested next steps
1. Run a full manual test with camera permission allowed and denied.
2. Verify transcript behavior and manual transcript editing.
3. Add automated tests for the video interview workflow and evaluation errors.
4. Build a richer completion report and persist video-session results through authenticated user accounts.
