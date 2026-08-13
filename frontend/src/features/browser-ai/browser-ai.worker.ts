/// <reference lib="webworker" />

import type { BrowserAIModel, GenerationMetrics } from "./types";
import type { BrowserAIWorkerCommand, BrowserAIWorkerEvent } from "./worker-protocol";

type RuntimeAdapter = {
  load(model: BrowserAIModel, requestId: string): Promise<void>;
  generate(
    prompt: string,
    schema: Record<string, unknown>,
    maxOutputTokens: number,
    requestId: string,
  ): Promise<{ text: string; metrics: GenerationMetrics }>;
  cancel(): void;
  dispose(): Promise<void>;
};

const worker = self as DedicatedWorkerGlobalScope;
let adapter: RuntimeAdapter | undefined;
let activeOperation: { cancelled: boolean } | undefined;

function emit(event: BrowserAIWorkerEvent): void {
  worker.postMessage(event);
}

function safeErrorCode(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") return "browser_ai_cancelled";
  return "browser_ai_runtime_failed";
}

function isCancelled(operation: { cancelled: boolean }): boolean {
  return operation.cancelled;
}

class LiteRTRuntimeAdapter implements RuntimeAdapter {
  private engine: import("@litert-lm/core").Engine | undefined;
  private conversation: import("@litert-lm/core").Conversation | undefined;
  private downloadController: AbortController | undefined;

  public async load(model: BrowserAIModel, requestId: string): Promise<void> {
    this.downloadController = new AbortController();
    const response = await fetch(model.modelReference, { signal: this.downloadController.signal });
    if (!response.ok || !response.body) throw new Error("model_download_failed");
    const total = Number(response.headers.get("content-length")) || model.downloadBytes;
    let loaded = 0;
    const reader = response.body.getReader();
    const chunks: ArrayBuffer[] = [];
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      chunks.push(chunk.value.slice().buffer);
      loaded += chunk.value.byteLength;
      emit({
        type: "progress",
        requestId,
        phase: "download",
        progress: Math.min(loaded / total, 1),
        loadedBytes: loaded,
        totalBytes: total,
        message: "Downloading model",
      });
    }
    emit({ type: "progress", requestId, phase: "initialize", progress: 0, message: "Initializing LiteRT-LM" });
    const { Engine } = await import("@litert-lm/core");
    this.engine = await Engine.create({
      model: new Blob(chunks),
      benchmarkEnabled: true,
      mainExecutorSettings: { maxNumTokens: model.contextTokens },
    });
    this.conversation = await this.engine.createConversation({ enableConstrainedDecoding: true });
    emit({ type: "progress", requestId, phase: "initialize", progress: 1, message: "Ready" });
  }

  public async generate(
    prompt: string,
    schema: Record<string, unknown>,
    _maxOutputTokens: number,
    requestId: string,
  ): Promise<{ text: string; metrics: GenerationMetrics }> {
    if (!this.conversation) throw new Error("model_not_loaded");
    const startedAt = performance.now();
    let firstTokenAt: number | null = null;
    let text = "";
    const schemaPrompt = `${prompt}\nJSON Schema: ${JSON.stringify(schema)}`;
    const reader = this.conversation.sendMessageStreaming(schemaPrompt).getReader();
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      const content = typeof chunk.value.content === "string" ? chunk.value.content : "";
      if (content && firstTokenAt === null) firstTokenAt = performance.now();
      text += content;
      if (content) emit({ type: "token", requestId, text: content });
    }
    const benchmark = await this.conversation.getBenchmarkInfo();
    return {
      text,
      metrics: {
        timeToFirstTokenMs: firstTokenAt === null ? null : firstTokenAt - startedAt,
        totalTimeMs: performance.now() - startedAt,
        outputTokens: benchmark.lastDecodeTokenCount,
        tokensPerSecond: benchmark.lastDecodeTokensPerSecond,
      },
    };
  }

  public cancel(): void {
    this.downloadController?.abort();
    this.conversation?.cancel();
  }

  public async dispose(): Promise<void> {
    this.cancel();
    await this.conversation?.delete();
    await this.engine?.delete();
    this.conversation = undefined;
    this.engine = undefined;
  }
}

