"use client";

import { useState } from "react";

type Question = { id:string; category:string; skill:string; difficulty:string; question:string; rationale:string; source:string };
type Profile = { target_role:string; years_experience:number; skills:string[]; claims:string[]; projects:string[]; required_skills:string[] };

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [resume,setResume] = useState("");
  const [jd,setJd] = useState("");
  const [role,setRole] = useState("Data Analyst");
  const [years,setYears] = useState("5");
  const [mode,setMode] = useState("mixed");
  const [plan,setPlan] = useState<{profile:Profile;questions:Question[]} | null>(null);
  const [index,setIndex] = useState(0);
  const [answer,setAnswer] = useState("");
  const [feedback,setFeedback] = useState<any>(null);
  const [loading,setLoading] = useState(false);

  async function start() {
    setLoading(true); setFeedback(null); setIndex(0);
    const r = await fetch(API+"/v1/interview/plan",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({resume_text:resume,job_description:jd,target_role:role,years_experience:Number(years),mode,question_count:10})});
    setPlan(await r.json()); setLoading(false);
  }

  async function submit() {
    if (!plan) return;
    setLoading(true);
    const r = await fetch(API+"/v1/interview/evaluate",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({question:plan.questions[index],answer,candidate:plan.profile})});
    setFeedback(await r.json()); setLoading(false);
  }

  function next() {
    setAnswer(""); setFeedback(null); setIndex(i=>Math.min(i+1,(plan?.questions.length||1)-1));
  }

  if (plan) {
    const q=plan.questions[index];
    return <main className="shell">
      <header><div className="logo">CareerCoach <span>AI</span></div><div className="pill">{index+1}/{plan.questions.length}</div></header>
      <section className="card">
        <div className="eyebrow">{q.category.toUpperCase()} · {q.skill} · {q.difficulty}</div>
        <h1>{q.question}</h1>
        <textarea value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="Answer as if you are in the real interview..." />
        {!feedback ? <button disabled={loading||!answer.trim()} onClick={submit}>{loading?"Evaluating…":"Submit answer"}</button> :
          <div className="feedback"><div className="score">{feedback.score}<small>/100</small></div>
            <div><b>Strengths</b>{feedback.strengths.map((x:string)=><p key={x}>✓ {x}</p>)}
            <b>Improve</b>{feedback.weaknesses.map((x:string)=><p key={x}>→ {x}</p>)}</div>
            {feedback.follow_up_question && <div className="follow"><b>AI follow-up</b><p>{feedback.follow_up_question}</p></div>}
            {index<plan.questions.length-1 && <button onClick={next}>Next question</button>}
          </div>}
      </section>
    </main>;
  }

  return <main className="shell"><header><div className="logo">CareerCoach <span>AI</span></div><div className="tag">Interview intelligence for professionals</div></header>
    <section className="hero"><div className="eyebrow">RESUME-PROOF · ADAPTIVE · ROLE-SPECIFIC</div><h1>Practice the interview you’re actually going to face.</h1><p>Upload your context. CareerCoach builds questions around your resume, job description, experience and weak spots.</p></section>
    <section className="card form">
      <label>Target role<input value={role} onChange={e=>setRole(e.target.value)}/></label>
      <label>Years of experience<input value={years} onChange={e=>setYears(e.target.value)}/></label>
      <label>Interview mode<select value={mode} onChange={e=>setMode(e.target.value)}><option value="mixed">Mixed</option><option value="technical">Technical</option><option value="behavioral">Behavioral</option><option value="pressure">Pressure</option></select></label>
      <label>Resume<textarea value={resume} onChange={e=>setResume(e.target.value)} placeholder="Paste your resume text here…"/></label>
      <label>Job description<textarea value={jd} onChange={e=>setJd(e.target.value)} placeholder="Paste the job description here…"/></label>
      <button disabled={loading||!role} onClick={start}>{loading?"Building interview…":"Start AI interview"}</button>
    </section>
  </main>;
}
