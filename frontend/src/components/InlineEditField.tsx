import { useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';

import { cn } from '@/lib/utils';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface InlineEditFieldProps {
  label: string;
  // Libellé lu par les lecteurs d'écran seulement (ex. un champ par ligne d'une liste)
  hideLabel?: boolean;
  value: string;
  maxLength: number;
  error?: string;
  onSave: (value: string) => void;
  className?: string;
}

// Champ enregistré dès qu'on le valide (Entrée) ou qu'on le quitte, s'il a changé ; Échap
// rétablit la valeur enregistrée. Le parent lui donne key={value} : une nouvelle valeur
// enregistrée remplace le brouillon.
export function InlineEditField({
  label,
  hideLabel = false,
  value,
  maxLength,
  error,
  onSave,
  className,
}: InlineEditFieldProps) {
  const [draft, setDraft] = useState(value);
  // Valeur déjà envoyée : Entrée puis la perte du focus ne l'envoient pas deux fois
  const lastSentValue = useRef(value);
  const id = useId();
  const errorId = `${id}-error`;

  function save() {
    const trimmedDraft = draft.trim();
    if (trimmedDraft === value || trimmedDraft === lastSentValue.current) return;
    lastSentValue.current = trimmedDraft;
    onSave(draft);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    save();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setDraft(value);
    }
  }

  return (
    <form onSubmit={handleSubmit} className={cn('flex min-w-0 flex-col gap-1', className)}>
      <Label htmlFor={id} className={cn(hideLabel && 'sr-only')}>
        {label}
      </Label>
      <Input
        id={id}
        value={draft}
        maxLength={maxLength}
        required
        aria-invalid={error !== undefined}
        aria-describedby={error === undefined ? undefined : errorId}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={save}
        onKeyDown={handleKeyDown}
      />
      {error !== undefined && (
        <span id={errorId} className="text-sm text-destructive">
          {error}
        </span>
      )}
    </form>
  );
}
