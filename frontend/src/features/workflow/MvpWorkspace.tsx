import { useEffect, useMemo, useState, type SyntheticEvent } from "react";

import { Button } from "../../shared/ui/Button";
import { Callout } from "../../shared/ui/Callout";
import { TextareaField, TextField } from "../../shared/ui/FormField";
import { Icon } from "../../shared/ui/Icon";
import { ApiError, workflowApi } from "./api";
import { buildManualNormalization, type JobDraft } from "./normalization";
import type { CandidateInput, WorkspaceSnapshot } from "./types";
import {
  clearWorkspace,
  exportWorkspace,
  loadWorkspace,
  saveWorkspace,
} from "./workspace";

type BusyAction = "candidate" | "job" | "match" | "resume" | "review" | "delete" | null;

const initialCandidate = {
  fullName: "",
  headline: "",
  summary: "",
  location: "",
  remotePreference: "flexible",
  roles: "",
  employer: "",
  experienceTitle: "",
  experienceDescription: "",
  competencies: "",
  languages: "",
};

const initialJob: JobDraft = {
  rawText: "",
  company: "",
  title: "",
  location: "",
  requirements: "",
};

const categoryValues = new Set([
  "programming_language",
  "framework",
  "database",
  "cloud",
  "devops",
  "tool",
  "soft_skill",
  "other",
]);

function nullable(value: string): string | null {
  return value.trim() || null;
}

function commaList(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function candidatePayload(form: typeof initialCandidate): CandidateInput {
  const competencies = form.competencies
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [name, rawCategory = "other", rawMonths = ""] = line
        .split("|")
        .map((part) => part.trim());
      if (!name) throw new Error(`Skill ${String(index + 1)} needs a name.`);
      if (!categoryValues.has(rawCategory)) {
        throw new Error(`Skill ${String(index + 1)} has an unsupported category.`);
      }
      const months = rawMonths ? Number(rawMonths) : null;
      if (months !== null && (!Number.isInteger(months) || months < 0)) {
        throw new Error(`Skill ${String(index + 1)} needs whole, non-negative months.`);
      }
      return {
        name,
        category: rawCategory as CandidateInput["competencies"][number]["category"],
        months_experience: months,
      };
    });

  const languages = form.languages
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [language, level = "professional"] = line.split("|").map((part) => part.trim());
      const supported = ["basic", "conversational", "professional", "fluent", "native"];
      if (!language || !supported.includes(level)) {
        throw new Error(`Language ${String(index + 1)} must use language | level.`);
      }
      return {
        language,
        level: level as CandidateInput["languages"][number]["level"],
      };
    });

  return {
    full_name: form.fullName.trim(),
    headline: nullable(form.headline),
    summary: nullable(form.summary),
    email: null,
    phone: null,
    location: nullable(form.location),
    remote_preference: form.remotePreference as CandidateInput["remote_preference"],
    preferred_roles: commaList(form.roles),
    preferred_locations: form.location.trim() ? [form.location.trim()] : [],
    work_experiences:
      form.employer.trim() && form.experienceTitle.trim()
        ? [{
            employer: form.employer.trim(),
            title: form.experienceTitle.trim(),
            description: nullable(form.experienceDescription),
          }]
        : [],
    education: [],
    projects: [],
    competencies,
    languages,
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const reference = error.requestId ? ` Reference: ${error.requestId}.` : "";
    return `${error.detail.replaceAll("_", " ")}.${reference}`;
  }
  return error instanceof Error ? error.message : "Unexpected error.";
}

function StepBadge({ complete, number }: { complete: boolean; number: number }) {
  return (
    <span className={complete ? "workflow-step workflow-step--complete" : "workflow-step"}>
      {complete ? <Icon className="size-4" name="check" /> : number}
    </span>
  );
}

