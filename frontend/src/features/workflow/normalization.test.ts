import { describe, expect, it } from "vitest";

import { buildManualNormalization } from "./normalization";

const rawText = "Acme Labs seeks a Backend Engineer in Madrid. Python is required. Docker is preferred.";

describe("buildManualNormalization", () => {
  it("creates exact evidence for fields and classified requirements", () => {
    const result = buildManualNormalization({
      rawText,
      company: "Acme Labs",
      title: "Backend Engineer",
      location: "Madrid",
      requirements: "required | skill | Python\npreferred | skill | Docker",
    });

    expect(result.title?.evidence).toEqual({ quote: "Backend Engineer", start_offset: 18, end_offset: 34 });
    expect(result.requirements).toHaveLength(2);
    expect(result.requirements[1]).toMatchObject({ priority: "preferred", normalized_value: "Docker" });
    expect(result.warnings).toEqual([]);
  });

  it("rejects values that do not occur verbatim in the untrusted source", () => {
    expect(() => buildManualNormalization({
      rawText,
      company: "Invented Company",
      title: "",
      location: "",
      requirements: "",
    })).toThrow(/must appear exactly/i);
  });

  it.each([
    ["", "Paste the source"],
    ["required | Python", "must use priority"],
    ["mandatory | skill | Python", "unsupported priority"],
    ["required | magic | Python", "unsupported type"],
    ["required | skill | ", "missing its exact quote"],
  ])("rejects malformed input %s", (requirements, message) => {
    const source = requirements ? rawText : "";
    expect(() => buildManualNormalization({
      rawText: source,
      company: "",
      title: "",
      location: "",
      requirements,
    })).toThrow(message);
  });

  it("records a warning when the user selects no requirements", () => {
    const result = buildManualNormalization({ rawText, company: "", title: "", location: "", requirements: "" });
    expect(result.requirements).toEqual([]);
    expect(result.warnings).toHaveLength(1);
  });
});
