import { useEffect, useState } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, within } from "storybook/test";
import { delay, http, HttpResponse } from "msw";

import { Callout } from "./Callout";
import { Skeleton } from "./Skeleton";

type RequestState =
  | { status: "loading" }
  | { status: "success"; message: string }
  | { status: "error" };

function MockedServiceStatus() {
  const [state, setState] = useState<RequestState>({ status: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    const loadStatus = async () => {
      try {
        const response = await fetch("/api/design-system/status", { signal: controller.signal });
        if (!response.ok) {
          throw new Error("Request failed");
        }
        setState({ status: "success", message: await response.text() });
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setState({ status: "error" });
      }
    };

    void loadStatus();
    return () => {
      controller.abort();
    };
  }, []);

  if (state.status === "loading") {
    return <div className="ds-loading-card"><Skeleton label="Checking local service" /></div>;
  }

  if (state.status === "error") {
    return <Callout title="Service unavailable" tone="error">The mocked local service could not be reached.</Callout>;
  }

  return <Callout title="Service ready" tone="success">{state.message}</Callout>;
}

const meta = {
  title: "Testing/MSW network states",
  component: MockedServiceStatus,
} satisfies Meta<typeof MockedServiceStatus>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Success: Story = {
  parameters: {
    msw: [
      http.get("*/api/design-system/status", async () => {
        await delay(80);
        return HttpResponse.text("The local API contract is available.");
      }),
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByText("The local API contract is available.")).toBeVisible();
  },
};

export const Failure: Story = {
  parameters: {
    msw: [
      http.get("*/api/design-system/status", () => new HttpResponse(null, { status: 503 })),
    ],
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent("Service unavailable");
  },
};
