import type {
    JDResp,
    ResumeResp,
    ResumeFileResp,
    QuizStartResp,
    QuizGradeResp,
    MatchResp,
  } from "./types";
  
  const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
  
  async function j<T>(r: Response): Promise<T> {
    if (!r.ok) {
      let detail = "Request failed";
      try {
        const e = await r.json();
        detail = e?.detail || JSON.stringify(e);
      } catch {}
      throw new Error(detail);
    }
    return r.json();
  }
  
  export const api = {
    base: BASE,
  
    async health(): Promise<{ status: string }> {
      const res = await fetch(`${BASE}/health`);
      if (!res.ok) throw new Error("Health check failed");
      const data = await res.json();
      console.log("Health check response:", data);
  
      // Accept either {"status":"ok"} or {"ok":true}
      if (data?.status === "ok") return { status: "ok" };
      if (data?.ok === true) return { status: "ok" };
      throw new Error("Unexpected health response: " + JSON.stringify(data));
    },
  
    async saveJD(payload: { title: string; jd_text: string }): Promise<JDResp> {
      const res = await fetch(`${BASE}/ingest/jd`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return j(res);
    },
  
    async saveResumeText(payload: { text: string }): Promise<ResumeResp> {
      const res = await fetch(`${BASE}/ingest/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return j(res);
    },
  
    async uploadResumeFile(file: File): Promise<ResumeFileResp> {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${BASE}/ingest/resume-file`, {
        method: "POST",
        body: form,
      });
      return j(res);
    },
  
    async startQuiz(payload: { job_id: number; n: number }): Promise<QuizStartResp> {
      const res = await fetch(`${BASE}/quiz/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return j(res);
    },
                                                      
    async gradeQuiz(payload: { quiz_id: number; answers: { question_id: number; text: string }[] }): Promise<QuizGradeResp> {
      const res = await fetch(`${BASE}/quiz/grade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return j(res);
    },                         
  
    async match(payload: { job_id: number; resume_id?: number; quiz_id?: number }): Promise<MatchResp> {
      const res = await fetch(`${BASE}/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return j(res);
    },
  };
  