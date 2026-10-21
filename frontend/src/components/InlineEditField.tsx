import {
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
} from 'react';

import { cn } from 'cn';
import { Input, inputClassName } from './ui/input';
import { Label } from './ui/label';

interface InlineEditFieldProps {
  label: string;
  // Libellé lu par les lecteurs d'écran seulement (ex. un champ par ligne d'une liste)
  hideLabel?: boolean;
  value: string;
  maxLength: number;
  // false : le champ peut être vidé (ex. le texte d'une tuile qui a une image)
  required?: boolean;
  // true : le texte passe à la ligne et le champ grandit, pour qu'un long nom se lise en entier
  // dans une colonne étroite. La valeur reste sur une seule ligne (Entrée enregistre).
  multiline?: boolean;
  error?: string;
  onSave: (value: string) => void;
  className?: string;
}

// Attributs communs au champ d'une ligne (<input>) et à la zone de texte (<textarea>)
interface SharedFieldProps {
  id: string;
  value: string;
  maxLength: number;
  required: boolean;
  'aria-invalid': boolean;
  'aria-describedby': string | undefined;
  onBlur: () => void;
}

// Champ enregistré dès qu'on le valide (Entrée) ou qu'on le quitte, s'il a changé ; Échap
// rétablit la valeur enregistrée. Le parent lui donne key={value} : une nouvelle valeur
// enregistrée remplace le brouillon. Après un échec, valider à nouveau renvoie la valeur.
export function InlineEditField({
  label,
  hideLabel = false,
  value,
  maxLength,
  required = true,
  multiline = false,
  error,
  onSave,
  className,
}: InlineEditFieldProps) {
  const [draft, setDraft] = useState<string>(value);
  // Brouillon envoyé avec Entrée : quitter ensuite le champ sans rien changer ne le renvoie pas
  const draftSentWithEnter: RefObject<string | null> = useRef<string | null>(null);
  const textAreaRef: RefObject<HTMLTextAreaElement | null> = useRef<HTMLTextAreaElement>(null);
  const id: string = useId();
  const errorId: string = `${id}-error`;

  // La zone de texte prend la hauteur de son contenu (en JS : la propriété CSS field-sizing
  // n'est pas encore gérée par tous les navigateurs)
  useLayoutEffect(() => {
    const textArea: HTMLTextAreaElement | null = textAreaRef.current;
    if (textArea === null) return;
    textArea.style.height = 'auto';
    textArea.style.height = `${textArea.scrollHeight}px`;
  }, [draft]);

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
    // Un retour à la ligne collé devient une espace : le passage à la ligne n'est qu'un affichage
    setDraft(newDraft.replace(/\r?\n/g, ' '));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) {
    if (event.key === 'Escape') {
      setDraft(value);
      return;
    }
    // Dans une zone de texte, Entrée ajouterait un retour à la ligne : elle enregistre, comme
    // dans un champ d'une ligne (sauf pendant une saisie IME, où elle valide un caractère)
    if (multiline && event.key === 'Enter' && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  const fieldProps: SharedFieldProps = {
    id,
    value: draft,
    maxLength,
    required,
    'aria-invalid': error !== undefined,
    'aria-describedby': error === undefined ? undefined : errorId,
    onBlur: handleBlur,
  };

  return (
    <form onSubmit={handleSubmit} className={cn('flex min-w-0 flex-col gap-1', className)}>
      <Label htmlFor={id} className={cn(hideLabel && 'sr-only')}>
        {label}
      </Label>
      {multiline ? (
        <textarea
          ref={textAreaRef}
          rows={1}
          {...fieldProps}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
          className={cn(inputClassName, 'min-h-8 resize-none overflow-hidden break-words')}
        />
      ) : (
        <Input
          {...fieldProps}
          onChange={(event) => handleChange(event.target.value)}
          onKeyDown={handleKeyDown}
        />
      )}
      {error !== undefined && (
        <span id={errorId} className="text-sm text-destructive">
          {error}
        </span>
      )}
    </form>
  );
}
