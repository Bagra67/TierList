import { cn } from 'cn';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import type { GameItem } from '../api/rooms';
import { CURRENT_CARD_CLASS } from './boardStyles';
import { GameItemView } from './GameItemView';

interface CurrentItemCardProps {
  item: GameItem;
  // Largeur selon l'endroit (colonne du plateau)
  className?: string;
}

// L'élément en cours, pour qui ne le place pas (l'hôte qui ne joue pas) ou l'a déjà placé
export function CurrentItemCard({ item, className }: CurrentItemCardProps) {
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  return (
    <div className={cn(CURRENT_CARD_CLASS, 'border', className)}>
      <GameItemView item={item} imageLabel={t('rooms.game.currentItemImage')} size="large" />
    </div>
  );
}
