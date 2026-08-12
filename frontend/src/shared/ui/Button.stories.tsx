import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { Button } from "./Button";
import { Icon } from "./Icon";

const meta = {
  title: "Foundations/Button",
  component: Button,
  args: {
    children: "Create profile",
    onClick: fn(),
  },
  parameters: { layout: "centered" },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: {
    endIcon: <span aria-hidden="true">→</span>,
  },
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Create profile" }));
    await expect(args.onClick).toHaveBeenCalledOnce();
  },
};

export const Variants: Story = {
  render: () => (
    <div className="ds-story-row">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="danger">Delete</Button>
    </div>
  ),
};

export const SizesAndIcons: Story = {
  render: () => (
    <div className="ds-story-row">
      <Button size="small" startIcon={<Icon className="size-4" name="sparkles" />}>Small</Button>
      <Button size="medium" startIcon={<Icon className="size-4" name="profile" />}>Medium</Button>
      <Button size="large" startIcon={<Icon className="size-5" name="resume" />}>Large</Button>
    </div>
  ),
};

export const Loading: Story = {
  args: {
    children: "Analyze offer",
    isLoading: true,
    loadingText: "Analyzing",
  },
};