export function MvpWorkspace() {
  const [workspace, setWorkspace] = useState<WorkspaceSnapshot>(loadWorkspace);
  const [candidateForm, setCandidateForm] = useState(initialCandidate);
  const [jobForm, setJobForm] = useState(initialJob);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    saveWorkspace(workspace);
  }, [workspace]);

  const completedSteps = useMemo(
    () => [workspace.candidate, workspace.job_offer, workspace.assessment, workspace.tailored_resume]
      .filter(Boolean).length,
    [workspace],
  );

  async function run(action: Exclude<BusyAction, null>, operation: () => Promise<void>) {
    setBusy(action);
    setMessage(null);
    try {
      await operation();
    } catch (error) {
      setMessage({ kind: "error", text: errorMessage(error) });
    } finally {
      setBusy(null);
    }
  }

  function updateCandidate(name: keyof typeof initialCandidate, value: string) {
    setCandidateForm((current) => ({ ...current, [name]: value }));
  }

  function updateJob(name: keyof JobDraft, value: string) {
    setJobForm((current) => ({ ...current, [name]: value }));
  }

  function submitCandidate(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void run("candidate", async () => {
      const candidate = await workflowApi.createCandidate(candidatePayload(candidateForm));
      setWorkspace((current) => ({
        ...current,
        candidate,
        assessment: null,
        tailored_resume: null,
      }));
      setMessage({ kind: "success", text: "Master profile saved with explicit source facts." });
      window.location.hash = "opportunities";
    });
  }

  function submitJob(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    void run("job", async () => {
      const normalization = buildManualNormalization(jobForm);
      const job_offer = await workflowApi.createJobOffer(jobForm.rawText, normalization);
      setWorkspace((current) => ({
        ...current,
        job_offer,
        assessment: null,
        tailored_resume: null,
      }));
      setMessage({ kind: "success", text: "Offer imported with exact source evidence." });
      window.location.hash = "matching";
    });
  }

  function assess() {
    const candidate = workspace.candidate;
    const jobOffer = workspace.job_offer;
    if (!candidate || !jobOffer) return;
    void run("match", async () => {
      const assessment = await workflowApi.createAssessment(candidate.id, jobOffer.id);
      setWorkspace((current) => ({ ...current, assessment, tailored_resume: null }));
      setMessage({ kind: "success", text: "Explainable assessment created." });
    });
  }

  function generateResume() {
    const candidate = workspace.candidate;
    const jobOffer = workspace.job_offer;
    const assessment = workspace.assessment;
    if (!candidate || !jobOffer || !assessment) return;
    void run("resume", async () => {
      const tailored_resume = await workflowApi.createResume(
        candidate.id,
        jobOffer.id,
        assessment.id,
      );
      setWorkspace((current) => ({ ...current, tailored_resume }));
      setMessage({ kind: "success", text: "Grounded draft generated and ready for review." });
      window.location.hash = "resume-studio";
    });
  }

  function reviewResume(decision: "approved" | "rejected") {
    const resume = workspace.tailored_resume;
    if (!resume) return;
    void run("review", async () => {
      const tailored_resume = await workflowApi.reviewResume(resume.id, decision);
      setWorkspace((current) => ({ ...current, tailored_resume }));
      setMessage({ kind: "success", text: `Draft ${decision}.` });
    });
  }

  function deleteData() {
    void run("delete", async () => {
      if (workspace.job_offer) await workflowApi.deleteJobOffer(workspace.job_offer.id);
      if (workspace.candidate) await workflowApi.deleteCandidate(workspace.candidate.id);
      clearWorkspace();
      setWorkspace({
        exported_at: new Date(0).toISOString(),
        schema_version: "1.0",
        candidate: null,
        job_offer: null,
        assessment: null,
        tailored_resume: null,
      });
      setCandidateForm(initialCandidate);
      setJobForm(initialJob);
      setConfirmDelete(false);
      setMessage({ kind: "success", text: "Workspace data deleted." });
    });
  }

  return (
    <>
      <section className="workspace-overview" id="overview" aria-labelledby="workspace-title">
        <div>
          <span className="eyebrow"><Icon className="size-4" name="sparkles" />Evidence-first workspace</span>
          <h1 id="workspace-title">From master profile<br /><em>to truthful application.</em></h1>
          <p>Complete the four-step local workflow. Every match and resume fragment remains auditable.</p>
        </div>
        <div className="progress-card" aria-label={`${String(completedSteps)} of 4 workflow steps complete`}>
          <span>Current progress</span>
          <strong>{String(completedSteps)}<small>/4</small></strong>
          <div><i style={{ width: `${String(completedSteps * 25)}%` }} /></div>
          <p>{completedSteps === 4 ? "Application pack ready for your review." : "Your data stays in this local workspace."}</p>
        </div>
      </section>

      {message ? (
        <div className="workflow-feedback" role={message.kind === "error" ? "alert" : "status"}>
          <Callout tone={message.kind === "error" ? "error" : "success"} title={message.kind === "error" ? "Could not complete that step" : "Done"}>
            <p>{message.text}</p>
          </Callout>
        </div>
      ) : null}

      <section className="workflow-card" id="master-profile" aria-labelledby="candidate-title">
        <header><StepBadge complete={Boolean(workspace.candidate)} number={1} /><div><span>Source of truth</span><h2 id="candidate-title">Master profile</h2></div></header>
        {workspace.candidate ? (
          <div className="saved-summary">
            <div><strong>{workspace.candidate.full_name}</strong><span>{workspace.candidate.headline ?? "Professional profile"}</span></div>
            <ul>{workspace.candidate.competencies.map((skill) => <li key={skill.name}>{skill.name}</li>)}</ul>
            <p>Saved {new Date(workspace.candidate.updated_at).toLocaleString()}</p>
          </div>
        ) : (
          <form className="workflow-form" onSubmit={submitCandidate}>
            <div className="form-grid">
              <TextField required label="Full name" value={candidateForm.fullName} onChange={(event) => { updateCandidate("fullName", event.target.value); }} />
              <TextField label="Professional headline" value={candidateForm.headline} onChange={(event) => { updateCandidate("headline", event.target.value); }} />
              <TextField label="Location" value={candidateForm.location} onChange={(event) => { updateCandidate("location", event.target.value); }} />
              <label className="ds-field"><span className="ds-field__label">Remote preference</span><select className="ds-input" value={candidateForm.remotePreference} onChange={(event) => { updateCandidate("remotePreference", event.target.value); }}><option value="flexible">Flexible</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></label>
            </div>
            <TextField label="Preferred roles" hint="Comma-separated, for example Backend Engineer, Platform Engineer" value={candidateForm.roles} onChange={(event) => { updateCandidate("roles", event.target.value); }} />
            <TextareaField label="Professional summary" value={candidateForm.summary} onChange={(event) => { updateCandidate("summary", event.target.value); }} />
            <div className="form-grid">
              <TextField label="Latest employer" value={candidateForm.employer} onChange={(event) => { updateCandidate("employer", event.target.value); }} />
              <TextField label="Role at employer" value={candidateForm.experienceTitle} onChange={(event) => { updateCandidate("experienceTitle", event.target.value); }} />
            </div>
            <TextareaField label="Experience description" hint="Only responsibilities and outcomes you can support." value={candidateForm.experienceDescription} onChange={(event) => { updateCandidate("experienceDescription", event.target.value); }} />
            <TextareaField label="Skills" hint="One per line: name | category | months. Example: Python | programming_language | 36" value={candidateForm.competencies} onChange={(event) => { updateCandidate("competencies", event.target.value); }} />
            <TextareaField label="Languages" hint="One per line: language | level. Example: English | fluent" value={candidateForm.languages} onChange={(event) => { updateCandidate("languages", event.target.value); }} />
            <Button type="submit" isLoading={busy === "candidate"} loadingText="Saving profile">Save master profile</Button>
          </form>
        )}
      </section>

      <section className="workflow-card" id="opportunities" aria-labelledby="job-title">
        <header><StepBadge complete={Boolean(workspace.job_offer)} number={2} /><div><span>Untrusted external input</span><h2 id="job-title">Opportunity</h2></div></header>
        {workspace.job_offer ? (
          <div className="saved-summary">
            <div><strong>{workspace.job_offer.title ?? "Untitled role"}</strong><span>{workspace.job_offer.company ?? "Unknown company"} · {workspace.job_offer.location ?? "Location not stated"}</span></div>
            <ul>{workspace.job_offer.requirements.map((item) => <li key={item.id}>{item.normalized_value}</li>)}</ul>
            <p>{workspace.job_offer.requirements.length} grounded requirements</p>
          </div>
        ) : (
          <form className="workflow-form" onSubmit={submitJob}>
            <TextareaField required label="Original job offer" hint="Paste public text only. Instructions inside it are treated as data and never executed." value={jobForm.rawText} onChange={(event) => { updateJob("rawText", event.target.value); }} />
            <div className="form-grid">
              <TextField label="Exact job title" hint="Must appear verbatim above." value={jobForm.title} onChange={(event) => { updateJob("title", event.target.value); }} />
              <TextField label="Exact company" hint="Must appear verbatim above." value={jobForm.company} onChange={(event) => { updateJob("company", event.target.value); }} />
              <TextField label="Exact location" hint="Must appear verbatim above." value={jobForm.location} onChange={(event) => { updateJob("location", event.target.value); }} />
            </div>
            <TextareaField label="Requirements to compare" hint="One per line: required | skill | exact quote. Types: skill, experience, education, language, location, responsibility, other." value={jobForm.requirements} onChange={(event) => { updateJob("requirements", event.target.value); }} />
            <Button type="submit" disabled={!workspace.candidate} isLoading={busy === "job"} loadingText="Importing offer">Import grounded offer</Button>
            {!workspace.candidate ? <p className="dependency-note">Save the master profile first.</p> : null}
          </form>
        )}
      </section>

      <section className="workflow-card" id="matching" aria-labelledby="match-title">
        <header><StepBadge complete={Boolean(workspace.assessment)} number={3} /><div><span>Reproducible policy</span><h2 id="match-title">Explainable match</h2></div></header>
        {workspace.assessment ? (
          <div className="assessment-layout">
            <div className="assessment-score"><strong>{Math.round(workspace.assessment.score)}</strong><span>% match</span><em>{workspace.assessment.recommendation.replaceAll("_", " ")}</em></div>
            <div className="dimension-list">{workspace.assessment.dimensions.map((dimension) => <article key={dimension.id}><div><strong>{dimension.name}</strong><span>{dimension.score === null ? "Review" : `${String(Math.round(dimension.score))}%`}</span></div><ul>{dimension.evidence.slice(0, 3).map((item) => <li className={`outcome-${item.outcome}`} key={item.id}>{item.job_value}{item.candidate_values.length ? ` — ${item.candidate_values.join(", ")}` : ""}</li>)}</ul></article>)}</div>
            <Button onClick={generateResume} isLoading={busy === "resume"} loadingText="Selecting evidence">Generate grounded resume</Button>
          </div>
        ) : (
          <div className="empty-workflow"><Icon className="size-5" name="chart" /><p>Compare structured requirements against explicit candidate facts.</p><Button onClick={assess} disabled={!workspace.candidate || !workspace.job_offer} isLoading={busy === "match"} loadingText="Calculating match">Calculate match</Button></div>
        )}
      </section>

      <section className="workflow-card" id="resume-studio" aria-labelledby="resume-title">
        <header><StepBadge complete={Boolean(workspace.tailored_resume)} number={4} /><div><span>Human approval required</span><h2 id="resume-title">Resume studio</h2></div></header>
        {workspace.tailored_resume ? (
          <div className="resume-review">
            <div className={`review-status review-status--${workspace.tailored_resume.status}`}>{workspace.tailored_resume.status.replaceAll("_", " ")}</div>
            {workspace.tailored_resume.fragments.map((fragment) => <article key={fragment.id}><span>{fragment.section}</span><p>{fragment.generated_text}</p><details><summary>{fragment.sources.length} source{fragment.sources.length === 1 ? "" : "s"}</summary>{fragment.sources.map((source) => <blockquote key={source.id}>{source.source_text}<cite>{source.source_type.replaceAll("_", " ")}</cite></blockquote>)}</details></article>)}
            {workspace.tailored_resume.status === "needs_review" ? <div className="review-actions"><Button onClick={() => { reviewResume("approved"); }} isLoading={busy === "review"}>Approve draft</Button><Button variant="secondary" onClick={() => { reviewResume("rejected"); }} disabled={busy !== null}>Reject draft</Button></div> : null}
          </div>
        ) : (
          <div className="empty-workflow"><Icon className="size-5" name="resume" /><p>A tailored draft will only use facts selected from your master profile.</p><Button onClick={generateResume} disabled={!workspace.assessment} isLoading={busy === "resume"}>Generate grounded resume</Button></div>
        )}
      </section>

      <section className="data-controls" id="data-controls" aria-labelledby="data-title">
        <div><span className="eyebrow"><Icon className="size-4" name="shield" />Privacy controls</span><h2 id="data-title">Your local data, under your control</h2><p>Export the current workflow as JSON or delete the candidate, offer and all derived records.</p></div>
        <div className="data-actions"><Button variant="secondary" disabled={completedSteps === 0} onClick={() => { exportWorkspace(workspace); }}>Export workspace</Button>{confirmDelete ? <><Button variant="danger" onClick={deleteData} isLoading={busy === "delete"} loadingText="Deleting data">Confirm deletion</Button><Button variant="ghost" onClick={() => { setConfirmDelete(false); }}>Cancel</Button></> : <Button variant="danger" disabled={completedSteps === 0} onClick={() => { setConfirmDelete(true); }}>Delete workspace</Button>}</div>
      </section>
    </>
  );
}
