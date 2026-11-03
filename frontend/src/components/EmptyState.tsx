import type { ReactNode } from 'react';
import { panelVariants } from './ui/panel';
import { cn } from 'cn';

interface EmptyStateProps {
  message: string;
  action?: ReactNode;
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className={cn(panelVariants({ variant: 'dashed' }), 'items-start gap-3 p-6')}>
      <p className="text-muted-foreground">{message}</p>
      {action}
    </div>
  );
}
