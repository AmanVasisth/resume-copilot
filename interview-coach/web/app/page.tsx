"use client";

import {useEffect,useRef,useState} from "react";
type Q={id:string;category:string;skill:string;difficulty:string;question:string;rationale:string;source:string};
type P={target_role:string;years_experience:number;skills:string[];claims:string[];projects:string[];required_skills:string[]};
type E={score:number;strengths:string[];weaknesses:string[];follow_up_question?:string;evaluation_method?:"llm_rubric"|"heuristic_fallback";evaluation_provider?:"gemini"|"openrouter"|"heuristic";confidence?:"high"|"medium"|"low"};
const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";

export default function Home(){
 const[resume,setResume]=useState(""),[jd,setJd]=useState(""),[role,setRole]=useState("Data Analyst"),[years,setYears]=useState("5"),[mode,setMode]=useState("mixed");
 const[plan,setPlan]=useState<{profile:P;questions:Q[]}|null>(null),[index,setIndex]=useState(0),[answer,setAnswer]=useState(""),[answerRecords,setAnswerRecords]=useState<Record<string,string>>({}),[feedback,setFeedback]=useState<E|null>(null),[asked,setAsked]=useState<Q[]>([]),[evals,setEvals]=useState<E[]>([]),[report,setReport]=useState<any>(null),[loading,setLoading]=useState(false);
 const[voice,setVoice]=useState(false),[listening,setListening]=useState(false),[voiceError,setVoiceError]=useState("");
 const[uploading,setUploading]=useState(false),[uploadError,setUploadError]=useState(""),[startError,setStartError]=useState("");
 const[sessionId,setSessionId]=useState<number|null>(null),[history,setHistory]=useState<any[]>([]),[showHistory,setShowHistory]=useState(false),[historyLoading,setHistoryLoading]=useState(false);
 const[candidateKey,setCandidateKey]=useState("");
 const[detailSession,setDetailSession]=useState<any>(null),[detailLoading,setDetailLoading]=useState(false);
 const[progress,setProgress]=useState<any>(null),[progressLoading,setProgressLoading]=useState(false),[showProgress,setShowProgress]=useState(false);
 const[recommendations,setRecommendations]=useState<any>(null),[recommendationsLoading,setRecommendationsLoading]=useState(false);
 const recognition=useRef<any>(null);
 const skillCatalog=["SQL","Python","Power BI","Qlik Sense","Databricks","Snowflake","Azure","Tableau","Machine Learning","GenAI","LangChain","Power Automate","Excel"];
 const resumeSkills=skillCatalog.filter(s=>resume.toLowerCase().includes(s.toLowerCase()));
 const jdSkills=skillCatalog.filter(s=>jd.toLowerCase().includes(s.toLowerCase()));

 useEffect(()=>{if(typeof window==="undefined")return;let key=window.localStorage.getItem("careercoach_candidate_key");if(!key){key="candidate-"+Math.random().toString(36).slice(2)+Date.now().toString(36);window.localStorage.setItem("careercoach_candidate_key",key)}setCandidateKey(key);const R=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;if(!R){return}const r=new R();r.continuous=true;r.interimResults=true;r.lang="en-IN";r.onresult=(e:any)=>{let finalText="";for(let i=e.resultIndex;i<e.results.length;i++){if(e.results[i].isFinal)finalText+=e.results[i][0].transcript+" "}if(finalText)setAnswer(a=>(a+" "+finalText).trim())};r.onerror=()=>{setListening(false);setVoiceError("Voice recognition stopped. You can continue with typing.")};r.onend=()=>setListening(false);recognition.current=r;return()=>{try{r.stop()}catch{}}},[]);

 function speak(text:string){if(typeof window==="undefined"||!("speechSynthesis" in window))return;window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang="en-IN";u.rate=.95;window.speechSynthesis.speak(u)}
 function toggleVoice(){setVoice(v=>{const nv=!v;if(!nv){try{recognition.current?.stop()}catch{};setListening(false)}return nv})}
 function startListening(){setVoiceError("");if(!recognition.current){setVoiceError("Voice recognition is not supported in this browser. Try Chrome or Edge.");return}setListening(true);try{recognition.current.start()}catch{}}
 function stopListening(){try{recognition.current?.stop()}catch{};setListening(false)}

 async function uploadResume(file:File){setUploadError("");setUploading(true);try{const fd=new FormData();fd.append("file",file);const r=await fetch(API+"/v1/resume/extract",{method:"POST",body:fd});const out=await r.json();if(!r.ok)throw new Error(out.detail||"Could not read resume");setResume(out.text||"");}catch(e:any){setUploadError(e.message||"Could not read resume")}finally{setUploading(false)}}
 async function loadHistory(){if(!candidateKey)return;setHistoryLoading(true);try{const r=await fetch(API+"/v1/sessions?candidate_key="+encodeURIComponent(candidateKey));const out=await r.json();setHistory(out.sessions||[])}catch{}finally{setHistoryLoading(false)}}
 async function loadProgress(){if(!candidateKey)return;setProgressLoading(true);try{const r=await fetch(API+"/v1/progress?candidate_key="+encodeURIComponent(candidateKey));const out=await r.json();setProgress(out)}catch(err){console.error(err);alert("Could not load progress. Check the backend is updated.")}finally{setProgressLoading(false)}}
 async function loadRecommendations(){if(!candidateKey)return;setRecommendationsLoading(true);try{const r=await fetch(API+"/v1/recommendations?candidate_key="+encodeURIComponent(candidateKey));const out=await r.json();if(!r.ok)throw new Error(out.detail||"Request failed");setRecommendations(out)}catch(err){console.error(err);alert("Could not load practice recommendations. Check the backend is updated.")}finally{setRecommendationsLoading(false)}}
 async function openSession(id:number){if(!candidateKey)return;setDetailLoading(true);try{const r=await fetch(API+"/v1/sessions/"+id+"?candidate_key="+encodeURIComponent(candidateKey));const out=await r.json();if(!r.ok)throw new Error(out.detail||"Could not load session");setDetailSession(out)}catch(err){console.error(err);alert("Could not load session details.")}finally{setDetailLoading(false)}}
 async function resumeSession(s:any){if(!s?.plan){alert("This older session does not have a saved interview plan, so it cannot be resumed. Start a new interview instead.");return}const base=s.plan;const questions=[...(base.questions||[])];const askedQs=(s.answers||[]).map((a:any)=>{let q=questions.find((x:Q)=>x.id===a.question_id);if(!q){q={id:a.question_id,question:a.question,skill:a.skill,category:a.category,difficulty:"professional",rationale:"Saved adaptive question",source:"adaptive"};questions.push(q)}return q});const evaluations=(s.answers||[]).map((a:any)=>a.evaluation as E);setPlan({...base,questions});setAsked(askedQs);setEvals(evaluations);setAnswerRecords(Object.fromEntries((s.answers||[]).map((a:any)=>[a.question_id,a.answer||""])));setSessionId(s.id);setRole(s.target_role);setYears(String(s.years_experience));setMode(s.mode);setReport(null);setFeedback(null);setAnswer("");setDetailSession(null);setShowHistory(false);if(!askedQs.length){setIndex(0);return}const last=askedQs[askedQs.length-1];const lastEval=evaluations[evaluations.length-1];setLoading(true);try{const r=await fetch(API+"/v1/interview/next",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate:base.profile,available_questions:questions,asked_questions:askedQs,evaluations,last_question:last,last_evaluation:lastEval})});const out=await r.json();if(out.interview_complete){setReport(out.readiness)}else{const q=out.question;const idx=questions.findIndex((x:Q)=>x.id===q.id);if(idx>=0)setIndex(idx);else{questions.push(q);setPlan({...base,questions});setIndex(questions.length-1)}if(voice)speak(q.question)}}catch(err){console.error(err);alert("Could not resume session. Please try again.")}finally{setLoading(false)}}
 async function start(){setStartError("");if(!role.trim()){setStartError("Add a target role to personalise your interview.");return}if(!resume.trim()&&!jd.trim()){setStartError("For useful, tailored questions, attach/paste your resume or add the job description first.");return}if(!Number.isFinite(Number(years))||Number(years)<0||Number(years)>50){setStartError("Enter a valid experience range from 0 to 50 years.");return}setLoading(true);try{const r=await fetch(API+"/v1/interview/plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_key:candidateKey,resume_text:resume,job_description:jd,target_role:role.trim(),years_experience:Number(years),mode,question_count:10})});const newPlan=await r.json();if(!r.ok)throw new Error(newPlan.detail||"Could not build interview");if(!newPlan.questions?.length)throw new Error("We could not build questions from this input. Add more resume detail or a job description and try again.");setPlan(newPlan);setAsked([]);setEvals([]);setAnswerRecords({});setReport(null);setIndex(0);setFeedback(null);setAnswer("");setSessionId(null);setDetailSession(null);try{const sr=await fetch(API+"/v1/sessions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_key:candidateKey,target_role:role,years_experience:Number(years),mode,plan:newPlan})});const so=await sr.json();if(sr.ok)setSessionId(so.id)}catch(e){console.warn("Session history could not be saved",e)} }catch(err:any){console.error(err);setStartError(err?.message||"Could not start interview. Check that the backend is running.")}finally{setLoading(false)}}
 async function submit(){if(!plan)return;stopListening();setLoading(true);setStartError("");try{const r=await fetch(API+"/v1/interview/evaluate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:plan.questions[index],answer,candidate:plan.profile})});const ev=await r.json();if(!r.ok){setFeedback(null);setStartError(typeof ev.detail==="string"?ev.detail:"AI evaluation is temporarily unavailable. Your answer has not been scored; please retry.");return}setFeedback(ev);setAnswerRecords(prev=>({...prev,[plan.questions[index].id]:answer}));if(sessionId&&plan){try{await fetch(API+"/v1/sessions/"+sessionId+"/answers",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_key:candidateKey,question:plan.questions[index],answer,evaluation:ev})})}catch{}}}catch(err){setFeedback(null);setStartError("Could not reach the evaluation service. Check that the backend is running, then retry.")}finally{setLoading(false)}}
 async function next(){if(!plan||!feedback)return;setLoading(true);const q=plan.questions[index],a=[...asked,q],e=[...evals,feedback];const r=await fetch(API+"/v1/interview/next",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate:plan.profile,available_questions:plan.questions,asked_questions:a,evaluations:e,last_question:q,last_evaluation:feedback})});const out=await r.json();setAsked(a);setEvals(e);setFeedback(null);setAnswer("");if(out.interview_complete){setReport(out.readiness);if(sessionId){const overall=Number(out.readiness?.overall_readiness||0);try{await fetch(API+"/v1/sessions/"+sessionId+"/complete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_key:candidateKey,overall_score:overall})})}catch{}}}else{const nextQ=out.question;const existingIndex=plan.questions.findIndex(x=>x.id===nextQ.id);if(existingIndex>=0){setIndex(existingIndex)}else{setPlan(p=>p?{...p,questions:[...p.questions,nextQ]}:p);setIndex(plan.questions.length)}if(voice)speak(nextQ.question)}setLoading(false)}

 async function finishInterview(){if(!plan||!feedback)return;setLoading(true);stopListening();const q=plan.questions[index],a=[...asked,q],e=[...evals,feedback];try{const r=await fetch(API+"/v1/interview/next",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate:plan.profile,available_questions:plan.questions,asked_questions:a,evaluations:e,last_question:q,last_evaluation:feedback})});const out=await r.json();if(!r.ok)throw new Error(out.detail||"Could not create readiness report");setAsked(a);setEvals(e);setReport(out.readiness);if(sessionId){await fetch(API+"/v1/sessions/"+sessionId+"/complete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({candidate_key:candidateKey,overall_score:Number(out.readiness?.overall_readiness||0)})})}}catch(err){console.error(err);alert("Could not finish the interview. Please try again.")}finally{setLoading(false)}}

  if (report) {
    const dimensions = [
      { key: "technical_correctness", label: "Technical accuracy" },
      { key: "relevance", label: "Question relevance" },
      { key: "ownership", label: "Personal contribution" },
      { key: "reasoning", label: "Reasoning & decisions" },
      { key: "validation", label: "Validation & results" },
      { key: "depth", label: "Technical depth" },
      { key: "specificity", label: "Specificity" },
      { key: "communication", label: "Communication" },
    ];
    const dimensionScores = dimensions.map(d => {
      const values = evals.map(e => Number((e as any)[d.key])).filter(v => Number.isFinite(v));
      return { ...d, score: values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : 0 };
    });
    const practicePriorities = [...dimensionScores].sort((a, b) => a.score - b.score).slice(0, 3);
    const answeredQuestions = asked.map((q, i) => ({ question: q, evaluation: evals[i] })).filter(x => x.evaluation);
    return (
      <main className="shell report-shell">
        <header>
          <div className="logo">CareerCoach <span>AI</span></div>
          <div className="header-actions">
            <button type="button" className="history-button" onClick={() => { setPlan(null); setReport(null); setFeedback(null); setShowHistory(true); loadHistory(); }}>Interview history</button>
            <button type="button" className="history-button" onClick={() => window.print()}>Print / Save PDF</button>
          </div>
        </header>
        <section className="card report-hero">
          <div className="eyebrow">YOUR INTERVIEW DEBRIEF</div>
          <div className="report-score-row">
            <div><div className="score">{report.overall_readiness}<small>/100</small></div><p className="report-muted">Overall practice score · {answeredQuestions.length} answers reviewed</p></div>
            <div className="report-status"><span className="report-status-dot"/><b>{report.recommendation}</b><small>Use this as practice guidance, not a hiring prediction.</small></div>
          </div>
          <div className="report-stat-grid">
            <div><span>Questions answered</span><strong>{answeredQuestions.length}</strong></div>
            <div><span>Strongest skill</span><strong>{(report.top_strengths || [])[0] || "Keep practising"}</strong></div>
            <div><span>Priority gaps</span><strong>{(report.priority_gaps || []).length}</strong></div>
          </div>
        </section>
        <section className="card report-section">
          <div className="eyebrow">SKILL BREAKDOWN</div><h2>Where you stand</h2>
          <p className="report-muted">Scores reflect your answers in this practice session, not a formal certification.</p>
          {Object.entries(report.skill_scores || {}).length ? <div className="report-skill-list">
            {Object.entries(report.skill_scores || {}).map(([k, v]) => {
              const score = Math.max(0, Math.min(100, Number(v) || 0));
              return <div className="report-skill" key={k}><div><b>{k}</b><strong>{score}/100</strong></div><div className="report-track"><span style={{width: score + "%"}}/></div><small>{score >= 80 ? "Strong evidence in this session" : score >= 65 ? "Developing — add more evidence" : "Priority area to practise"}</small></div>;
            })}
          </div> : <p>No skill-level scores were recorded.</p>}
          <h3 className="report-subheading">Core interview dimensions</h3>
          <div className="report-dimensions">{dimensionScores.map(d => <div className="report-dimension" key={d.key}><span>{d.label}</span><b>{d.score}</b><div className="report-track"><span style={{width: d.score + "%"}}/></div></div>)}</div>
        </section>
        <section className="card report-section">
          <div className="eyebrow">YOUR NEXT PRACTICE PLAN</div><h2>Turn gaps into a plan</h2>
          <p className="report-muted">Start with the lowest-scoring dimensions. Use real examples and never invent project metrics.</p>
          <div className="report-practice-list">{practicePriorities.map((d, i) => <article className="report-practice-card" key={d.key}><div className="report-practice-number">0{i+1}</div><div><b>{d.label} <span>{d.score}/100</span></b><p>{d.key === "technical_correctness" ? "Review the core concept, explain what each service actually does, and distinguish retrieval, orchestration and generation." : d.key === "relevance" ? "Answer the exact question first, then connect your example to the role and business problem." : d.key === "ownership" ? "Separate what you personally implemented from what the wider team delivered; name your concrete actions." : d.key === "reasoning" ? "Explain the options you considered, why you chose one, and the trade-off you accepted." : d.key === "validation" ? "Describe test cases, the baseline, how you measured results, and only report metrics you can substantiate." : d.key === "depth" ? "Add implementation details, architecture, edge cases, monitoring and failure handling that you actually worked with." : d.key === "specificity" ? "Replace broad claims with one real example, the tools used, your actions and observable evidence." : "Use a clear Situation → Action → Decision → Result structure; be concise and explain technical terms plainly."}</p></div></article>)}</div>
          <div className="report-gap-box"><b>Priority skills from this interview</b><p>{(report.priority_gaps || []).join(" · ") || "No skill gap fell below the current threshold. Keep practising with harder questions."}</p></div>
        </section>
        <section className="card report-section">
          <div className="eyebrow">ANSWER-BY-ANSWER REVIEW</div><h2>Feedback you can revisit</h2>
          {answeredQuestions.length ? <div className="report-answer-list">{answeredQuestions.map(({question, evaluation}, i) => <article className="report-answer" key={question.id + "-" + i}><div className="report-answer-heading"><span>{i+1}. {question.skill} · {question.category}</span><strong>{evaluation!.score}/100</strong></div><p className="report-question-text">{question.question}</p><div className="report-answer-body"><b>Your answer</b><p>{answerRecords[question.id]?.trim() || "The original answer was not available in this report. This question may have come from an older saved session."}</p><b>Strengths</b>{(evaluation!.strengths || []).length ? (evaluation!.strengths || []).map((s, j) => <p key={j}>✓ {s}</p>) : <p>None recorded.</p>}<b>Improve next time</b>{(evaluation!.weaknesses || []).length ? (evaluation!.weaknesses || []).map((w, j) => <p key={j}>→ {w}</p>) : <p>No specific gaps were returned.</p>}{evaluation!.follow_up_question && <p><b>Practice prompt:</b> {evaluation!.follow_up_question}</p>}</div></article>)}</div> : <p>No individual answers are available in this report.</p>}
          <div className="report-actions"><button onClick={() => { setPlan(null); setReport(null); setFeedback(null); setAnswer(""); setAnswerRecords({}); setAsked([]); setEvals([]); setSessionId(null); setIndex(0); }}>Start another interview</button><button className="report-secondary" onClick={() => window.print()}>Save this report as PDF</button></div>
        </section>
        <p className="report-disclaimer">CareerCoach AI provides practice feedback, not a guarantee of interview performance. Scores can vary between AI evaluations; use the evidence and explanations alongside the number.</p>
      </main>
    );
  }
  if (plan) {
    const q = plan.questions[index];
    return (
      <main className="shell">
        <header>
          <div className="logo">CareerCoach <span>AI</span></div>
          <div className="pill">{voice ? "🎙 Voice interview" : "Text interview"}</div>
        </header>
        <section className="card">
          <div className="eyebrow">{q.category.toUpperCase()} · {q.skill} · {q.difficulty}</div>
          <h1>{q.question}</h1>
          {voice && (
            <div className="voicebar">
              <button className={listening ? "recording" : ""} onClick={listening ? stopListening : startListening}>{listening ? "● Listening…" : "🎙 Speak answer"}</button>
              <span>{listening ? "Speak naturally. Your answer is being transcribed." : "Use your microphone or type below."}</span>
            </div>
          )}
          <textarea value={answer} onChange={e => setAnswer(e.target.value)} placeholder={voice ? "Your spoken answer will appear here…" : "Answer as if you are in the real interview..."} />
          {voice && voiceError && <p className="error">{voiceError}</p>}
          {startError && <p className="error" role="alert">{startError}</p>}
          {!feedback ? (
            <button disabled={loading || !answer.trim()} onClick={submit}>{loading ? "Evaluating…" : "Submit answer"}</button>
          ) : (
            <div className="feedback">
              <div className="score">{feedback.score}<small>/100</small></div>
              <div className="evaluation-note"><b>{feedback.score<20?"Not enough evidence yet":feedback.score<50?"Needs stronger evidence":feedback.score<70?"Developing answer":"Strong answer"}</b><span>{feedback.evaluation_method==="llm_rubric"?(feedback.evaluation_provider==="openrouter"?"AI rubric evaluation · OpenRouter":feedback.evaluation_provider==="gemini"?"AI rubric evaluation · Gemini":"AI rubric evaluation"):"Basic relevance/structure check"} · {feedback.confidence==="medium"?"moderate confidence":"low confidence"}</span>{feedback.evaluation_method!=="llm_rubric"&&<p>Detailed technical accuracy is not verified in fallback mode. Add an AI provider key for rubric-based grading.</p>}</div>
              <b>Strengths</b>
              {feedback.strengths.map(x => <p key={x}>✓ {x}</p>)}
              <b>Improve</b>
              {feedback.weaknesses.map(x => <p key={x}>→ {x}</p>)}
              {feedback.follow_up_question && <div className="follow"><b>AI follow-up</b><p>{feedback.follow_up_question}</p></div>}
              <div className="feedback-actions">
                <button disabled={loading} onClick={next}>{loading ? "Adapting…" : "Continue adaptive interview"}</button>
                <button type="button" className="finish-button" disabled={loading} onClick={finishInterview}>{loading ? "Finishing…" : "Finish interview & view report"}</button>
              </div>
            </div>
          )}
        </section>
      </main>
    );
  }
 return (
 <main className="dashboard-shell">
  <aside className="sidebar">
    <div className="brand-lockup"><span className="brand-mark">✦</span><div className="logo">CareerCoach <span>AI</span></div></div>
    <div className="nav-label">WORKSPACE</div>
    <button className="nav-item active" onClick={()=>{setShowHistory(false);setShowProgress(false);window.scrollTo({top:0,behavior:"smooth"})}}>⌂ <span>Dashboard</span></button>
    <button className="nav-item" onClick={()=>document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}>◉ <span>Start interview</span></button>
    <button className="nav-item" onClick={()=>{setShowProgress(true);loadProgress();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}>☷ <span>Practice plan</span></button>
    <button className="nav-item" onClick={()=>{setShowHistory(true);loadHistory();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}>◷ <span>Interview history</span></button>
    <button className="nav-item" onClick={()=>{setShowProgress(true);loadProgress();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}>▥ <span>Progress analytics</span></button>
    <div className="sidebar-spacer"/>
    <div className="upgrade-card"><div className="upgrade-icon">✦</div><b>Build your career edge</b><p>Practice with feedback tailored to your resume and target role.</p><button onClick={()=>document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}>Start practising ↗</button></div>
    <div className="sidebar-foot"><span className="online-dot"/> Your personal AI coach</div>
  </aside>
  <div className="dashboard-main">
    <header className="dashboard-topbar"><div><div className="topbar-kicker">YOUR CAREER WORKSPACE</div><h2>Welcome back, Aman <span>✦</span></h2></div><div className="topbar-actions"><div className="status-chip"><span className="online-dot"/> AI coach ready</div><button type="button" className="history-button" onClick={()=>{setShowHistory(v=>!v);if(!showHistory)loadHistory();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}>Interview history</button></div></header>
    <section className="launch-hero">
      <div className="launch-copy"><div className="launch-pill"><span/> PERSONALIZED · ADAPTIVE · RESUME-AWARE</div><h1>Turn interview practice into your <em>unfair advantage.</em></h1><p>Practice realistic interviews, get useful feedback, and focus your time on the skills that will move you forward.</p><div className="hero-actions"><button onClick={()=>document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}>Start mock interview <span>→</span></button><button className="hero-secondary" onClick={()=>{setShowProgress(true);loadProgress();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}>Explore my progress</button></div><div className="hero-trust"><span>✦ Resume-aware questions</span><span>◉ Instant feedback</span><span>↗ Adaptive practice</span></div></div>
      <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="hero-glow"/><div className="bot-face"><div className="bot-antenna"/><div className="bot-eyes"><i/><i/></div><div className="bot-smile"/></div><div className="float-card float-card-one"><span className="float-icon purple">✦</span><div><b>Adaptive questions</b><small>Built around your experience</small></div></div><div className="float-card float-card-two"><span className="float-icon cyan">↗</span><div><b>Actionable feedback</b><small>Know what to improve next</small></div></div><div className="hero-spark spark-one">✦</div><div className="hero-spark spark-two">✧</div></div>
    </section>
    <section className="quick-actions">
      <button className="quick-card quick-purple" onClick={()=>document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}><span className="quick-icon">▶</span><span className="quick-text"><b>Start an interview</b><small>Role-specific questions and feedback</small><strong>Begin practice ↗</strong></span></button>
      <button className="quick-card quick-blue" onClick={()=>{setShowProgress(true);loadProgress();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}><span className="quick-icon">▤</span><span className="quick-text"><b>Practice plan</b><small>Find your highest-impact next steps</small><strong>Build my plan ↗</strong></span></button>
      <button className="quick-card quick-green" onClick={()=>{setShowProgress(true);loadProgress();document.getElementById("workspace-panels")?.scrollIntoView({behavior:"smooth"})}}><span className="quick-icon">▥</span><span className="quick-text"><b>Progress analytics</b><small>Track skills across sessions</small><strong>View progress ↗</strong></span></button>
      <button className="quick-card quick-orange" onClick={()=>document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}><span className="quick-icon">▧</span><span className="quick-text"><b>Resume insights</b><small>Turn your experience into proof</small><strong>Analyse resume ↗</strong></span></button>
    </section>
    <div id="workspace-panels">{showProgress&&<section className="history-panel"><div className="history-head"><b>Your progress</b><button type="button" className="secondary-button" onClick={loadProgress}>{progressLoading?"Loading…":"Refresh"}</button></div>{!progress?<p>Complete an interview to start building your progress profile.</p>:<><div className="progress-summary"><div><span>Completed interviews</span><strong>{progress.completed_sessions}</strong></div><div><span>Total answers</span><strong>{progress.answers_count}</strong></div><div><span>Average interview score</span><strong>{progress.average_completed_score==null?"—":progress.average_completed_score+"/100"}</strong></div></div><h3>Skill performance</h3>{(progress.skills||[]).length===0?<p>No skill scores yet. Submit interview answers first.</p>:<div className="skill-list">{progress.skills.map((s:any)=><div className="skill-row" key={s.skill}><div><b>{s.skill}</b><p>{s.answers_count} answers · {s.sessions_count} sessions · {s.trend}</p></div><div className="skill-score"><strong>{s.average_score}</strong><span>/100</span><div className="skill-track"><div style={{width:s.average_score+"%"}}/></div></div></div>)}</div>}<h3>Priority gaps</h3><p>{(progress.priority_gaps||[]).join(" · ")||"No priority gaps detected yet."}</p><div className="history-head practice-head"><b>Practice these next</b><button type="button" className="secondary-button" onClick={loadRecommendations}>{recommendationsLoading?"Building plan…":"Generate practice plan"}</button></div>{recommendations&&<div className="practice-list">{(recommendations.topics||[]).map((t:any)=><div className="practice-card" key={t.skill}><div className="practice-card-top"><b>{t.skill}</b><strong>{t.score==null?"New focus":t.score+"/100"}</strong></div><p>{t.reason||"Based on previous answer feedback."}</p>{(t.weaknesses||[]).length>0&&<p><strong>Remembered gaps:</strong> {(t.weaknesses||[]).join(" · ")}</p>}<p><strong>Practice:</strong> {t.practice}</p><button type="button" className="secondary-button" onClick={()=>{setJd((jd?"\n\n":"")+"Practice focus: "+t.skill+". "+t.practice);document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}}>Use in next interview</button></div>)}</div>}</>}</section>}
    {showHistory&&<section className="history-panel"><div className="history-head"><b>Previous interviews</b><button type="button" className="secondary-button" onClick={loadHistory}>{historyLoading?"Loading…":"Refresh"}</button></div>{history.length===0?<p>No saved interviews yet. Complete an interview and it will appear here.</p>:history.map((s:any)=><div className="history-item" key={s.id}><div><b>{s.target_role}</b><p>{new Date(s.created_at).toLocaleString()} · {s.answers_count} answers · {s.status}</p><div className="history-actions"><button type="button" className="secondary-button" onClick={()=>openSession(s.id)}>{detailLoading?"Loading…":"View details"}</button></div></div><strong>{s.overall_score==null?"—":s.overall_score+"/100"}</strong></div>)}{detailSession&&<div className="session-detail"><div className="history-head"><b>{detailSession.target_role} — session details</b><button type="button" className="secondary-button" onClick={()=>setDetailSession(null)}>Close</button></div><p>{detailSession.answers?.length||0} saved answers · {detailSession.status}</p>{(detailSession.answers||[]).map((a:any,i:number)=><div className="answer-detail" key={a.id}><b>{i+1}. {a.question}</b><p><strong>Your answer:</strong> {a.answer}</p><p><strong>Score:</strong> {a.score}/100</p><p><strong>Strengths:</strong> {(a.evaluation?.strengths||[]).join(" · ")||"—"}</p><p><strong>Improve:</strong> {(a.evaluation?.weaknesses||[]).join(" · ")||"—"}</p></div>)}{detailSession.status==="in_progress"&&<button type="button" onClick={()=>resumeSession(detailSession)}>Resume interview</button>}</div>}</section>}</div>
    <section className="dashboard-lower"><div className="setup-panel card" id="interview-setup"><div className="section-heading"><div><div className="eyebrow">LET'S GET YOU READY</div><h2>Build your interview session</h2><p>Choose your target role and personalise the practice.</p></div><span className="setup-number">01 <small>/ 04</small></span></div><div className="form"><label>Target role<input value={role} onChange={e=>setRole(e.target.value)} placeholder="e.g. Data Analyst"/></label><label>Years of experience<input value={years} onChange={e=>setYears(e.target.value)} type="number" min="0" max="50"/></label><label>Interview mode<select value={mode} onChange={e=>setMode(e.target.value)}><option value="mixed">Mixed interview</option><option value="technical">Technical deep dive</option><option value="behavioral">Behavioral</option><option value="pressure">Pressure round</option></select></label><label>Job description<textarea value={jd} onChange={e=>setJd(e.target.value)} placeholder="Paste the job description to make questions more targeted…"/></label><label className="resume-field">Resume<div className="upload-row"><input className="file-input" type="file" accept=".pdf,.docx,.txt,.md" onChange={e=>{const f=e.target.files?.[0];if(f)uploadResume(f)}}/><span>{uploading?"Reading resume…":"Attach PDF, DOCX, TXT or MD"}</span></div>{uploadError&&<p className="error">{uploadError}</p>}<textarea value={resume} onChange={e=>setResume(e.target.value)} placeholder="Or paste your resume text here…"/>{resume&&<div className="file-status">✓ Resume ready for interview personalization</div>}</label><div className="setup-readiness"><div className="readiness-head"><b>Personalisation check</b><span>{(resume.trim()?1:0)+(jd.trim()?1:0)+ (role.trim()?1:0)} of 3 ready</span></div><div className="readiness-checks"><span className={role.trim()?"ready":""}>● Target role</span><span className={resume.trim()?"ready":""}>● Resume</span><span className={jd.trim()?"ready":""}>● Job description</span></div>{resumeSkills.length>0&&<div className="detected-skills"><small>Skills detected in resume</small><div>{resumeSkills.map(s=><span key={s}>{s}</span>)}</div></div>}{jdSkills.length>0&&<div className="detected-skills"><small>Skills mentioned in job description</small><div>{jdSkills.map(s=><span key={s}>{s}</span>)}</div></div>}<p>{resume.trim()&&jd.trim()?"Great — questions can connect your experience to the role requirements.":resume.trim()?"Add the job description too for a more targeted interview.":jd.trim()?"Add your resume to challenge your real project claims.":"Add a resume or job description to improve question relevance."}</p></div>{startError&&<p className="error" role="alert">{startError}</p>}<div className="voicechoice"><b>Interview format</b><button type="button" className={voice?"selected":""} onClick={toggleVoice}>{voice?"🎙 Voice interview":"⌨ Text interview"}</button></div><button disabled={loading||!role} onClick={start}>{loading?"Preparing your interview…":"Generate my interview →"}</button></div></div>
      <aside className="coach-panel"><div className="coach-header"><span className="coach-spark">✦</span><div><b>Your AI coach</b><small>Small steps. Stronger answers.</small></div><span className="live-tag">LIVE</span></div><div className="coach-message"><div className="coach-avatar">✦</div><p>Start with a realistic interview. Your feedback will highlight what you did well and what to improve next.</p></div><div className="coach-tip"><b>Coach's tip</b><p>Use a real example, explain the decision you made, and finish with evidence of the outcome.</p></div><button className="coach-cta" onClick={()=>document.getElementById("interview-setup")?.scrollIntoView({behavior:"smooth"})}>Let's practise ↗</button><div className="coach-footer">Your progress is saved in this browser profile.</div></aside>
    </section>
    <footer className="dashboard-footer"><span>CareerCoach AI</span><span>Built for deliberate practice · Your next opportunity starts here.</span></footer>
  </div>
 </main>
  );
}
