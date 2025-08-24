import React, { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import type { MatchResp, QuizGradeResp, QuizStartResp } from './types'

const pct = (n?: number | null) => (n == null ? '—' : `${Math.round(n)}%`)
const badgeClass = (b?: string) => {
  if (!b) return 'badge border-slate-300 text-slate-700 bg-slate-100'
  if (b.includes('strong')) return 'badge border-green-200 text-green-800 bg-green-100'
  if (b.includes('good')) return 'badge border-emerald-200 text-emerald-800 bg-emerald-100'
  if (b.includes('gaps') || b.includes('weak')) return 'badge border-amber-200 text-amber-800 bg-amber-50'
  if (b.includes('low') || b.includes('risk')) return 'badge border-rose-200 text-rose-800 bg-rose-50'
  return 'badge border-slate-300 text-slate-700 bg-slate-100'
}

export default function App() {
  // Health
  const [health, setHealth] = useState<'checking'|'ok'|'error'>('checking')
  useEffect(() => {
    api.health().then(() => setHealth('ok')).catch(() => setHealth('error'))
  }, [])

  // JD
  const [jobTitle, setJobTitle] = useState('')
  const [jobText, setJobText] = useState('')
  const [jobId, setJobId] = useState<number | null>(null)

  // Resume
  const [resumeText, setResumeText] = useState('')
  const [resumeId, setResumeId] = useState<number | null>(null)

  // Quiz
  const [quizN, setQuizN] = useState(5)
  const [quiz, setQuiz] = useState<QuizStartResp | null>(null)
  const [answers, setAnswers] = useState<Record<number,string>>({})
  const [graded, setGraded] = useState<QuizGradeResp | null>(null)

  // Results
  const [cvResult, setCvResult] = useState<MatchResp | null>(null)
  const [combined, setCombined] = useState<MatchResp | null>(null)

  // Busy & toast
  const [busy, setBusy] = useState<string | null>(null)
  const [toast, setToast] = useState<{kind:'success'|'error'|'info', msg:string} | null>(null)

  const canCvMatch = !!jobId && !!resumeId
  const canStartQuiz = !!jobId
  const canComputeCombined = !!jobId && (!!resumeId || !!quiz?.quiz_id || !!graded)

  const resetAll = () => {
    setJobTitle(''); setJobText(''); setJobId(null)
    setResumeText(''); setResumeId(null)
    setQuizN(5); setQuiz(null); setAnswers({}); setGraded(null)
    setCvResult(null); setCombined(null)
  }

  // Actions
  async function saveJD() {
    setBusy('jd')
    try {
      const r = await api.saveJD({ title: jobTitle, jd_text: jobText })
      setJobId(r.job_id); setToast({kind:'success', msg:`Saved JD (job_id: ${r.job_id})`})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'Failed to save JD'})
    } finally { setBusy(null) }
  }

  async function saveResume() {
    setBusy('resume_text')
    try {
      const r = await api.saveResumeText({ text: resumeText })
      setResumeId(r.resume_id); setToast({kind:'success', msg:`Saved Resume (resume_id: ${r.resume_id})`})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'Failed to save resume'})
    } finally { setBusy(null) }
  }

  async function uploadResumeFile(file?: File | null) {
    if (!file) return
    setBusy('resume_file')
    try {
      const r = await api.uploadResumeFile(file)
      setResumeId(r.resume_id); setToast({kind:'success', msg:`Uploaded resume (id: ${r.resume_id}, ${r.chars} chars)`})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'Upload failed'})
    } finally { setBusy(null) }
  }

  async function runCvMatch() {
    if (!canCvMatch) return
    setBusy('cv')
    try {
      const r = await api.match({ job_id: jobId!, resume_id: resumeId! })
      setCvResult(r); setToast({kind:'success', msg:'CV match computed'})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'CV match failed'})
    } finally { setBusy(null) }
  }

  async function startQuiz() {
    if (!canStartQuiz) return
    setBusy('quiz_start')
    try {
      const r = await api.startQuiz({ job_id: jobId!, n: quizN })
      setQuiz(r); setAnswers({}); setGraded(null)
      setToast({kind:'success', msg:`Quiz started (quiz_id: ${r.quiz_id})`})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'Quiz start failed'})
    } finally { setBusy(null) }
  }

  async function submitAnswers() {
    if (!quiz?.quiz_id) return
    setBusy('quiz_grade')
    try {
      const payload = {
        quiz_id: quiz.quiz_id,
        answers: quiz.questions.map(q => ({ question_id: q.id, text: answers[q.id] || '' }))
      }
      const r = await api.gradeQuiz(payload)
      setGraded(r); setToast({kind:'success', msg:`Quiz graded (${Math.round(r.overall)}%)`})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'Quiz grade failed'})
    } finally { setBusy(null) }
  }

  async function computeCombined() {
    if (!jobId) return
    setBusy('combined')
    try {
      const body: { job_id:number; resume_id?:number; quiz_id?:number } = { job_id: jobId }
      if (resumeId) body.resume_id = resumeId
      if (quiz?.quiz_id) body.quiz_id = quiz.quiz_id
      const r = await api.match(body)
      setCombined(r); setToast({kind:'success', msg:'Combined fit computed'})
    } catch (e:any) {
      setToast({kind:'error', msg:e.message || 'Combined fit failed'})
    } finally { setBusy(null) }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
        <h1 className="text-2xl font-semibold">HireScore — AI Job Fit & Interview Prep</h1>
        <div className="sm:ml-auto">
          {health === 'checking' && <span className="badge border-slate-300 bg-slate-100 text-slate-700">Checking…</span>}
          {health === 'ok' && <span className="badge border-green-200 bg-green-100 text-green-700">Connected</span>}
          {health === 'error' && <span className="badge border-rose-200 bg-rose-50 text-rose-700">Backend Offline</span>}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className={
          `card p-3 ${toast.kind==='success'?'bg-green-50 border-green-200':
          toast.kind==='error'?'bg-rose-50 border-rose-200':'bg-slate-50 border-slate-200'}`
        }>
          <div className="text-sm">{toast.msg}</div>
        </div>
      )}

      {/* JD Card */}
      <div className="card">
        <div className="card-h">
          <div className="text-lg font-medium">Paste Job Description</div>
          <div className="text-sm text-slate-600">Enter a title and full JD. You can take the quiz with just a JD, or add a resume to enable CV matching and combined fit.</div>
        </div>
        <div className="card-c space-y-4">
          <div>
            <label className="block text-sm mb-1">Job Title</label>
            <input className="input" value={jobTitle} onChange={e=>setJobTitle(e.target.value)} placeholder="e.g. Senior Software Engineer" />
          </div>
          <div>
            <label className="block text-sm mb-1">Job Description</label>
            <textarea className="textarea" value={jobText} onChange={e=>setJobText(e.target.value)} placeholder="Paste the complete job description here…" />
          </div>
          <div className="flex items-center gap-3">
            <button className="btn-primary" disabled={!jobTitle || !jobText || !!busy} onClick={saveJD}>
              {busy==='jd' ? 'Saving…' : 'Save JD'}
            </button>
            {jobId && <span className="badge border-slate-300 text-slate-700 bg-slate-100">job_id: {jobId}</span>}
          </div>
        </div>
      </div>

      {/* Resume Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-h">
            <div className="text-lg font-medium">Paste Resume</div>
            <div className="text-sm text-slate-600">Paste your resume as plain text.</div>
          </div>
          <div className="card-c space-y-4">
            {!jobId && <div className="text-sm border border-amber-200 bg-amber-50 text-amber-900 rounded-md p-3">Tip: You can save a resume now, but quiz generation works best with a saved JD.</div>}
            <div>
              <label className="block text-sm mb-1">Resume Text</label>
              <textarea className="textarea" value={resumeText} onChange={e=>setResumeText(e.target.value)} placeholder="Paste your complete resume here…" />
            </div>
            <div className="flex items-center gap-3">
              <button className="btn-primary" disabled={!resumeText || !!busy} onClick={saveResume}>
                {busy==='resume_text' ? 'Saving…' : 'Save Resume'}
              </button>
              {resumeId && <span className="badge border-slate-300 text-slate-700 bg-slate-100">resume_id: {resumeId}</span>}
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <div className="text-lg font-medium">Upload Resume File</div>
            <div className="text-sm text-slate-600">PDF, DOCX, or TXT (≤ 5MB).</div>
          </div>
          <div className="card-c space-y-4">
            <input type="file" accept=".pdf,.docx,.txt" onChange={(e)=>uploadResumeFile(e.target.files?.[0])} className="input" />
            <div className="text-xs text-slate-500">Upload triggers immediately on file select.</div>
            {resumeId && <span className="badge border-slate-300 text-slate-700 bg-slate-100">resume_id: {resumeId}</span>}
          </div>
        </div>
      </div>

      {/* Results & Actions */}
      <div className="card">
        <div className="card-h">
          <div className="text-lg font-medium">Results & Actions</div>
          <div className="text-sm text-slate-600">Run CV Match, take an Interview Quiz, or compute Combined Fit. Do them in any order.</div>
        </div>
        <div className="card-c space-y-10">

          {/* CV Match */}
          <section className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <span>JD: {jobId ? <span className="badge border-slate-300 bg-slate-100">ID {jobId}</span> : <span className="badge border-amber-300 bg-amber-50 text-amber-800">missing</span>}</span>
              <span>Resume: {resumeId ? <span className="badge border-slate-300 bg-slate-100">ID {resumeId}</span> : <span className="badge border-amber-300 bg-amber-50 text-amber-800">optional for CV match</span>}</span>
            </div>
            <button className="btn-outline" disabled={!canCvMatch || !!busy} onClick={runCvMatch}>
              {busy==='cv' ? 'Computing…' : 'Run CV Match'}
            </button>

            {cvResult?.cv_match && (
              <div className="mt-3 grid gap-3">
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-semibold">{pct(cvResult.cv_match.score)}</div>
                  <span className={badgeClass(cvResult.badge)}>{cvResult.badge || 'cv'}</span>
                </div>
                <div className="text-sm text-slate-700">
                  Matched <b>{cvResult.cv_match.matched}</b> of <b>{cvResult.cv_match.total_skills}</b> skills
                </div>
                {(cvResult.recommend?.top_cv_gaps?.length || cvResult.cv_match.gaps.length) ? (
                  <div className="text-sm">
                    <div className="mb-1 text-slate-600">Top gaps:</div>
                    <div className="flex flex-wrap gap-2">
                      {(cvResult.recommend?.top_cv_gaps || cvResult.cv_match.gaps).slice(0,8).map((g, i) => (
                        <span key={i} className="badge border-slate-200 bg-slate-100 text-slate-800">{g}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
                {cvResult.message && <div className="text-sm text-slate-600">{cvResult.message}</div>}
              </div>
            )}
          </section>

          {/* Quiz */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <label className="text-sm">Questions:</label>
              <input type="number" className="input w-24" min={1} max={10} value={quizN} onChange={(e)=>setQuizN(Number(e.target.value || 5))} />
              <button className="btn-outline" disabled={!canStartQuiz || !!busy} onClick={startQuiz}>
                {busy==='quiz_start' ? 'Starting…' : 'Start Quiz'}
              </button>
              {quiz && <span className="badge border-slate-300 bg-slate-100">quiz_id: {quiz.quiz_id}</span>}
            </div>

            {quiz?.questions?.length ? (
              <div className="space-y-4">
                {quiz.questions.map(q => (
                  <div key={q.id} className="space-y-2">
                    <div className="text-sm font-medium">{q.idx}. {q.text}</div>
                    <textarea
                      className="textarea"
                      value={answers[q.id] || ''}
                      onChange={e => setAnswers(a => ({ ...a, [q.id]: e.target.value }))}
                      placeholder="Type your answer…"
                    />
                  </div>
                ))}
                <button className="btn-primary" disabled={!!busy} onClick={submitAnswers}>
                  {busy==='quiz_grade' ? 'Grading…' : 'Submit Answers'}
                </button>

                {graded && (
                  <div className="mt-4 space-y-2">
                    <div className="text-xl font-semibold">Overall: {pct(graded.overall)}</div>
                    <div className="space-y-2">
                      {graded.feedback.map((f, i) => (
                        <div key={i} className="border border-slate-200 rounded-lg p-3 bg-white">
                          <div className="text-sm font-medium">Q{ i+1 } — Score: {pct(f.score)}</div>
                          <div className="text-sm text-slate-700 mt-1">{f.tip}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </section>

          {/* Combined Fit */}
          <section className="space-y-3">
            <button className="btn-outline" disabled={!canComputeCombined || !!busy} onClick={computeCombined}>
              {busy==='combined' ? 'Computing…' : 'Compute Combined Fit'}
            </button>

            {combined && (
              <div className="grid gap-3">
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-semibold">{pct(combined.combined ?? combined.cv_match?.score ?? combined.quiz_match?.score)}</div>
                  <span className={badgeClass(combined.badge)}>{combined.badge || 'combined'}</span>
                </div>
                {combined.message && <div className="text-sm text-slate-700">{combined.message}</div>}
                {combined.recommend?.top_cv_gaps?.length ? (
                  <div className="text-sm">
                    <div className="mb-1 text-slate-600">Recommended gaps to address:</div>
                    <div className="flex flex-wrap gap-2">
                      {combined.recommend.top_cv_gaps.slice(0,8).map((g,i)=>(
                        <span key={i} className="badge border-slate-200 bg-slate-100 text-slate-800">{g}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Footer controls */}
      <div className="flex items-center gap-3 justify-end">
        <button className="btn-outline" onClick={resetAll}>Reset Session</button>
        <a className="btn-outline" href="/api-docs" target="_blank" rel="noreferrer">API Docs</a>
      </div>
    </div>
  )
}
