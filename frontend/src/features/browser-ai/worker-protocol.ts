import type { BrowserAIModel, GenerationMetrics } from "./types";

export type BrowserAIWorkerCommand =
  | Readonly<{ type: "load"; requestId: string; model: BrowserAIModel }>
  | Readonly<{
      type: "generate";
      requestId: string;
      prompt: string;
      schema: Record<string, unknown>;
      maxOutputTokens: number;
    }>
  | Readonly<{ type: "cancel"; requestId: string }>
  | Readonly<{ type: "clear-cache"; requestId: string; model: BrowserAIModel }>
  | Readonly<{ type: "dispose"; requestId: string }>;

export type BrowserAIWorkerEvent =
  | Readonly<{
      type: "progress";
      requestId: string;
      phase: "download" | "initialize";
      progress: number;
      loadedBytes?: number;
      totalBytes?: number;
      message: string;
    }>
  | Readonly<{ type: "loaded"; requestId: string }>
  | Readonly<{ type: "token"; requestId: string; text: string }>
  | Readonly<{
      type: "completed";
      requestId: string;
      text: string;
      metrics: GenerationMetrics;
    }>
  | Readonly<{ type: "cancelled"; requestId: string }>
  | Readonly<{ type: "disposed"; requestId: string }>
  | Readonly<{ type: "cache-cleared"; requestId: string }>
  | Readonly<{ type: "error"; requestId: string; code: string }>;

export function isBrowserAIWorkerEvent(value: unknown): value is BrowserAIWorkerEvent {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as { type?: unknown; requestId?: unknown };
  const eventTypes = new Set([
    "progress",
    "loaded",
    "token",
    "completed",
    "cancelled",
    "disposed",
    "cache-cleared",
    "error",
  ]);
  return (
    typeof candidate.type === "string" &&
    eventTypes.has(candidate.type) &&
    typeof candidate.requestId === "string"
  );
}
