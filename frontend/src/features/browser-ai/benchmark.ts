import { Validator } from "@cfworker/json-schema";

import type { BenchmarkCase, BenchmarkResult, GenerationResult } from "./types";

const factSchema = {
  type: "object",
  additionalProperties: false,
  required: ["role", "skills"],
  properties: {
    role: { type: "string" },
    skills: { type: "array", items: { type: "string" }, maxItems: 5 },
  },
} as const;

export const benchmarkCases: readonly BenchmarkCase[] = [
  {
    id: "candidate-facts-en",
    language: "en",
    prompt:
      "Return JSON only. From this fictional statement, extract the role and skills: Alex Example worked as a Backend Engineer and used Python and SQL.",
    schema: factSchema,
  },
  {
    id: "candidate-facts-es",
    language: "es",
    prompt:
      "Devuelve solo JSON. Extrae el puesto y las habilidades de esta frase ficticia: Alex Ejemplo trabajó como Backend Engineer usando Python y SQL.",
    schema: factSchema,
  },
];

export function evaluateBenchmarkResult(
  benchmarkCase: BenchmarkCase,
  generation: GenerationResult,
): BenchmarkResult {
  try {
    const output: unknown = JSON.parse(generation.text);
    const validator = new Validator(benchmarkCase.schema);
    const schemaValid = validator.validate(output).valid;
    return {
      caseId: benchmarkCase.id,
      language: benchmarkCase.language,
      validJson: true,
      schemaValid,
      cancelled: false,
      metrics: generation.metrics,
    };
  } catch {
    return {
      caseId: benchmarkCase.id,
      language: benchmarkCase.language,
      validJson: false,
      schemaValid: false,
      cancelled: false,
      metrics: generation.metrics,
    };
  }
}
