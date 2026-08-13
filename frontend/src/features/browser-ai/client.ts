import type { BrowserAIModel, GenerationResult } from "./types";
import {
  isBrowserAIWorkerEvent,
  type BrowserAIWorkerCommand,
  type BrowserAIWorkerEvent,
} from "./worker-protocol";

export type ProgressListener = (
  event: Extract<BrowserAIWorkerEvent, { type: "progress" }>,
) => void;

type PendingOperation = {
  resolve: (value: unknown) => void;
  reject: (reason: Error) => void;
  onProgress?: ProgressListener;
  onToken?: (text: string) => void;
};

export class BrowserAIClient {
  private readonly pending = new Map<string, PendingOperation>();

  public constructor(private readonly worker: Worker) {
    worker.addEventListener("message", this.onMessage);
    worker.addEventListener("error", this.onWorkerError);
  }

  public load(model: BrowserAIModel, onProgress?: ProgressListener): Promise<void> {
    return this.send<undefined>({ type: "load", requestId: crypto.randomUUID(), model }, { onProgress });
  }

  public generate(
    prompt: string,
    schema: Record<string, unknown>,
    onToken?: (text: string) => void,
  ): Promise<GenerationResult> {
    return this.send<GenerationResult>(
      {
        type: "generate",
        requestId: crypto.randomUUID(),
        prompt,
        schema,
        maxOutputTokens: 256,
      },
      { onToken },
    );
  }

  public cancel(): void {
    this.worker.postMessage({ type: "cancel", requestId: crypto.randomUUID() } satisfies BrowserAIWorkerCommand);
  }

  public clearCache(model: BrowserAIModel): Promise<void> {
    return this.send<undefined>({
      type: "clear-cache",
      requestId: crypto.randomUUID(),
      model,
    });
  }

  public async dispose(): Promise<void> {
    try {
      await this.send<undefined>({ type: "dispose", requestId: crypto.randomUUID() });
    } finally {
      this.worker.removeEventListener("message", this.onMessage);
      this.worker.removeEventListener("error", this.onWorkerError);
      this.worker.terminate();
      this.rejectAll("browser_ai_client_disposed");
    }
  }

  private send<T>(
    command: BrowserAIWorkerCommand,
    listeners: Pick<PendingOperation, "onProgress" | "onToken"> = {},
  ): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      this.pending.set(command.requestId, {
        resolve: (value) => { resolve(value as T); },
        reject,
        ...listeners,
      });
      this.worker.postMessage(command);
    });
  }

  private readonly onMessage = (message: MessageEvent<unknown>): void => {
    if (!isBrowserAIWorkerEvent(message.data)) return;
    const event = message.data;
    const operation = this.pending.get(event.requestId);
    if (!operation) return;

    if (event.type === "progress") operation.onProgress?.(event);
    if (event.type === "token") operation.onToken?.(event.text);
    if (event.type === "loaded" || event.type === "disposed" || event.type === "cache-cleared") {
      this.pending.delete(event.requestId);
      operation.resolve(undefined);
    }
    if (event.type === "completed") {
      this.pending.delete(event.requestId);
      operation.resolve({ text: event.text, metrics: event.metrics });
    }
    if (event.type === "cancelled" || event.type === "error") {
      this.pending.delete(event.requestId);
      operation.reject(new Error(event.type === "error" ? event.code : "browser_ai_cancelled"));
    }
  };

  private readonly onWorkerError = (): void => {
    this.rejectAll("browser_ai_worker_failed");
  };

  private rejectAll(code: string): void {
    for (const operation of this.pending.values()) operation.reject(new Error(code));
    this.pending.clear();
  }
}

export function createBrowserAIClient(): BrowserAIClient {
  return new BrowserAIClient(
    new Worker(new URL("./browser-ai.worker.ts", import.meta.url), { type: "module" }),
  );
}
