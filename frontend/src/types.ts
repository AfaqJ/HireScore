export interface JDResp { job_id: number }
export interface ResumeResp { resume_id: number }
export interface ResumeFileResp { resume_id: number; chars: number }
export interface QuizStartResp {
  quiz_id: number
  questions: { id: number; idx: number; text: string }[]
}
export interface QuizGradeResp {
  overall: number
  feedback: { question_id: number; score: number; tip: string }[]
}
export interface MatchResp {
  cv_match?: { score: number; gaps: string[]; matched: number; total_skills: number } | null
  quiz_match?: { score: number } | null
  combined?: number | null
  badge?: string
  message?: string
  recommend?: { top_cv_gaps?: string[] }
}
