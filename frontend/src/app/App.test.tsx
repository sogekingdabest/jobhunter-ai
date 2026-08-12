import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

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
  it("introduces the product without claiming unfinished features are available", () => {
    renderApp();

    expect(
      screen.getByRole("heading", { name: /find the right role/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Foundation preview")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Explainable matching" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Truthful by design" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Private when you want" }),
    ).toBeInTheDocument();
  });

  it("marks overview as the current primary destination", () => {
    renderApp();

    const desktopNavigation = screen.getAllByRole("navigation", {
      name: "Primary navigation",
    })[0];

    if (!desktopNavigation) {
      throw new Error("Desktop navigation not found");
    }

    expect(within(desktopNavigation).getByRole("link", { name: "Overview" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("cycles through explicit and system theme preferences", async () => {
    const user = userEvent.setup();
    renderApp();

    expect(document.documentElement).toHaveAttribute("data-theme", "light");

    await user.click(screen.getByRole("button", { name: /use light theme/i }));
    expect(window.localStorage.getItem("jobhunter-theme")).toBe("light");

    await user.click(screen.getByRole("button", { name: /use dark theme/i }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem("jobhunter-theme")).toBe("dark");

    await user.click(screen.getByRole("button", { name: /use system theme/i }));
    expect(window.localStorage.getItem("jobhunter-theme")).toBe("system");
  });
});
