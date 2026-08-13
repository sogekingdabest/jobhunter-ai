import type { BrowserAIModel } from "./types";

export const browserAIModels = [
  {
    id: "gemma-4-e2b-it-litert-web",
    name: "Gemma 4 E2B IT",
    runtime: "litert-lm",
    modelReference:
      "https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/73d35ec/gemma-4-E2B-it-web.litertlm",
    revision: "73d35ec",
    license: "Apache-2.0",
    downloadBytes: 2_008_432_640,
    recommendedMemoryGb: 8,
    contextTokens: 8_192,
    languages: ["English", "Spanish", "multilingual"],
    structuredOutput: "validated-json",
    sha256: "3a08e8d94e23b814ae5414469c370c503813949acb8ceaa17e4ebf8a35af35b5",
    experimental: true,
  },
  {
    id: "gemma-4-e4b-it-litert-web",
    name: "Gemma 4 E4B IT",
    runtime: "litert-lm",
    modelReference:
      "https://huggingface.co/litert-community/gemma-4-E4B-it-litert-lm/resolve/4f479a5/gemma-4-E4B-it-web.litertlm",
    revision: "4f479a5",
    license: "Apache-2.0",
    downloadBytes: 2_970_000_000,
    recommendedMemoryGb: 12,
    contextTokens: 8_192,
    languages: ["English", "Spanish", "multilingual"],
    structuredOutput: "validated-json",
    sha256: "3904d826d5dddd25ea173e85204caec09e68ba038116e9b992b69cbdc94f57a0",
    experimental: true,
  },
  {
    id: "llama-3.2-1b-webllm",
    name: "Llama 3.2 1B Instruct",
    runtime: "webllm",
    modelReference: "Llama-3.2-1B-Instruct-q4f16_1-MLC",
    revision: "webllm-0.2.84-model-v0_2_84",
    license: "Llama 3.2 Community License",
    downloadBytes: 879_040_000,
    recommendedMemoryGb: 4,
    contextTokens: 4_096,
    languages: ["English", "Spanish"],
    structuredOutput: "json-schema",
    experimental: false,
  },
] as const satisfies readonly BrowserAIModel[];

export function findBrowserAIModel(modelId: string): BrowserAIModel | undefined {
  return browserAIModels.find((model) => model.id === modelId);
}

export function formatBytes(bytes: number): string {
  return new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(
    bytes / 1_000_000_000,
  ) + " GB";
}
