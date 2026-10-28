import type { GameItem } from '../api/rooms';
import { cn } from 'cn';

interface GameItemViewProps {
  item: GameItem;
  // Nom de l'image quand l'item n'a pas de texte (avec un texte, l'image est illustrative)
  imageLabel: string;
  size: 'large' | 'small';
}

// Un item de la partie : son image et/ou son texte, en grand (item en cours) ou en petit (plateau)
export function GameItemView({ item, imageLabel, size }: GameItemViewProps) {
  return (
    <span className={cn('flex items-center gap-2', size === 'large' && 'flex-col items-start')}>
      {item.image_url !== null && (
        // Avec un texte, il est affiché à côté : l'image est illustrative (alt vide), sinon le
        // lecteur d'écran le lirait deux fois
        <img
          src={item.image_url}
          alt={item.text === null ? imageLabel : ''}
          className={cn(
            'rounded-sm object-cover',
            size === 'large' ? 'size-32' : 'size-12 sm:size-14',
          )}
        />
      )}
      {item.text !== null && (
        <span className={size === 'large' ? 'text-lg font-semibold' : 'px-1 text-sm font-medium'}>
          {item.text}
        </span>
      )}
    </span>
  );
}
