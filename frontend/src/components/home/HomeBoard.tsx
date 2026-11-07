import { cn } from 'cn';
import { type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';

import {
  HOME_BOARD,
  HOME_BOARD_ITEM_APPEAR_MS,
  HOME_BOARD_PLAYER_COLORS,
  HOME_BOARD_ITEM_STAGGER_MS,
  type HomeBoardItem,
  type HomeBoardRow,
} from '../../constants/home';
import { ITEM_CHIP_CLASS, TIER_LABEL_CLASS, tierColorStyle } from '../boardStyles';

export function HomeBoard({ className }: { className?: string }) {
  const { t } = useTranslation();
  let appearanceRankAcrossRows: number = 0;

  return (
    <figure className={cn('flex flex-col gap-2', className)}>
      <div aria-hidden="true" className="flex flex-col gap-2">
        {HOME_BOARD.map((row: HomeBoardRow) => (
          <div key={row.tier} className="flex rounded-lg border bg-card shadow-sm">
            <span
              style={tierColorStyle(row.color)}
              className={cn(
                TIER_LABEL_CLASS,
                'rounded-l-lg font-heading text-3xl font-black font-stretch-125%',
              )}
            >
              {row.tier}
            </span>
            <div className="flex flex-wrap items-center gap-2 p-2">
              {row.items.map((item: HomeBoardItem) => {
                const timing: CSSProperties = {
                  animationDelay: `${appearanceRankAcrossRows++ * HOME_BOARD_ITEM_STAGGER_MS}ms`,
                  animationDuration: `${HOME_BOARD_ITEM_APPEAR_MS}ms`,
                };
                return (
                  <span
                    key={item.key}
                    style={timing}
                    className={cn(ITEM_CHIP_CLASS, 'relative px-2 motion-safe:animate-reveal')}
                  >
                    <span className="text-sm font-medium">{t(`home.board.items.${item.key}`)}</span>
                    {item.voterInitials.length > 0 && <Voters voterInitials={item.voterInitials} />}
                  </span>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <figcaption className="sr-only">{t('home.board.description')}</figcaption>
    </figure>
  );
}

function Voters({ voterInitials }: { voterInitials: readonly string[] }) {
  return (
    <span className="absolute -top-2.5 -right-2 flex gap-0.5">
      {voterInitials.map((initial: string) => (
        <span
          key={initial}
          style={tierColorStyle(HOME_BOARD_PLAYER_COLORS[initial] ?? '')}
          className="flex size-5 items-center justify-center rounded-full text-[10px] font-bold ring-2 ring-card"
        >
          {initial}
        </span>
      ))}
    </span>
  );
}
