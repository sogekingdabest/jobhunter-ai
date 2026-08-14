import type { JobNormalization } from "./types";

export interface JobDraft {
  rawText: string;
  company: string;
  title: string;
  location: string;
  requirements: string;
}

const requirementTypes = new Set([
  "skill",
  "experience",
  "education",
  "language",
  "location",
  "responsibility",
  "other",
]);
const priorities = new Set(["required", "preferred", "unspecified"]);

function evidence(rawText: string, quote: string) {
  const start = rawText.indexOf(quote);
  if (start < 0) {
    throw new Error(`“${quote}” must appear exactly in the pasted offer.`);
  }
  return { quote, start_offset: start, end_offset: start + quote.length };
}

function grounded(rawText: string, value: string) {
  const trimmed = value.trim();
  return trimmed
    ? { value: trimmed, evidence: evidence(rawText, trimmed), confidence: 1 }
    : null;
}

export function buildManualNormalization(draft: JobDraft): JobNormalization {
  const rawText = draft.rawText;
  if (!rawText.trim()) {
    throw new Error("Paste the source job offer before importing it.");
  }

  const requirements = draft.requirements
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const parts = line.split("|").map((part) => part.trim());
      if (parts.length !== 3) {
        throw new Error(`Requirement ${String(index + 1)} must use priority | type | exact quote.`);
      }
      const [priority, requirementType, quote] = parts;
      if (!priority || !priorities.has(priority)) {
        throw new Error(`Requirement ${String(index + 1)} has an unsupported priority.`);
      }
      if (!requirementType || !requirementTypes.has(requirementType)) {
        throw new Error(`Requirement ${String(index + 1)} has an unsupported type.`);
      }
      if (!quote) {
        throw new Error(`Requirement ${String(index + 1)} is missing its exact quote.`);
      }
      return {
        requirement_type: requirementType as JobNormalization["requirements"][number]["requirement_type"],
        priority: priority as JobNormalization["requirements"][number]["priority"],
        normalized_value: quote,
        evidence: evidence(rawText, quote),
        confidence: 1,
      };
    });

  return {
    contract_version: "1.0",
    company: grounded(rawText, draft.company),
    title: grounded(rawText, draft.title),
    location: grounded(rawText, draft.location),
    remote_type: null,
    employment_type: null,
    seniority: null,
    requirements,
    warnings: requirements.length ? [] : ["No requirements were selected by the user."],
  };
}
