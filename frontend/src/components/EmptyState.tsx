import type { ReactNode } from 'react';

interface EmptyStateProps {
  // Ce qui manque, et comment le remplir
  message: string;
  // Le bouton ou le lien qui permet d'agir, s'il n'est pas déjà à côté du titre de la page
  action?: ReactNode;
}

// Liste vide : un encadré qui dit quoi faire, plutôt qu'une ligne grise
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex w-full flex-col items-start gap-3 rounded-xl border border-dashed p-6">
      <p className="text-muted-foreground">{message}</p>
      {action}
    </div>
  );
}
