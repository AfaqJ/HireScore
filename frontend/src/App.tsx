import React, { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { MatchResp, QuizGradeResp, QuizStartResp } from "./types";

/* ---------- helpers ---------- */
const pct = (n?: number | null) => (n == null ? "—" : `${Math.round(n)}%`);

function humanizeBadge(b?: string) {
  if (!b) return { label: "Result", tone: "neutral", emoji: "ℹ️" };
  const key = b.toLowerCase();
  if (key.includes("strong") || key.includes("good"))
    return { label: "Strong match", tone: "good", emoji: "✅" };
  if (key.includes("gap") || key.includes("weak") || key.includes("risk"))
    return { label: "Gaps to address", tone: "warn", emoji: "⚠️" };
  if (key.includes("low"))
    return { label: "Low match", tone: "bad", emoji: "❗" };
  return { label: "Result", tone: "neutral", emoji: "ℹ️" };
}

function Spinner() {
  return (
    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/60 border-t-transparent align-[-2px]" />
  );
}

/* ---------- File Upload (drag & drop + click) ---------- */
type FileUploadProps = {
  accept?: string;
  busy?: boolean;
  onSelect: (file?: File | null) => void;
};

function FileUpload({ accept = ".pdf,.docx,.txt", busy, onSelect }: FileUploadProps) {
  const [dragging, setDragging] = useState(false);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | null) {
    const file = files && files[0] ? files[0] : null;
    if (!file) return;
    setSelectedName(`${file.name} • ${Math.ceil(file.size / 1024)} KB`);
    onSelect(file);
  }

  function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    e.stopPropagation();
    setDragging(false);
    handleFiles(e.dataTransfer?.files || null);
  }

  return (
    <div
      className={`upload-drop ${dragging ? "is-drag" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragEnter={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="dz-icon" aria-hidden>📄</div>
      <div className="dz-title">Drop your resume here</div>
      <div className="dz-sub">PDF, DOCX, or TXT</div>

      <div className="mt-4 flex items-center gap-3">
        <button
          className="btn-primary btn-sm"
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          Choose File
        </button>
        <span className="text-xs text-slate-500">or drag & drop</span>
      </div>

      {selectedName && (
        <div className="mt-3 text-xs text-slate-600">{selectedName}</div>
      )}

      {busy && (
        <div className="upload-overlay">
          <div className="flex items-center gap-2 rounded-lg bg-slate-900/80 px-3 py-2 text-xs text-white">
            <Spinner />
            <span>Uploading…</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- app ---------- */
export default function App() {
  /* Health */
  const [health, setHealth] = useState<"checking" | "ok" | "error">("checking");
  useEffect(() => {
    api
      .health()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("error"));
  }, []);

  /* JD */
  const [jobTitle, setJobTitle] = useState("");
  const [jobText, setJobText] = useState("");
  const [jobId, setJobId] = useState<number | null>(null);
  const [savedJobTitle, setSavedJobTitle] = useState("");
  const [savedJobText, setSavedJobText] = useState("");

  /* Resume */
  const [resumeText, setResumeText] = useState("");
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [savedResumeText, setSavedResumeText] = useState("");

  /* Quiz */
  const [quizN, setQuizN] = useState(5);
  const [quiz, setQuiz] = useState<QuizStartResp | null>(null);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  
  const [graded, setGraded] = useState<QuizGradeResp | null>(null);
  const [quizOpen, setQuizOpen] = useState(false);
  const [quizMatch, setQuizMatch] = useState<{
    score: number;
    gaps: string[];
    matched: number;
    total_skills: number;
    message?: string;
  } | null>(null);

  /* Results */
  const [cvResult, setCvResult] = useState<MatchResp | null>(null);
  const [showCvResult, setShowCvResult] = useState(false);

  /* Busy & toast */
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<
    { kind: "success" | "error" | "info"; msg: string } | null
  >(null);

  useEffect(() => {
    if (!toast) return;
    if (toast.kind === "error") return;
    const t = setTimeout(() => setToast(null), 10_000);
    return () => clearTimeout(t);
  }, [toast]);

  const jdChanged =
    jobTitle.trim() !== savedJobTitle.trim() ||
    jobText.trim() !== savedJobText.trim();
  const resumeChanged = resumeText.trim() !== savedResumeText.trim();

  const canCvMatch = !!jobId && !!resumeId;
  const canGenerateQuiz = !!jobId;

  /* Actions */
  async function saveJD() {
    if (!jobTitle.trim() || !jobText.trim() || !jdChanged) return;
    setBusy("jd");
    try {
      const r = await api.saveJD({ title: jobTitle, jd_text: jobText });
      setJobId(r.job_id);
      setSavedJobTitle(jobTitle);
      setSavedJobText(jobText);
      setToast({ kind: "success", msg: "Job description saved ✅" });
    } catch (e: any) {
      setToast({ kind: "error", msg: e.message || "Failed to save job" });
    } finally {
      setBusy(null);
    }
  }

  async function saveResume() {
    if (!resumeText.trim() || !resumeChanged) return;
    setBusy("resume_text");
    try {
      const r = await api.saveResumeText({ text: resumeText });
      setResumeId(r.resume_id);
      setSavedResumeText(resumeText);
      setToast({ kind: "success", msg: "Resume saved ✅" });
    } catch (e: any) {
      setToast({ kind: "error", msg: e.message || "Failed to save resume" });
    } finally {
      setBusy(null);
    }
  }

  async function uploadResumeFile(file?: File | null) {
    if (!file) return;
    setBusy("resume_file");
    try {
      const r = await api.uploadResumeFile(file);
      setResumeId(r.resume_id);
      setSavedResumeText(""); // file-based upload
      setToast({ kind: "success", msg: "Resume uploaded ✅" });
    } catch (e: any) {
      setToast({ kind: "error", msg: e.message || "Upload failed" });
    } finally {
      setBusy(null);
    }
  }

  async function runCvMatch() {
    if (!canCvMatch) return;
    setBusy("cv");
    try {
      const r = await api.match({ job_id: jobId!, resume_id: resumeId! });
      setCvResult(r);
      setShowCvResult(true);
      setToast({ kind: "success", msg: "CV match computed ✅" });
    } catch (e: any) {
      setToast({ kind: "error", msg: e.message || "CV match failed" });
    } finally {
      setBusy(null);
    }
  }

  async function generateQuiz() {
    if (!canGenerateQuiz) return;
    setBusy("quiz_start");
    try {
      const r = await api.startQuiz({ job_id: jobId!, n: quizN });
      setQuiz(r);
      setAnswers({});
      setGraded(null);
      setQuizOpen(true);
      setToast({ kind: "success", msg: "Quiz generated ✅" });
    } catch (e: any) {
      setToast({ kind: "error", msg: e.message || "Quiz generation failed" });
    } finally {
      setBusy(null);
    }
  }

  async function submitAnswers() {
    if (!quiz?.quiz_id) return;
    setBusy("quiz_grade");
    try {
      const payload = {
        quiz_id: quiz.quiz_id,
        answers: quiz.questions.map((q) => ({
          question_id: q.id,
          text: answers[q.id] || "",
        })),
      };
      const r = await api.gradeQuiz(payload);
setGraded(r);
setQuizMatch(r.quiz_match ?? null);
setQuizOpen(false);
setToast({
  kind: "success",
  msg: `Quiz graded: ${Math.round(r.overall)}% ✅`,
});

    } catch (e: any) {
      setToast({ kind: "error", msg: e.message || "Quiz grading failed" });
    } finally {
      setBusy(null);
    }
  }

  function resetAll() {
    setJobTitle("");
    setJobText("");
    setJobId(null);
    setSavedJobTitle("");
    setSavedJobText("");
    setResumeText("");
    setResumeId(null);
    setSavedResumeText("");
    setQuizN(5);
    setQuiz(null);
    setAnswers({});
    setGraded(null);
    setCvResult(null);
    setShowCvResult(false);
  }

  /* ---------- UI ---------- */
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navbar */}
      <nav className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="text-lg font-semibold tracking-tight text-slate-900">
            <span className="text-indigo-600">HireScore</span>{" "}
            <span className="text-slate-800">· AI Job Fit & Interview Prep</span>
          </div>
          <div>
            {health === "checking" && (
              <span className="chip chip-muted">Checking…</span>
            )}
            {health === "ok" && <span className="chip chip-good">Connected</span>}
            {health === "error" && (
              <span className="chip chip-bad">Backend Offline</span>
            )}
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8">
        {/* Toast */}
        {toast && (
          <div
            className={`toast ${
              toast.kind === "success"
                ? "toast-success"
                : toast.kind === "error"
                ? "toast-error"
                : "toast-info"
            }`}
          >
            <div className="flex-1 text-sm">{toast.msg}</div>
            <button
              className="icon-btn"
              aria-label="Close"
              onClick={() => setToast(null)}
            >
              ✖
            </button>
          </div>
        )}

        {/* JD */}
        <section className="card">
          <header className="section-header">
            <div className="section-title">Paste Job Description</div>
            <div className="section-sub">
              Add a title and full JD. You can generate a quiz with just a JD,
              and add a resume later for CV matching.
            </div>
          </header>
          <div className="card-c space-y-4">
            <div>
              <label className="label">Job Title</label>
              <input
                className="input"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="e.g. Senior Software Engineer"
              />
            </div>
            <div>
              <label className="label">Job Description</label>
              <textarea
                className="textarea"
                value={jobText}
                onChange={(e) => setJobText(e.target.value)}
                placeholder="Paste the complete job description here…"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                className="btn-primary"
                disabled={
                  !jobTitle.trim() || !jobText.trim() || !jdChanged || busy === "jd"
                }
                onClick={saveJD}
              >
                {busy === "jd" ? (
                  <>
                    <Spinner /> <span className="ml-2">Saving…</span>
                  </>
                ) : (
                  "Save JD"
                )}
              </button>
            </div>
          </div>
        </section>

        {/* Resume */}
        <section className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="card">
            <header className="section-header">
              <div className="section-title">Update Resume</div>
              <div className="section-sub">
                Paste your resume as plain text. (JD helps generate better quiz
                questions.)
              </div>
            </header>
            <div className="card-c space-y-4">
              <div>
                <label className="label">Resume Text</label>
                <textarea
                  className="textarea"
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                  placeholder="Paste your complete resume here…"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  className="btn-primary"
                  disabled={
                    !resumeText.trim() || !resumeChanged || busy === "resume_text"
                  }
                  onClick={saveResume}
                >
                  {busy === "resume_text" ? (
                    <>
                      <Spinner /> <span className="ml-2">Saving…</span>
                    </>
                  ) : (
                    "Save Resume"
                  )}
                </button>
              </div>
            </div>
          </div>

          <div className="card">
            <header className="section-header">
              <div className="section-title">Upload Resume File</div>
              <div className="section-sub">PDF, DOCX, or TXT</div>
            </header>
            <div className="card-c space-y-3">
              <FileUpload
                accept=".pdf,.docx,.txt"
                busy={busy === "resume_file"}
                onSelect={(file) => uploadResumeFile(file)}
              />
              <div className="text-xs text-slate-500">
                Upload triggers immediately on file select.
              </div>
            </div>
          </div>
        </section>

        {/* Results */}
        <section className="card">
          <header className="section-header">
            <div className="section-title">Results</div>
            <div className="section-sub">
              Run CV Match or generate an interview quiz. Do them in any order.
            </div>
          </header>

          <div className="card-c space-y-10">
            {/* CV Match */}
            <div className="space-y-3">
              <div className="text-sm text-slate-600">
                JD: {jobId ? "ready" : "missing"} · Resume:{" "}
                {resumeId ? "ready" : "optional"}
              </div>
              <button
                className="btn-outline"
                disabled={!canCvMatch || busy === "cv"}
                onClick={runCvMatch}
              >
                {busy === "cv" ? (
                  <>
                    <Spinner /> <span className="ml-2">Computing…</span>
                  </>
                ) : (
                  "Run CV Match"
                )}
              </button>

              {cvResult?.cv_match && showCvResult && (
                <div className="result-panel">
                  <button
                    className="icon-btn absolute right-3 top-3"
                    aria-label="Close"
                    onClick={() => setShowCvResult(false)}
                  >
                    ✖
                  </button>

                  <div className="flex items-baseline gap-3">
                    <div className="text-4xl font-semibold">
                      {pct(cvResult.cv_match.score)}
                    </div>
                    <div
                      className={`chip ${
                        humanizeBadge(cvResult.badge).tone === "good"
                          ? "chip-good"
                          : humanizeBadge(cvResult.badge).tone === "warn"
                          ? "chip-warn"
                          : humanizeBadge(cvResult.badge).tone === "bad"
                          ? "chip-bad"
                          : "chip-muted"
                      }`}
                    >
                      {humanizeBadge(cvResult.badge).emoji}{" "}
                      {humanizeBadge(cvResult.badge).label}
                    </div>
                  </div>

                  <div className="mt-1 text-sm text-slate-700">
                    Matched <b>{cvResult.cv_match.matched}</b> of{" "}
                    <b>{cvResult.cv_match.total_skills}</b> skills
                  </div>

                  {(cvResult.recommend?.top_cv_gaps?.length ||
                    cvResult.cv_match.gaps.length) && (
                    <div className="mt-4">
                      <div className="mb-1 text-sm text-slate-600">
                        Top gaps to work on:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(cvResult.recommend?.top_cv_gaps ||
                          cvResult.cv_match.gaps)
                          .slice(0, 10)
                          .map((g, i) => (
                            <span key={i} className="chip chip-muted">
                              {g}
                            </span>
                          ))}
                      </div>
                    </div>
                  )}

                  {cvResult.message && (
                    <div className="mt-4 text-sm text-slate-700">
                      {cvResult.message}
                    </div>
                  )}
                </div>
              )}
            </div>
            {/* Quiz Fit (self-assessment) */}
{quizMatch && (
  <div className="result-panel">
    <div className="flex items-baseline gap-3">
      <div className="text-4xl font-semibold">{pct(quizMatch.score)}</div>
      <span className="chip chip-muted">Quiz Fit</span>
    </div>

    <div className="mt-1 text-sm text-slate-700">
      Strong answers on {quizMatch.matched} of {quizMatch.total_skills} areas.
    </div>

    {!!quizMatch.gaps?.length && (
      <div className="mt-4">
        <div className="mb-1 text-sm text-slate-600">Improve these areas:</div>
        <div className="flex flex-wrap gap-2">
          {quizMatch.gaps.slice(0, 10).map((g, i) => (
            <span key={i} className="chip chip-muted">{g}</span>
          ))}
        </div>
      </div>
    )}

    {quizMatch.message && (
      <div className="mt-4 text-sm text-slate-700">{quizMatch.message}</div>
    )}
  </div>
)}

            {/* Quiz */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <label className="text-sm">Questions:</label>
                <input
                  type="number"
                  className="input input-narrow"
                  min={1}
                  max={10}
                  value={quizN}
                  onChange={(e) => setQuizN(Number(e.target.value || 5))}
                  onKeyDown={(e) => {
                    const allowed = ["ArrowUp", "ArrowDown", "Tab"];
                    if (!allowed.includes(e.key)) e.preventDefault();
                  }}
                  onPaste={(e) => e.preventDefault()}
                />
                <button
                  className="btn-outline"
                  disabled={!canGenerateQuiz || busy === "quiz_start"}
                  onClick={generateQuiz}
                >
                  {busy === "quiz_start" ? (
                    <>
                      <Spinner /> <span className="ml-2">Generating…</span>
                    </>
                  ) : (
                    "Generate Quiz"
                  )}
                </button>
                {quiz && (
                  <button
                    className="btn-outline"
                    onClick={() => setQuizOpen(true)}
                  >
                    Open Quiz
                  </button>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3">
          <button className="btn-outline" onClick={resetAll}>
            Reset Session
          </button>
        </div>
      </main>

      {/* Quiz Modal */}
      {quizOpen && (
        <div className="modal-backdrop" onClick={() => setQuizOpen(false)}>
          <div
            className="modal-panel"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <header className="flex items-start justify-between">
              <div className="text-lg font-semibold">🧪 Quiz</div>
              <button
                className="icon-btn"
                aria-label="Close"
                onClick={() => setQuizOpen(false)}
              >
                ✖
              </button>
            </header>

            {!quiz?.questions?.length ? (
              <div className="py-8 text-center text-sm text-slate-600">
                No questions generated yet.
              </div>
            ) : (
                <div className="mt-4 max-h-[60vh] space-y-4 overflow-y-auto pr-1">
                {quiz.questions.map((q, i) => (
                  <div key={q.id} className="space-y-2">
                    <div className="text-sm font-medium">
                      {i + 1}. {q.text}
                    </div>
                    <textarea
                      className="textarea"
                      value={answers[q.id] || ""}
                      onChange={(e) =>
                        setAnswers((a) => ({ ...a, [q.id]: e.target.value }))
                      }
                      placeholder="Type your answer…"
                    />
                  </div>
                ))}
              </div>
              
            )}

            <div className="mt-5 flex items-center justify-end gap-3">
              <button className="btn-outline" onClick={() => setQuizOpen(false)}>
                Close
              </button>
              <button
                className="btn-primary"
                disabled={busy === "quiz_grade" || !quiz?.questions?.length}
                onClick={submitAnswers}
              >
                {busy === "quiz_grade" ? (
                  <>
                    <Spinner /> <span className="ml-2">Grading…</span>
                  </>
                ) : (
                  "Submit Answers"
                )}
              </button>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
