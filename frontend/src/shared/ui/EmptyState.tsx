import type { ReactNode } from "react";

import { Icon, type IconName } from "./Icon";

export interface EmptyStateProps {
  action?: ReactNode;
  description: string;
  icon?: IconName;
  title: string;
}

export function EmptyState({ action, description, icon = "compass", title }: EmptyStateProps) {
  return (
    <section className="ds-empty-state">
      <span className="ds-empty-state__icon"><Icon className="size-7" name={icon} /></span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action ? <div className="ds-empty-state__action">{action}</div> : null}
    </section>
  );
}
