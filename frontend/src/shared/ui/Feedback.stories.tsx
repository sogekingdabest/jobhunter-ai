import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "./Button";
import { Callout } from "./Callout";
import { EmptyState } from "./EmptyState";
import { Skeleton } from "./Skeleton";

const meta = {
  title: "Foundations/Feedback states",
  parameters: { layout: "padded" },
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const CalloutTones: Story = {
  render: () => (
    <div className="ds-story-stack">
      <Callout title="Evidence connected" tone="success">All generated claims link to verified profile facts.</Callout>
      <Callout title="Review suggested" tone="warning">The offer asks for a skill that only partially matches your projects.</Callout>
      <Callout title="Untrusted instruction ignored" tone="error">Instructions embedded in the job description were not executed.</Callout>
      <Callout title="Local processing" tone="info" action={<Button size="small" variant="secondary">Details</Button>}>
        This document can be processed without sending it to a cloud provider.
      </Callout>
    </div>
  ),
};

export const NoOpportunities: Story = {
  render: () => (
    <EmptyState
      action={<Button endIcon={<span aria-hidden="true">→</span>}>Import an offer</Button>}
      description="Paste a job description or import one by URL when you are ready to compare it with your profile."
      icon="briefcase"
      title="No opportunities yet"
    />
  ),
};

export const LoadingProfile: Story = {
  render: () => (
    <div className="ds-loading-card">
      <Skeleton height="1.4rem" label="Loading profile title" width="48%" />
      <Skeleton label="Loading profile summary" />
      <Skeleton label="Loading profile summary" width="82%" />
      <Skeleton height="2.6rem" label="Loading profile action" width="34%" />
    </div>
  ),
};
