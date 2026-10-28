import * as React from 'react';
import { cn } from 'cn';

// Liste déroulante native (<select>) à l'apparence des champs : bordure, focus, mode sombre.
// Native plutôt que Radix : le clavier, le mobile et les lecteurs d'écran sont gérés par le navigateur
function NativeSelect({ className, ...props }: React.ComponentProps<'select'>) {
  return (
    <select
      data-slot="native-select"
      className={cn(
        'h-8 rounded-lg border border-input bg-transparent px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 dark:bg-input/30',
        className,
      )}
      {...props}
    />
  );
}

export { NativeSelect };
