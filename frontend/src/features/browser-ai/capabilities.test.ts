import { describe, expect, it } from "vitest";

import { canRunBrowserAI, detectBrowserCapabilities } from "./capabilities";
import type { BrowserCapabilities } from "./types";

function fakeWindow(storageFails = false): Window {
  return {
    isSecureContext: true,
    crossOriginIsolated: false,
    navigator: {
      gpu: {},
      hardwareConcurrency: 8,
      deviceMemory: 16,
      storage: {
        estimate: storageFails
          ? () => Promise.reject(new Error("blocked"))
          : () => Promise.resolve({ quota: 10_000, usage: 1_000 }),
      },
    },
  } as unknown as Window;
}

describe("browser capability detection", () => {
  it("reports hardware and storage hints without requesting permissions", async () => {
    await expect(detectBrowserCapabilities(fakeWindow())).resolves.toMatchObject({
      secureContext: true,
      webGpu: true,
      hardwareConcurrency: 8,
      deviceMemoryGb: 16,
      storageQuotaBytes: 10_000,
      storageUsageBytes: 1_000,
    });
  });

  it("treats unavailable storage estimates as unknown", async () => {
    const result = await detectBrowserCapabilities(fakeWindow(true));
    expect(result.storageQuotaBytes).toBeNull();
    expect(result.storageUsageBytes).toBeNull();
  });

  it("requires secure WebGPU and WASM together", () => {
    const ready: BrowserCapabilities = {
      secureContext: true,
      crossOriginIsolated: false,
      webAssembly: true,
      webGpu: true,
      hardwareConcurrency: null,
      deviceMemoryGb: null,
      storageQuotaBytes: null,
      storageUsageBytes: null,
    };
    expect(canRunBrowserAI(ready)).toBe(true);
    expect(canRunBrowserAI({ ...ready, webGpu: false })).toBe(false);
    expect(canRunBrowserAI({ ...ready, secureContext: false })).toBe(false);
    expect(canRunBrowserAI({ ...ready, webAssembly: false })).toBe(false);
  });
});
