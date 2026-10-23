"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Question = { id: string; category: string; skill: string; difficulty: string; question: string; rationale: string; source: string };
type Candidate = { target_role: string; years_experience: number; skills: string[]; claims: string[]; projects: string[]; required_skills: string[]; skill_evidence?: Record<string, string[]> };
type Evaluation = { score: number; strengths: string[]; weaknesses: string[]; follow_up_question?: string | null; evaluation_method?: string; evaluation_provider?: string; confidence?: string; next_focus?: string; relevance?: number; technical_correctness?: number; ownership?: number; reasoning?: number; validation?: number; depth?: number; specificity?: number; communication?: number };
type Plan = { profile: Candidate; questions: Question[] };
type SpeechRecognitionLike = {
  continuous: boolean; interimResults: boolean; lang: string;
  onresult: ((event: any) => void) | null; onerror: ((event: any) => void) | null; onend: (() => void) | null;
  start: () => void; stop: () => void;
};
declare global { interface Window { SpeechRecognition?: new () => SpeechRecognitionLike; webkitSpeechRecognition?: new () => SpeechRecognitionLike } }

const styles = `
:root{color-scheme:light}
*{box-sizing:border-box}
.video-shell{min-height:100vh;background:#f5f7fb;color:#172033;padding:28px 18px 56px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.video-wrap{max-width:1120px;margin:0 auto}
.v-top{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:28px}
.v-brand{display:flex;align-items:center;gap:11px;font-weight:800;font-size:18px;letter-spacing:-.4px}
.v-logo{display:grid;place-items:center;width:40px;height:40px;border-radius:13px;background:#4f46e5;color:white;font-size:21px;box-shadow:0 7px 18px #4f46e52b}
.v-link{color:#4f46e5;text-decoration:none;font-weight:700;font-size:14px}
.v-hero{margin:14px 0 24px}
.v-eyebrow{font-size:11px;letter-spacing:1.7px;font-weight:800;color:#6258d8;text-transform:uppercase}
.v-hero h1{font-size:clamp(30px,4vw,44px);line-height:1.1;letter-spacing:-1.8px;margin:9px 0 12px}
.v-hero p{color:#667085;max-width:700px;line-height:1.7;margin:0}
.v-card{background:white;border:1px solid #e7eaf2;border-radius:20px;padding:24px;box-shadow:0 10px 30px #18204408}
.v-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.v-field{display:flex;flex-direction:column;gap:8px;font-size:13px;font-weight:700;color:#344054}
.v-field input,.v-field textarea,.v-field select,.v-transcript{font:inherit;font-weight:400;color:#182230;border:1px solid #dce1eb;border-radius:11px;padding:12px 13px;outline:none;background:#fff;width:100%}
.v-field textarea{min-height:120px;resize:vertical;line-height:1.5}
.v-field input:focus,.v-field textarea:focus,.v-transcript:focus{border-color:#8178ee;box-shadow:0 0 0 3px #635bff18}
.v-span{grid-column:1/-1}
.v-btn{border:0;border-radius:11px;background:#4f46e5;color:white;font-weight:750;padding:12px 17px;cursor:pointer;transition:transform .15s,background .15s}
.v-btn:hover{background:#4338ca;transform:translateY(-1px)}
.v-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.v-btn.secondary{background:#eef0ff;color:#4438ca}
.v-btn.ghost{background:white;color:#344054;border:1px solid #dce1eb}
.v-note{font-size:12px;line-height:1.6;color:#667085}
.v-privacy{display:flex;gap:10px;padding:13px 14px;background:#f0fdf4;border:1px solid #d1fadf;border-radius:12px;color:#166534;font-size:12px;line-height:1.5;margin-top:16px}
.v-error{padding:12px 14px;border-radius:11px;background:#fff1f0;color:#b42318;font-size:13px;margin:14px 0}
.v-workspace{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(300px,.8fr);gap:18px;align-items:start}
.v-video{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:14px;background:#111827}
.v-video-frame{position:relative;background:#111827;border-radius:14px;overflow:hidden}
.v-live{position:absolute;top:12px;left:12px;padding:6px 9px;border-radius:7px;background:#ffffffed;color:#344054;font-size:11px;font-weight:800}
.v-live.rec{background:#fee4e2;color:#b42318}
.v-record-controls{display:flex;flex-wrap:wrap;gap:9px;margin-top:13px}
.v-q-label{font-size:11px;font-weight:800;letter-spacing:1.2px;color:#6258d8;text-transform:uppercase}
.v-question{font-size:23px;line-height:1.4;letter-spacing:-.5px;margin:11px 0 15px}
.v-meta{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.v-pill{padding:6px 9px;background:#f2f4f7;border-radius:999px;color:#475467;font-size:11px;font-weight:700}
.v-transcript{min-height:150px;resize:vertical;line-height:1.65}
.v-score{font-size:42px;line-height:1;font-weight:850;letter-spacing:-1.5px;color:#4f46e5}
.v-feedback-list{padding-left:18px;line-height:1.6;color:#475467;font-size:13px}
.v-feedback-list li{margin:5px 0}
.v-meter{height:7px;border-radius:99px;background:#eef0f6;overflow:hidden;margin:8px 0 13px}
.v-meter span{display:block;height:100%;background:#6558e8;border-radius:99px}
.v-foot{font-size:12px;color:#98a2b3;text-align:center;margin-top:25px}
@media(max-width:760px){.v-grid,.v-workspace{grid-template-columns:1fr}.v-card{padding:17px}.v-top{align-items:flex-start}.v-hero h1{letter-spacing:-1px}.v-span{grid-column:auto}}
`;

