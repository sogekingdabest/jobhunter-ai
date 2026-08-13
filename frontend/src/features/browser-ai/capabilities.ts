import type { BrowserCapabilities } from "./types";

type NavigatorWithDeviceMemory = Omit<Navigator, "storage"> & {
  readonly deviceMemory?: number;
  readonly storage?: Pick<StorageManager, "estimate">;
};

export async function detectBrowserCapabilities(
  browser: Window = window,
): Promise<BrowserCapabilities> {
  const navigatorWithMemory = browser.navigator as NavigatorWithDeviceMemory;
  const estimate = await navigatorWithMemory.storage?.estimate().catch(() => undefined);

  return {
    secureContext: browser.isSecureContext === true,
    crossOriginIsolated: browser.crossOriginIsolated === true,
    webAssembly: typeof WebAssembly === "object",
    webGpu: "gpu" in navigatorWithMemory,
    hardwareConcurrency: navigatorWithMemory.hardwareConcurrency || null,
    deviceMemoryGb: navigatorWithMemory.deviceMemory ?? null,
    storageQuotaBytes: estimate?.quota ?? null,
    storageUsageBytes: estimate?.usage ?? null,
  };
}

export function canRunBrowserAI(capabilities: BrowserCapabilities): boolean {
  return capabilities.secureContext && capabilities.webAssembly && capabilities.webGpu;
}
