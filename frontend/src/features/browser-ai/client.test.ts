import { describe, expect, it, vi } from "vitest";

import { browserAIModels } from "./catalog";
import { BrowserAIClient } from "./client";
import type { BrowserAIWorkerCommand, BrowserAIWorkerEvent } from "./worker-protocol";

class FakeWorker extends EventTarget {
  public readonly commands: BrowserAIWorkerCommand[] = [];
  public readonly terminate = vi.fn();

  public postMessage(command: BrowserAIWorkerCommand): void {
    this.commands.push(command);
  }

  public emit(event: BrowserAIWorkerEvent): void {
    this.dispatchEvent(new MessageEvent("message", { data: event }));
  }
}

function latestCommand(worker: FakeWorker): BrowserAIWorkerCommand {
  const command = worker.commands.at(-1);
  if (!command) throw new Error("missing_worker_command");
  return command;
}

describe("BrowserAIClient", () => {
  it("routes progress and completion by opaque request id", async () => {
    const worker = new FakeWorker();
    const client = new BrowserAIClient(worker as unknown as Worker);
    const progress = vi.fn();
    const load = client.load(browserAIModels[0], progress);
    const loadCommand = latestCommand(worker);

    worker.emit({
      type: "progress",
      requestId: loadCommand.requestId,
      phase: "download",
      progress: 0.5,
      message: "halfway",
    });
    worker.emit({ type: "loaded", requestId: loadCommand.requestId });
    await expect(load).resolves.toBeUndefined();
    expect(progress).toHaveBeenCalledOnce();

    const onToken = vi.fn();
    const generation = client.generate("prompt", {}, onToken);
    const generationCommand = latestCommand(worker);
    worker.emit({ type: "token", requestId: generationCommand.requestId, text: "{" });
    worker.emit({
      type: "completed",
      requestId: generationCommand.requestId,
      text: "{}",
      metrics: {
        timeToFirstTokenMs: 5,
        totalTimeMs: 10,
        outputTokens: 2,
        tokensPerSecond: 200,
      },
    });

    await expect(generation).resolves.toMatchObject({ text: "{}" });
    expect(onToken).toHaveBeenCalledWith("{");
  });

  it("uses categorical errors and terminates after disposal", async () => {
    const worker = new FakeWorker();
    const client = new BrowserAIClient(worker as unknown as Worker);
    const generation = client.generate("prompt", {});
    const generationCommand = latestCommand(worker);
    worker.emit({
      type: "error",
      requestId: generationCommand.requestId,
      code: "browser_ai_runtime_failed",
    });
    await expect(generation).rejects.toThrow("browser_ai_runtime_failed");

    const disposal = client.dispose();
    const disposeCommand = latestCommand(worker);
    worker.emit({ type: "disposed", requestId: disposeCommand.requestId });
    await disposal;
    expect(worker.terminate).toHaveBeenCalledOnce();
  });

  it("sends explicit cancellation and cache cleanup commands", async () => {
    const worker = new FakeWorker();
    const client = new BrowserAIClient(worker as unknown as Worker);
    client.cancel();
    expect(latestCommand(worker).type).toBe("cancel");

    const clearing = client.clearCache(browserAIModels[2]);
    const clearCommand = latestCommand(worker);
    expect(clearCommand.type).toBe("clear-cache");
    worker.emit({ type: "cache-cleared", requestId: clearCommand.requestId });
    await expect(clearing).resolves.toBeUndefined();
  });
});
