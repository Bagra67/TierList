import { ImageOff } from 'lucide-react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import { cn } from 'cn';

interface RemovedImageProps {
  // Taille et coins, ceux de l'image qu'il remplace
  className: string;
  // Le texte « Image retirée » sous l'icône, quand il y a la place
  showLabel: boolean;
}

// Visuel d'une image masquée ou supprimée par la modération (US-1.4) : il prend sa place, partout
// où elle était affichée. Une icône et un nom accessible, pas seulement une couleur.
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
