import { beforeEach, describe, expect, it } from "vitest";

import { clearWorkspace, emptyWorkspace, loadWorkspace, saveWorkspace } from "./workspace";

describe("workspace persistence", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("round-trips the versioned local workspace", () => {
    const workspace = emptyWorkspace();
    saveWorkspace(workspace);
    expect(loadWorkspace()).toEqual(workspace);
  });

  it("falls back safely for invalid or unsupported local data", () => {
    window.localStorage.setItem("jobhunter-workspace-v1", "not json");
    expect(loadWorkspace()).toEqual(emptyWorkspace());
    window.localStorage.setItem("jobhunter-workspace-v1", JSON.stringify({ schema_version: "2.0" }));
    expect(loadWorkspace()).toEqual(emptyWorkspace());
  });

  it("clears the persisted workspace", () => {
    saveWorkspace(emptyWorkspace());
    clearWorkspace();
    expect(window.localStorage.getItem("jobhunter-workspace-v1")).toBeNull();
  });
});
