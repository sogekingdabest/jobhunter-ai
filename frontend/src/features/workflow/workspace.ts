import type { WorkspaceSnapshot } from "./types";

const STORAGE_KEY = "jobhunter-workspace-v1";

export function emptyWorkspace(): WorkspaceSnapshot {
  return {
    exported_at: new Date(0).toISOString(),
    schema_version: "1.0",
    candidate: null,
    job_offer: null,
    assessment: null,
    tailored_resume: null,
  };
}

export function loadWorkspace(): WorkspaceSnapshot {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) return emptyWorkspace();
  try {
    const parsed = JSON.parse(stored) as unknown;
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("schema_version" in parsed) ||
      parsed.schema_version !== "1.0"
    ) {
      return emptyWorkspace();
    }
    return parsed as WorkspaceSnapshot;
  } catch {
    return emptyWorkspace();
  }
}

export function saveWorkspace(snapshot: WorkspaceSnapshot): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

export function clearWorkspace(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function exportWorkspace(snapshot: WorkspaceSnapshot): void {
  const payload = { ...snapshot, exported_at: new Date().toISOString() };
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `jobhunter-export-${payload.exported_at.slice(0, 10)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}
