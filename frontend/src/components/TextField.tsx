import { useId, type InputHTMLAttributes } from 'react';

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  name: string;
  error?: string;
}

// Champ de formulaire étiqueté ; l'erreur éventuelle est reliée au champ pour les lecteurs d'écran
export function TextField({ label, error, ...inputProps }: TextFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <p>
      <label htmlFor={id}>{label}</label>
      <br />
      <input
        id={id}
        aria-invalid={error !== undefined}
        aria-describedby={error === undefined ? undefined : errorId}
        {...inputProps}
      />
      {error !== undefined && (
        <>
          <br />
          <span id={errorId}>{error}</span>
        </>
      )}
    </p>
  );
}
