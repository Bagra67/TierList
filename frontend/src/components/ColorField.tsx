import { useEffect, useRef, useState } from 'react';

interface ColorFieldProps {
  label: string;
  value: string;
  onSave: (color: string) => void;
}

// Sélecteur de couleur natif. L'événement input (onChange de React) suit chaque mouvement
// dans le sélecteur : il ne sert qu'à l'aperçu. La couleur n'est enregistrée qu'à l'événement
// change natif, émis quand l'utilisateur valide son choix. Le parent lui donne key={value}.
export function ColorField({ label, value, onSave }: ColorFieldProps) {
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const input = inputRef.current;
    if (input === null) return;
    function handleCommit() {
      if (input !== null && input.value.toUpperCase() !== value) {
        onSave(input.value);
      }
    }
    input.addEventListener('change', handleCommit);
    return () => input.removeEventListener('change', handleCommit);
  }, [value, onSave]);

  return (
    <input
      ref={inputRef}
      type="color"
      aria-label={label}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      className="size-8 shrink-0 cursor-pointer rounded-md border bg-transparent p-0.5"
    />
  );
}
