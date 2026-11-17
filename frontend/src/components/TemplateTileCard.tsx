import type { ReactNode } from 'react';

import { RemovedImage } from './RemovedImage';
import { panelVariants } from './ui/panel';

interface TemplateTileCardProps {
  imageUrl: string | null;
  imageRemoved: boolean;
  imageAlt: string;
  text: string | null;
  children?: ReactNode;
}

export function TemplateTileCard({
  imageUrl,
  imageRemoved,
  imageAlt,
  text,
  children,
}: TemplateTileCardProps) {
  return (
    <li className={panelVariants({ className: 'gap-2 p-3' })}>
      {imageRemoved && (
        <RemovedImage className="aspect-square w-full rounded-sm" showLabel={true} />
      )}
      {imageUrl !== null && (
        <img
          src={imageUrl}
          alt={imageAlt}
          className="aspect-square w-full rounded-sm object-cover"
        />
      )}
      {children}
      {text !== null && <p className="text-sm font-medium break-words">{text}</p>}
    </li>
  );
}
