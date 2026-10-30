import { cn } from 'cn';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { useHistory } from '../../api/history';
import type { PastGame } from '../../api/rooms';
import { HOME_RECENT_COUNT } from '../../constants/home';
import { ROUTES, resultsPath } from '../../constants/routes';
import { translateError } from '../../errors/apiError';
import { EmptyState } from '../EmptyState';
import { ErrorMessage } from '../ErrorMessage';
import { LoadingSkeleton } from '../LoadingSkeleton';
import { panelVariants } from '../ui/panel';
import { textLinkClassName } from '../ui/text-link';

// Accueil connecté : les dernières parties closes (l'historique est trié de la plus récente à la
// plus ancienne), avec le lien de leurs résultats
export function RecentGames() {
  const { data, isPending, isError, error } = useHistory();
  const { t } = useTranslation();
  const headingId: string = useId();
  const games: PastGame[] = data?.pages[0]?.games.slice(0, HOME_RECENT_COUNT) ?? [];

  return (
    <section aria-labelledby={headingId} className="flex min-w-0 flex-col items-start gap-3">
      <div className="flex w-full flex-wrap items-baseline justify-between gap-2">
        <h2 id={headingId} className="text-lg font-semibold">
          {t('home.recentGames.title')}
        </h2>
        {games.length > 0 && (
          <Link to={ROUTES.HISTORY} className={textLinkClassName}>
            {t('home.recentGames.all')}
          </Link>
        )}
      </div>
      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {data !== undefined && games.length === 0 && (
        <EmptyState message={t('home.recentGames.empty')} />
      )}
      {games.length > 0 && (
        <ul className={panelVariants({ variant: 'list' })}>
          {games.map((game: PastGame) => (
            <li
              key={game.public_token}
              className="flex items-center justify-between gap-4 px-4 py-3"
            >
              <div className="flex min-w-0 flex-col gap-1">
                <span className="truncate font-medium">{game.template_name}</span>
                <span className="text-sm text-muted-foreground">
                  {t('history.closedAt', { date: new Date(game.closed_at) })}
                </span>
              </div>
              <Link
                to={resultsPath(game.public_token)}
                aria-label={t('history.openLabel', { name: game.template_name })}
                className={cn(textLinkClassName, 'shrink-0 text-sm')}
              >
                {t('history.open')}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
