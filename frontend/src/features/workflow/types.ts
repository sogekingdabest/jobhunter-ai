export interface CandidateInput {
  full_name: string;
  headline: string | null;
  summary: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  remote_preference: "onsite" | "hybrid" | "remote" | "flexible" | null;
  preferred_roles: string[];
  preferred_locations: string[];
  work_experiences: Array<{
    employer: string;
    title: string;
    description: string | null;
  }>;
  education: never[];
  projects: never[];
  competencies: Array<{
    name: string;
    category: "programming_language" | "framework" | "database" | "cloud" | "devops" | "tool" | "soft_skill" | "other";
    months_experience: number | null;
  }>;
  languages: Array<{
    language: string;
    level: "basic" | "conversational" | "professional" | "fluent" | "native";
  }>;
}

export interface CandidateProfile extends CandidateInput {
  id: string;
  evidence_source_id: string;
  created_at: string;
  updated_at: string;
}

interface Evidence {
  quote: string;
  start_offset: number;
  end_offset: number;
}

interface GroundedValue<T extends string = string> {
  value: T;
  evidence: Evidence;
  confidence: number;
}

export interface JobNormalization {
  contract_version: "1.0";
  company: GroundedValue | null;
  title: GroundedValue | null;
  location: GroundedValue | null;
  remote_type: null;
  employment_type: null;
  seniority: null;
  requirements: Array<{
    requirement_type: "skill" | "experience" | "education" | "language" | "location" | "responsibility" | "other";
    priority: "required" | "preferred" | "unspecified";
    normalized_value: string;
    evidence: Evidence;
    confidence: number;
  }>;
  warnings: string[];
}

export interface JobOffer {
  id: string;
  evidence_source_id: string;
  raw_text: string;
  content_fingerprint: string;
  company: string | null;
  title: string | null;
  location: string | null;
  remote_type: string | null;
  requirements: Array<{
    id: string;
    requirement_type: string;
    priority: string;
    normalized_value: string;
    original_text: string;
  }>;
  warnings: string[];
  discovered_at: string;
}

export interface MatchAssessment {
  id: string;
  candidate_profile_id: string;
  job_offer_id: string;
  score: number;
  structured_score: number;
  semantic_score: number | null;
  recommendation: "strong_match" | "good_match" | "weak_match" | "blocked" | "needs_review";
  dimensions: Array<{
    id: string;
    name: string;
    score: number | null;
    weight: number;
    evidence: Array<{
      id: string;
      outcome: string;
      job_value: string;
      candidate_values: string[];
      explanation_code: string;
    }>;
  }>;
  gates: Array<{
    id: string;
    status: string;
    explanation_code: string;
  }>;
  assessed_at: string;
}

export interface TailoredResume {
  id: string;
  candidate_profile_id: string;
  job_offer_id: string;
  match_assessment_id: string;
  generation_version: string;
  status: "needs_review" | "approved" | "rejected";
  fragments: Array<{
    id: string;
    section: string;
    position: number;
    generated_text: string;
    method: "extractive" | "llm_rephrased";
    sources: Array<{
      id: string;
      source_type: string;
      source_id: string;
      source_text: string;
    }>;
  }>;
  created_at: string;
  reviewed_at: string | null;
}

export interface WorkspaceSnapshot {
  exported_at: string;
  schema_version: "1.0";
  candidate: CandidateProfile | null;
  job_offer: JobOffer | null;
  assessment: MatchAssessment | null;
  tailored_resume: TailoredResume | null;
}
