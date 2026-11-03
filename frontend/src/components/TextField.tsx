import { useId, type InputHTMLAttributes } from 'react';

import { Input } from './ui/input';
import { Label } from './ui/label';

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  name: string;
  error?: string;
}

export function TextField({ label, error, ...inputProps }: TextFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={error !== undefined}
        aria-describedby={error === undefined ? undefined : errorId}
        {...inputProps}
      />
      {error !== undefined && (
        <span id={errorId} className="text-sm text-destructive">
          {error}
        </span>
      )}
    </div>
  );
}
