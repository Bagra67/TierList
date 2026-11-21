import { cn } from 'cn';
import type { LucideIcon } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { translateError } from '../errors/apiError';
import { ErrorMessage } from './ErrorMessage';
import { Button } from './ui/button';

interface ToggleActionButtonProps {
  pressed: boolean;
  onToggle: () => void;
  pending: boolean;
  error: Error | null;
  icon: LucideIcon;
  pressedIconClassName: string;
  label?: string;
  ariaLabel?: string;
  compact?: boolean;
  className?: string;
}

export function ToggleActionButton({
  pressed,
  onToggle,
  pending,
  error,
  icon: Icon,
  pressedIconClassName,
  label,
  ariaLabel,
  compact = false,
  className,
}: ToggleActionButtonProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <div className={cn('flex flex-col items-end gap-1', compact && 'relative z-10')}>
      <Button
        type="button"
        variant={compact ? 'ghost' : 'outline'}
        size={compact ? 'sm' : 'default'}
        aria-pressed={pressed}
        aria-label={ariaLabel}
        disabled={pending}
        onClick={onToggle}
        className={className}
      >
        <Icon aria-hidden="true" className={pressed ? pressedIconClassName : undefined} />
        {label}
      </Button>
      {error !== null && (
        <ErrorMessage className={compact ? 'text-right text-xs' : 'text-sm'}>
          {translateError(t, error)}
        </ErrorMessage>
      )}
    </div>
  );
}
