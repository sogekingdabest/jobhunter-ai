import { describe, expect, it } from "vitest";

import { isBrowserAIWorkerEvent } from "./worker-protocol";

describe("browser AI worker protocol", () => {
  it("accepts known events and rejects malformed or unknown messages", () => {
    expect(isBrowserAIWorkerEvent({ type: "loaded", requestId: "one" })).toBe(true);
    expect(isBrowserAIWorkerEvent({ type: "invented", requestId: "one" })).toBe(false);
    expect(isBrowserAIWorkerEvent({ type: "loaded" })).toBe(false);
    expect(isBrowserAIWorkerEvent(null)).toBe(false);
  });
});
