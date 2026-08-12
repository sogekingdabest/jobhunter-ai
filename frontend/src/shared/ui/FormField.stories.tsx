import type { SyntheticEvent } from "react";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { Button } from "./Button";
import { TextareaField, TextField } from "./FormField";

interface FormStoryArgs {
  onSubmit: () => void;
}

const meta = {
  title: "Foundations/Form fields",
  args: { onSubmit: fn() },
  render: ({ onSubmit }) => {
    const handleSubmit = (event: SyntheticEvent<HTMLFormElement, SubmitEvent>) => {
      event.preventDefault();
      onSubmit();
    };

    return (
      <form className="ds-form-preview" onSubmit={handleSubmit}>
        <TextField
          autoComplete="organization-title"
          hint="Use the title from your current or most recent role."
          label="Professional headline"
          name="headline"
          placeholder="Backend engineer"
          required
        />
        <TextareaField
          hint="Only include experience already present in your master profile."
          label="Professional summary"
          name="summary"
          placeholder="Describe your focus and strengths"
          required
        />
        <div className="ds-form-preview__actions">
          <Button variant="ghost">Cancel</Button>
          <Button type="submit">Save profile</Button>
        </div>
      </form>
    );
  },
} satisfies Meta<FormStoryArgs>;

export default meta;
type Story = StoryObj<typeof meta>;

export const CompleteForm: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText(/professional headline/i), "Backend engineer");
    await userEvent.type(
      canvas.getByLabelText(/professional summary/i),
      "I build reliable APIs with Python.",
    );
    await userEvent.click(canvas.getByRole("button", { name: "Save profile" }));

    await expect(args.onSubmit).toHaveBeenCalledOnce();
  },
};

export const ValidationError: Story = {
  render: () => (
    <div className="ds-form-preview">
      <TextField
        defaultValue="Senior astronaut"
        error="This headline is not supported by your verified experience."
        label="Professional headline"
      />
      <TextareaField disabled label="Generated summary" value="Waiting for verified profile facts." readOnly />
    </div>
  ),
};
