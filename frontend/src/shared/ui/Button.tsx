import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "small" | "medium" | "large";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  endIcon?: ReactNode;
  isLoading?: boolean;
  loadingText?: string;
  size?: ButtonSize;
  startIcon?: ReactNode;
  variant?: ButtonVariant;
}

export function Button({
  children,
  className = "",
  disabled,
  endIcon,
  isLoading = false,
  loadingText = "Working",
  size = "medium",
  startIcon,
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  const classes = ["ds-button", `ds-button--${variant}`, `ds-button--${size}`, className]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      aria-busy={isLoading || undefined}
      className={classes}
      disabled={disabled || isLoading}
      type={type}
      {...props}
    >
      {isLoading ? <span aria-hidden="true" className="ds-spinner" /> : startIcon}
      <span>{isLoading ? loadingText : children}</span>
      {!isLoading && endIcon}
    </button>
  );
}
