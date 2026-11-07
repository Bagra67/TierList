import { ImageOff } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from 'cn';

interface RemovedImageProps {
  className: string;
  showLabel: boolean;
}

export function RemovedImage({ className, showLabel }: RemovedImageProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <span
      role="img"
      aria-label={t('common.imageRemoved')}
      className={cn(
        'flex shrink-0 flex-col items-center justify-center gap-1 bg-muted p-1 text-center text-muted-foreground',
        className,
      )}
    >
      <ImageOff className={showLabel ? 'size-8' : 'size-5'} aria-hidden="true" />
      {showLabel && <span className="text-xs leading-tight">{t('common.imageRemoved')}</span>}
    </span>
  );
}
