import type {
  CandidateInput,
  CandidateProfile,
  JobNormalization,
  JobOffer,
  MatchAssessment,
  TailoredResume,
} from "./types";

const API_ROOT = "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly requestId: string | null,
  ) {
    super(detail);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("content-type", "application/json");
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new ApiError(
      response.status,
      body?.detail ?? "request_failed",
      response.headers.get("x-request-id"),
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const workflowApi = {
  createCandidate: (payload: CandidateInput) =>
    request<CandidateProfile>("/candidate-profiles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createJobOffer: (rawText: string, normalization: JobNormalization) =>
    request<JobOffer>("/job-offers/manual", {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText, normalization }),
    }),
  createAssessment: (candidateProfileId: string, jobOfferId: string) =>
    request<MatchAssessment>("/match-assessments", {
      method: "POST",
      body: JSON.stringify({
        candidate_profile_id: candidateProfileId,
        job_offer_id: jobOfferId,
      }),
    }),
  createResume: (candidateProfileId: string, jobOfferId: string, matchAssessmentId: string) =>
    request<TailoredResume>("/tailored-resumes", {
      method: "POST",
      body: JSON.stringify({
        candidate_profile_id: candidateProfileId,
        job_offer_id: jobOfferId,
        match_assessment_id: matchAssessmentId,
        use_llm: false,
      }),
    }),
  reviewResume: (resumeId: string, decision: "approved" | "rejected") =>
    request<TailoredResume>(`/tailored-resumes/${resumeId}/review`, {
      method: "PATCH",
      body: JSON.stringify({ decision }),
    }),
  deleteCandidate: (candidateId: string) =>
    request<undefined>(`/candidate-profiles/${candidateId}`, { method: "DELETE" }),
  deleteJobOffer: (offerId: string) =>
    request<undefined>(`/job-offers/${offerId}`, { method: "DELETE" }),
};