export default function VideoInterviewPage() {
  const [role, setRole] = useState("Data Analyst");
  const [years, setYears] = useState("5");
  const [resume, setResume] = useState("");
  const [jd, setJd] = useState("");
  const [mode, setMode] = useState("mixed");
  const [plan, setPlan] = useState<Plan | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [asked, setAsked] = useState<Question[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cameraReady, setCameraReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [recordingUrl, setRecordingUrl] = useState("");
  const [completed, setCompleted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const transcriptRef = useRef("");
  const recordUrlRef = useRef("");

  const currentQuestion = questions[questionIndex];

  useEffect(() => {
    transcriptRef.current = transcript;
  }, [transcript]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach(track => track.stop());
      recognitionRef.current?.stop();
      if (recordUrlRef.current) URL.revokeObjectURL(recordUrlRef.current);
    };
  }, []);

  const startCamera = useCallback(async () => {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Camera access is unavailable in this browser. Use a recent Chrome or Edge browser over localhost or HTTPS.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: true });
      streamRef.current?.getTracks().forEach(track => track.stop());
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
      setCameraReady(true);
    } catch (e: any) {
      setError(e?.name === "NotAllowedError" ? "Camera/microphone permission was blocked. Allow access in your browser address bar and retry." : "Could not start your camera and microphone. Check that another app is not using them.");
    }
  }, []);

  async function buildInterview() {
    setError("");
    if (!role.trim()) { setError("Please enter your target role."); return; }
    if (!resume.trim() && !jd.trim()) { setError("Add your resume or the job description so the AI can personalise questions."); return; }
    setLoading(true);
    try {
      const response = await fetch(API + "/v1/interview/plan", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_key: "video-demo-" + (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Date.now()), resume_text: resume, job_description: jd, target_role: role.trim(), years_experience: Number(years), mode, question_count: 5 })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not create an interview plan.");
      if (!data.questions?.length) throw new Error("No questions were generated. Add more resume or job-description detail.");
      setPlan(data); setQuestions(data.questions); setQuestionIndex(0); setAsked([]); setEvaluations([]); setEvaluation(null); setTranscript(""); setCompleted(false); setRecordingUrl("");
      window.setTimeout(() => document.getElementById("video-workspace")?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    } catch (e: any) {
      setError(e?.message || "Could not connect to the AI interview service. Check that the backend is running.");
    } finally { setLoading(false); }
  }

  function startSpeechRecognition() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) { setSpeechSupported(false); return; }
    try {
      const recognition = new Recognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-IN";
      recognition.onresult = (event: any) => {
        let finalText = "";
        let interimText = "";
        for (let i = 0; i < event.results.length; i++) {
          const result = event.results[i];
          if (result.isFinal) finalText += result[0].transcript + " ";
          else interimText += result[0].transcript + " ";
        }
        const previous = transcriptRef.current;
        const priorFinal = previous.split(" ").filter(Boolean).join(" ");
        const combined = [priorFinal, finalText.trim(), interimText.trim()].filter(Boolean).join(" ");
        setTranscript(combined);
        transcriptRef.current = combined;
      };
      recognition.onerror = () => setSpeechSupported(false);
      recognition.onend = () => { recognitionRef.current = null; };
      recognitionRef.current = recognition;
      recognition.start();
    } catch { setSpeechSupported(false); }
  }

  function startRecording() {
    setError("");
    if (!streamRef.current) { setError("Start the camera before recording."); return; }
    if (typeof MediaRecorder === "undefined") { setError("This browser cannot record video. Try the latest Chrome or Edge."); return; }
    chunksRef.current = [];
    if (recordUrlRef.current) URL.revokeObjectURL(recordUrlRef.current);
    recordUrlRef.current = "";
    setRecordingUrl("");
    try {
      const preferred = MediaRecorder.isTypeSupported("video/webm;codecs=vp9,opus") ? "video/webm;codecs=vp9,opus" : "video/webm";
      const recorder = new MediaRecorder(streamRef.current, { mimeType: preferred });
      recorder.ondataavailable = e => { if (e.data && e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "video/webm" });
        const url = URL.createObjectURL(blob);
        recordUrlRef.current = url;
        setRecordingUrl(url);
      };
      recorderRef.current = recorder;
      recorder.start(500);
      setTranscript("");
      transcriptRef.current = "";
      setElapsed(0);
      startSpeechRecognition();
      setRecording(true);
    } catch { setError("Recording could not start. Check your camera/microphone permission and try again."); }
  }

  function stopRecording() {
    try { if (recorderRef.current?.state === "recording") recorderRef.current.stop(); } catch {}
    try { recognitionRef.current?.stop(); } catch {}
    setRecording(false);
  }

  async function submitAnswer() {
    if (!plan || !currentQuestion) return;
    if (transcript.trim().split(/\s+/).length < 3) { setError("Add or dictate your spoken answer in the transcript box before evaluating."); return; }
    setLoading(true); setError("");
    try {
      const response = await fetch(API + "/v1/interview/evaluate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: currentQuestion, answer: transcript.trim(), candidate: plan.profile })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "AI evaluation is unavailable. Please retry.");
      setEvaluation(data); setEvaluations(prev => [...prev, data]); setAsked(prev => [...prev, currentQuestion]);
    } catch (e: any) { setError(e?.message || "Could not evaluate this answer. Please retry."); }
    finally { setLoading(false); }
  }

  async function nextQuestion() {
    if (!plan || !currentQuestion || !evaluation) return;
    setLoading(true); setError("");
    try {
      const response = await fetch(API + "/v1/interview/next", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate: plan.profile, available_questions: questions, asked_questions: asked, evaluations: [...evaluations.slice(0, -1), evaluation], last_question: currentQuestion, last_evaluation: evaluation })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load the next question.");
      if (data.interview_complete || !data.question) { setCompleted(true); stopRecording(); streamRef.current?.getTracks().forEach(t => t.stop()); streamRef.current = null; setCameraReady(false); return; }
      const next = data.question as Question;
      const existing = questions.some(q => q.id === next.id);
      setQuestions(prev => existing ? prev : [...prev, next]);
      setQuestionIndex(prev => prev + 1); setAsked(prev => prev.some(q => q.id === currentQuestion.id) ? prev : [...prev, currentQuestion]);
      setEvaluation(null); setTranscript(""); transcriptRef.current = ""; setRecordingUrl("");
      if (videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
    } catch (e: any) { setError(e?.message || "Could not move to the next question."); }
    finally { setLoading(false); }
  }

  function resetInterview() {
    stopRecording();
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setCameraReady(false); setPlan(null); setQuestions([]); setQuestionIndex(0); setAsked([]); setEvaluations([]); setEvaluation(null); setTranscript(""); setCompleted(false); setRecordingUrl(""); setError("");
  }

  useEffect(() => {
    if (!recording) return;
    const id = window.setInterval(() => setElapsed(value => value + 1), 1000);
    return () => window.clearInterval(id);
  }, [recording]);

  const time = (seconds: number) => `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`;

  return (
    <>
      <style jsx global>{styles}</style>
      <main className="video-shell">
        <div className="video-wrap">
          <header className="v-top">
            <div className="v-brand"><span className="v-logo">✦</span><span>CareerCoach <span style={{ color: "#6258d8" }}>AI</span></span></div>
            <a className="v-link" href="/">← Back to interview coach</a>
          </header>

          {!plan && !completed && <>
            <section className="v-hero">
              <div className="v-eyebrow">VIDEO INTERVIEW LAB · EARLY ACCESS</div>
              <h1>Practise out loud.<br /><span style={{ color: "#6258d8" }}>Improve with evidence.</span></h1>
              <p>Run a role-specific webcam mock interview. Your answers are transcribed where supported, evaluated by the existing AI coach, and turned into actionable feedback.</p>
            </section>
            <section className="v-card">
              <div className="v-grid">
                <label className="v-field">Target role<input value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Data Analyst" /></label>
                <label className="v-field">Years of experience<input type="number" min="0" max="50" value={years} onChange={e => setYears(e.target.value)} /></label>
                <label className="v-field">Interview style<select value={mode} onChange={e => setMode(e.target.value)}><option value="mixed">Mixed interview</option><option value="technical">Technical deep dive</option><option value="behavioral">Behavioral</option><option value="pressure">Pressure round</option></select></label>
                <label className="v-field">Resume file (optional)<input type="file" accept=".pdf,.docx,.txt,.md" onChange={async e => {
                  const file = e.target.files?.[0]; if (!file) return;
                  if (file.size > 8 * 1024 * 1024) { setError("Please use a resume smaller than 8 MB."); return; }
                  setError("");
                  const form = new FormData(); form.append("file", file);
                  try { const r = await fetch(API + "/v1/resume/extract", { method: "POST", body: form }); const d = await r.json(); if (!r.ok) throw new Error(d.detail || "Could not read this resume."); setResume(d.text || ""); }
                  catch (err: any) { setError(err?.message || "Could not read the resume. You can paste the text below."); }
                }} /></label>
                <label className="v-field v-span">Resume text<textarea value={resume} onChange={e => setResume(e.target.value)} placeholder="Paste your resume text or upload a file above…" /></label>
                <label className="v-field v-span">Job description<textarea value={jd} onChange={e => setJd(e.target.value)} placeholder="Paste the job description to get more targeted interview questions…" /></label>
              </div>
              <div className="v-privacy"><span>🔒</span><span><b>Privacy-first prototype.</b> Camera/video stays in this browser and is not uploaded to the backend. The transcript is sent to the existing evaluation API when you ask for feedback. Browser speech recognition availability varies.</span></div>
              {error && <div className="v-error" role="alert">{error}</div>}
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 18 }}><button className="v-btn" disabled={loading} onClick={buildInterview}>{loading ? "Preparing questions…" : "Build my video interview →"}</button></div>
            </section>
          </>}

          {plan && !completed && currentQuestion && <section id="video-workspace">
            <div className="v-hero">
              <div className="v-eyebrow">YOUR VIDEO MOCK INTERVIEW</div>
              <h1>{role} <span style={{ color: "#98a2b3", fontWeight: 500 }}>· Question {questionIndex + 1}</span></h1>
              <p>Answer naturally, like a real interview. You can edit the transcript before asking the AI to evaluate your answer.</p>
            </div>
            <div className="v-workspace">
              <div className="v-card">
                <div className="v-video-frame">
                  <video ref={videoRef} className="v-video" autoPlay muted playsInline />
                  <span className={"v-live" + (recording ? " rec" : "")}>{recording ? "● RECORDING " + time(elapsed) : cameraReady ? "CAMERA READY" : "CAMERA NOT STARTED"}</span>
                </div>
                <div className="v-record-controls">
                  {!cameraReady ? <button className="v-btn" onClick={startCamera}>Enable camera & mic</button> : null}
                  {cameraReady && !recording && !evaluation ? <button className="v-btn" onClick={startRecording}>● Start recording answer</button> : null}
                  {recording ? <button className="v-btn" style={{ background: "#b42318" }} onClick={stopRecording}>■ Stop recording</button> : null}
                  {recordingUrl ? <a className="v-btn secondary" href={recordingUrl} download={`careercoach-answer-${questionIndex + 1}.webm`} style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}>Download recording ↓</a> : null}
                  {evaluation && <button className="v-btn ghost" onClick={() => { setEvaluation(null); setTranscript(""); setRecordingUrl(""); }}>Try this answer again</button>}
                </div>
                <p className="v-note" style={{ marginTop: 12 }}>{speechSupported ? "Speech-to-text works in supported browsers. Review the transcript before submitting." : "Automatic speech-to-text is unavailable or was blocked. Type your answer in the transcript box instead."} Your recording remains local until you download it.</p>
              </div>

              <div className="v-card">
                <div className="v-q-label">Question {questionIndex + 1} of {questions.length}</div>
                <div className="v-question">{currentQuestion.question}</div>
                <div className="v-meta"><span className="v-pill">{currentQuestion.category}</span><span className="v-pill">{currentQuestion.skill}</span><span className="v-pill">{currentQuestion.difficulty}</span></div>
                <label className="v-field">Your answer transcript<textarea className="v-transcript" value={transcript} onChange={e => { setTranscript(e.target.value); transcriptRef.current = e.target.value; }} placeholder="Your spoken answer appears here when speech recognition is supported. You can also type your answer…" /></label>
                {error && <div className="v-error" role="alert">{error}</div>}
                {!evaluation ? <button className="v-btn" style={{ width: "100%", marginTop: 14 }} disabled={loading || recording} onClick={submitAnswer}>{loading ? "Evaluating answer…" : "Evaluate my answer →"}</button> : <>
                  <div style={{ borderTop: "1px solid #eaecf0", marginTop: 20, paddingTop: 18 }}>
                    <div className="v-q-label">AI feedback</div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 10 }}><span className="v-score">{evaluation.score}</span><span style={{ color: "#667085", fontSize: 13 }}>/ 100 answer score</span></div>
                    <div className="v-meter"><span style={{ width: evaluation.score + "%" }} /></div>
                    <b style={{ fontSize: 13 }}>What went well</b><ul className="v-feedback-list">{(evaluation.strengths || []).map((s, i) => <li key={"s" + i}>{s}</li>)}</ul>
                    <b style={{ fontSize: 13 }}>What to improve</b><ul className="v-feedback-list">{(evaluation.weaknesses || []).map((s, i) => <li key={"w" + i}>{s}</li>)}</ul>
                    {evaluation.follow_up_question && <div style={{ background: "#f5f3ff", padding: 12, borderRadius: 10, fontSize: 13, lineHeight: 1.6 }}><b>Possible follow-up:</b> {evaluation.follow_up_question}</div>}
                    <button className="v-btn" style={{ width: "100%", marginTop: 14 }} disabled={loading} onClick={nextQuestion}>{loading ? "Loading next question…" : questionIndex + 1 >= questions.length ? "Finish / continue interview →" : "Next question →"}</button>
                  </div>
                </>}
              </div>
            </div>
          </section>}

          {completed && <section className="v-card">
            <div className="v-eyebrow">SESSION COMPLETE</div>
            <h1 style={{ fontSize: 34, letterSpacing: -1, margin: "10px 0" }}>You showed up. That's progress.</h1>
            <p style={{ color: "#667085", lineHeight: 1.7 }}>Your video practice session is complete. Here is a quick snapshot of your evaluated answers.</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 12, margin: "22px 0" }}>
              <div style={{ padding: 17, borderRadius: 13, background: "#f5f3ff" }}><div className="v-note">Average answer score</div><div className="v-score" style={{ marginTop: 9 }}>{evaluations.length ? Math.round(evaluations.reduce((sum, item) => sum + item.score, 0) / evaluations.length) : 0}</div></div>
              <div style={{ padding: 17, borderRadius: 13, background: "#f0fdf4" }}><div className="v-note">Answers evaluated</div><div style={{ fontSize: 32, fontWeight: 850, marginTop: 9 }}>{evaluations.length}</div></div>
            </div>
            <h3>Keep improving</h3><p className="v-note">Review your downloaded recordings, revisit the weak areas above, and practise your answers again with specific examples and measurable outcomes.</p>
            <button className="v-btn" onClick={resetInterview}>Start another video interview</button>
          </section>}

          <footer className="v-foot">CareerCoach AI · Webcam MVP · Video is processed locally in this prototype.</footer>
        </div>
      </main>
    </>
  );
}
