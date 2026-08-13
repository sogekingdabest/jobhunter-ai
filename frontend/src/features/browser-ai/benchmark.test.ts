import { describe, expect, it } from "vitest";

import { benchmarkCases, evaluateBenchmarkResult } from "./benchmark";

const metrics = {
  timeToFirstTokenMs: 10,
  totalTimeMs: 50,
  outputTokens: 5,
  tokensPerSecond: 100,
};

describe("browser AI benchmark", () => {
  it("uses equivalent fictional fixtures in English and Spanish", () => {
    expect(benchmarkCases.map((fixture) => fixture.language)).toEqual(["en", "es"]);
    expect(benchmarkCases.every((fixture) => fixture.prompt.includes("Alex"))).toBe(true);
  });

  it("distinguishes JSON parsing from schema adherence", () => {
    const fixture = benchmarkCases[0];
    expect(fixture).toBeDefined();
    if (!fixture) return;

    expect(
      evaluateBenchmarkResult(fixture, {
        text: JSON.stringify({ role: "Backend Engineer", skills: ["Python", "SQL"] }),
        metrics,
      }),
    ).toMatchObject({ validJson: true, schemaValid: true });
    expect(
      evaluateBenchmarkResult(fixture, { text: JSON.stringify({ role: 7 }), metrics }),
    ).toMatchObject({ validJson: true, schemaValid: false });
    expect(evaluateBenchmarkResult(fixture, { text: "not json", metrics })).toMatchObject({
      validJson: false,
      schemaValid: false,
    });
  });
});
