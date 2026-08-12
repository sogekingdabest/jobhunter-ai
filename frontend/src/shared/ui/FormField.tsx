import {
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from "react";

interface FieldFrameProps {
  children: ReactNode;
  error?: string;
  hint?: string;
  id: string;
  label: string;
  required?: boolean;
}

function FieldFrame({ children, error, hint, id, label, required }: FieldFrameProps) {
  return (
    <div className="ds-field">
      <label className="ds-field__label" htmlFor={id}>
        {label}
        {required ? <span aria-hidden="true" className="ds-field__required">*</span> : null}
      </label>
      {children}
      {error ? <p className="ds-field__error" id={`${id}-error`}>{error}</p> : null}
      {!error && hint ? <p className="ds-field__hint" id={`${id}-hint`}>{hint}</p> : null}
    </div>
  );
}

export interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  error?: string;
  hint?: string;
  label: string;
}

export function TextField({ error, hint, id: providedId, label, required, ...props }: TextFieldProps) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <FieldFrame error={error} hint={hint} id={id} label={label} required={required}>
      <input
        aria-describedby={describedBy}
        aria-invalid={Boolean(error)}
        className="ds-input"
        id={id}
        required={required}
        {...props}
      />
    </FieldFrame>
  );
}

export interface TextareaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string;
  hint?: string;
  label: string;
}

export function TextareaField({ error, hint, id: providedId, label, required, ...props }: TextareaFieldProps) {
  const generatedId = useId();
  const id = providedId ?? generatedId;
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <FieldFrame error={error} hint={hint} id={id} label={label} required={required}>
      <textarea
        aria-describedby={describedBy}
        aria-invalid={Boolean(error)}
        className="ds-input ds-textarea"
        id={id}
        required={required}
        {...props}
      />
    </FieldFrame>
  );
}
