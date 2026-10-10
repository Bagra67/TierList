import { useId, useRef, useState, type FormEvent, type KeyboardEvent, type RefObject } from 'react';

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
// enregistrée remplace le brouillon. Après un échec, valider à nouveau renvoie la valeur.
export function InlineEditField({
  label,
  hideLabel = false,
  value,
  maxLength,
  error,
  onSave,
  className,
}: InlineEditFieldProps) {
  const [draft, setDraft] = useState<string>(value);
  // Brouillon envoyé avec Entrée : quitter ensuite le champ sans rien changer ne le renvoie pas
  const draftSentWithEnter: RefObject<string | null> = useRef<string | null>(null);
  const id: string = useId();
  const errorId: string = `${id}-error`;

  function save() {
    const trimmedDraft: string = draft.trim();
    if (trimmedDraft === value) return;
    onSave(draft);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    draftSentWithEnter.current = draft;
    save();
  }

  function handleBlur() {
    if (draft === draftSentWithEnter.current) return;
    save();
  }

  function handleChange(newDraft: string) {
    draftSentWithEnter.current = null;
    setDraft(newDraft);
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
        onChange={(event) => handleChange(event.target.value)}
        onBlur={handleBlur}
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
