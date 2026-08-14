import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { App } from "./App";
import { ThemeProvider } from "./providers/ThemeProvider";

function renderApp() {
  return render(
    <ThemeProvider>
      <App />
    </ThemeProvider>,
  );
}

describe("App", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("presents the complete evidence-first MVP workflow", () => {
    renderApp();

    expect(screen.getByRole("heading", { name: /from master profile/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Master profile" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Opportunity" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Explainable match" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Resume studio" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Optional in-browser AI" })).toBeInTheDocument();
  });

  it("marks overview as the current primary destination", () => {
    renderApp();
    const desktopNavigation = screen.getAllByRole("navigation", { name: "Primary navigation" })[0];
    if (!desktopNavigation) throw new Error("Desktop navigation not found");
    expect(within(desktopNavigation).getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps downstream steps disabled until their dependencies exist", () => {
    renderApp();
    expect(screen.getByRole("button", { name: "Import grounded offer" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Calculate match" })).toBeDisabled();
    expect(screen.getByText("Save the master profile first.")).toBeInTheDocument();
  });

  it("cycles through explicit and system theme preferences", async () => {
    const user = userEvent.setup();
    renderApp();
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    await user.click(screen.getByRole("button", { name: /use light theme/i }));
    expect(window.localStorage.getItem("jobhunter-theme")).toBe("light");
    await user.click(screen.getByRole("button", { name: /use dark theme/i }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    await user.click(screen.getByRole("button", { name: /use system theme/i }));
    expect(window.localStorage.getItem("jobhunter-theme")).toBe("system");
  });
});
