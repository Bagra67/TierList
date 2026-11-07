import type { GameItem } from '../api/rooms';
import { cn } from 'cn';
import { ITEM_CHIP_IMAGE_SIZE_CLASS } from './boardStyles';
import { RemovedImage } from './RemovedImage';

interface GameItemViewProps {
  item: GameItem;
  imageLabel: string;
  size: 'large' | 'small';
}

export function GameItemView({ item, imageLabel, size }: GameItemViewProps) {
  const imageSizeClass: string = size === 'large' ? 'size-32' : ITEM_CHIP_IMAGE_SIZE_CLASS;
  const altAvoidingDoubleReading: string = item.text === null ? imageLabel : '';
  return (
    <span className={cn('flex items-center gap-2', size === 'large' && 'flex-col items-start')}>
      {item.image_removed && (
        <RemovedImage className={cn('rounded-sm', imageSizeClass)} showLabel={size === 'large'} />
      )}
      {item.image_url !== null && (
        <img
          src={item.image_url}
          alt={altAvoidingDoubleReading}
          className={cn('rounded-sm object-cover', imageSizeClass)}
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
