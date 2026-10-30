import * as React from 'react';
import { cn } from 'cn';

// Forme grise qui pulse à la place d'un contenu en cours de chargement (décorative)
function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="skeleton"
      aria-hidden="true"
      className={cn('animate-pulse rounded-md bg-muted', className)}
      {...props}
    />
  );
}

export { Skeleton };
