import { describe, expect, it } from "vitest";

import { browserAIModels, findBrowserAIModel, formatBytes } from "./catalog";

describe("browser AI model catalog", () => {
  it("pins models to runtime-specific immutable references", () => {
    expect(browserAIModels).toHaveLength(3);
    expect(browserAIModels.filter((model) => model.runtime === "litert-lm")).toHaveLength(2);
    for (const model of browserAIModels) {
      expect(model.downloadBytes).toBeGreaterThan(0);
      expect(model.revision).not.toBe("main");
      expect(model.license).not.toHaveLength(0);
    }
  });

  it("finds known models and formats decimal download sizes", () => {
    expect(findBrowserAIModel("gemma-4-e2b-it-litert-web")?.name).toBe("Gemma 4 E2B IT");
    expect(findBrowserAIModel("missing")).toBeUndefined();
    expect(formatBytes(2_000_000_000)).toBe("2 GB");
  });
});
