import type { ReactNode } from 'react';
import { panelVariants } from './ui/panel';
import { cn } from 'cn';

interface EmptyStateProps {
  // Ce qui manque, et comment le remplir
  message: string;
  // Le bouton ou le lien qui permet d'agir, s'il n'est pas déjà à côté du titre de la page
  action?: ReactNode;
}

// Liste vide : un encadré qui dit quoi faire, plutôt qu'une ligne grise
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className={cn(panelVariants({ variant: 'dashed' }), 'items-start gap-3 p-6')}>
      <p className="text-muted-foreground">{message}</p>
      {action}
    </div>
  );
}
