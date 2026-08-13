export type BrowserAIRuntime = "litert-lm" | "webllm";

export type BrowserAIModel = Readonly<{
  id: string;
  name: string;
  runtime: BrowserAIRuntime;
  modelReference: string;
  revision: string;
  license: string;
  downloadBytes: number;
  recommendedMemoryGb: number;
  contextTokens: number;
  languages: readonly string[];
  structuredOutput: "json-schema" | "validated-json";
  sha256?: string;
  experimental: boolean;
}>;

export type BrowserCapabilities = Readonly<{
  secureContext: boolean;
  crossOriginIsolated: boolean;
  webAssembly: boolean;
  webGpu: boolean;
  hardwareConcurrency: number | null;
  deviceMemoryGb: number | null;
  storageQuotaBytes: number | null;
  storageUsageBytes: number | null;
}>;

export type BenchmarkLanguage = "en" | "es";

export type BenchmarkCase = Readonly<{
  id: string;
  language: BenchmarkLanguage;
  prompt: string;
  schema: Record<string, unknown>;
}>;

export type GenerationMetrics = Readonly<{
  timeToFirstTokenMs: number | null;
  totalTimeMs: number;
  outputTokens: number | null;
  tokensPerSecond: number | null;
}>;

export type GenerationResult = Readonly<{
  text: string;
  metrics: GenerationMetrics;
}>;

export type BenchmarkResult = Readonly<{
  caseId: string;
  language: BenchmarkLanguage;
  validJson: boolean;
  schemaValid: boolean;
  cancelled: boolean;
  metrics: GenerationMetrics;
}>;