class WebLLMRuntimeAdapter implements RuntimeAdapter {
  private engine: import("@mlc-ai/web-llm").MLCEngine | undefined;

  public async load(model: BrowserAIModel, requestId: string): Promise<void> {
    const { CreateMLCEngine } = await import("@mlc-ai/web-llm");
    this.engine = await CreateMLCEngine(model.modelReference, {
      initProgressCallback: (report) => {
        emit({
          type: "progress",
          requestId,
          phase: report.progress < 1 ? "download" : "initialize",
          progress: report.progress,
          message: report.text,
        });
      },
    });
  }

  public async generate(
    prompt: string,
    schema: Record<string, unknown>,
    maxOutputTokens: number,
    requestId: string,
  ): Promise<{ text: string; metrics: GenerationMetrics }> {
    if (!this.engine) throw new Error("model_not_loaded");
    const startedAt = performance.now();
    let firstTokenAt: number | null = null;
    let text = "";
    const stream = await this.engine.chat.completions.create({
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object", schema: JSON.stringify(schema) },
      max_tokens: maxOutputTokens,
      temperature: 0,
      seed: 42,
      stream: true,
      stream_options: { include_usage: true },
    });
    let outputTokens: number | null = null;
    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta.content ?? "";
      if (content && firstTokenAt === null) firstTokenAt = performance.now();
      text += content;
      if (content) emit({ type: "token", requestId, text: content });
      outputTokens = chunk.usage?.completion_tokens ?? outputTokens;
    }
    const totalTimeMs = performance.now() - startedAt;
    return {
      text,
      metrics: {
        timeToFirstTokenMs: firstTokenAt === null ? null : firstTokenAt - startedAt,
        totalTimeMs,
        outputTokens,
        tokensPerSecond: outputTokens === null ? null : outputTokens / (totalTimeMs / 1_000),
      },
    };
  }

  public cancel(): void {
    void this.engine?.interruptGenerate();
  }

  public async dispose(): Promise<void> {
    this.cancel();
    await this.engine?.unload();
    this.engine = undefined;
  }
}

async function handle(command: BrowserAIWorkerCommand): Promise<void> {
  if (command.type === "cancel") {
    if (activeOperation) activeOperation.cancelled = true;
    adapter?.cancel();
    emit({ type: "cancelled", requestId: command.requestId });
    return;
  }
  if (command.type === "dispose") {
    await adapter?.dispose();
    adapter = undefined;
    emit({ type: "disposed", requestId: command.requestId });
    return;
  }
  if (command.type === "clear-cache") {
    await adapter?.dispose();
    adapter = undefined;
    if (command.model.runtime === "webllm") {
      const { deleteModelAllInfoInCache } = await import("@mlc-ai/web-llm");
      await deleteModelAllInfoInCache(command.model.modelReference);
    }
    emit({ type: "cache-cleared", requestId: command.requestId });
    return;
  }
  const operation = { cancelled: false };
  activeOperation = operation;
  if (command.type === "load") {
    await adapter?.dispose();
    adapter = command.model.runtime === "litert-lm" ? new LiteRTRuntimeAdapter() : new WebLLMRuntimeAdapter();
    await adapter.load(command.model, command.requestId);
    if (isCancelled(operation)) {
      await adapter.dispose();
      adapter = undefined;
      throw new DOMException("Cancelled", "AbortError");
    }
    emit({ type: "loaded", requestId: command.requestId });
    return;
  }
  if (!adapter) throw new Error("model_not_loaded");
  const result = await adapter.generate(
    command.prompt,
    command.schema,
    command.maxOutputTokens,
    command.requestId,
  );
  if (isCancelled(operation)) throw new DOMException("Cancelled", "AbortError");
  emit({ type: "completed", requestId: command.requestId, ...result });
}

worker.addEventListener("message", (message: MessageEvent<BrowserAIWorkerCommand>) => {
  void handle(message.data).catch((error: unknown) => {
    if (safeErrorCode(error) === "browser_ai_cancelled") {
      emit({ type: "cancelled", requestId: message.data.requestId });
    } else {
      emit({ type: "error", requestId: message.data.requestId, code: safeErrorCode(error) });
    }
  });
});
