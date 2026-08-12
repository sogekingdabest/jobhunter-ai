import type { ReactNode } from "react";

import { Icon } from "./Icon";

export type CalloutTone = "info" | "success" | "warning" | "error";

export interface CalloutProps {
  action?: ReactNode;
  children: ReactNode;
  title: string;
  tone?: CalloutTone;
}

export function Callout({ action, children, title, tone = "info" }: CalloutProps) {
  return (
    <section
      className={`ds-callout ds-callout--${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <span className="ds-callout__icon"><Icon className="size-5" name={tone === "success" ? "check" : "shield"} /></span>
      <div className="ds-callout__content">
        <h3>{title}</h3>
        <div>{children}</div>
      </div>
      {action ? <div className="ds-callout__action">{action}</div> : null}
    </section>
  );
}
