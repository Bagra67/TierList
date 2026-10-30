import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { cn } from 'cn';

import { useHistory } from '../api/history';
import type { PastGame } from '../api/rooms';
import { ErrorMessage } from '../components/ErrorMessage';
import { EmptyState } from '../components/EmptyState';
import { Button } from '../components/ui/button';
import { textLinkClassName } from '../components/ui/text-link';
import { ROUTES, resultsPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { panelVariants } from '../components/ui/panel';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { PageContainer } from '../components/PageContainer';
import { CONTENT_COLUMN_CLASS } from '../constants/layout';

// Historique du compte (US-5.5) : ses parties closes, jouées ou animées comme room admin, de la
// plus récente à la plus ancienne, chacune avec le lien de ses résultats
export function HistoryPage() {
  const { data, isPending, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useHistory();
  const { t } = useTranslation();
  const games: PastGame[] = data?.pages.flatMap((page) => page.games) ?? [];

  return (
    <PageContainer width="app">
      <div className={cn(CONTENT_COLUMN_CLASS, 'flex flex-col items-start gap-6')}>
        <h1 className="text-2xl font-semibold">{t('history.title')}</h1>
        {isPending && <LoadingSkeleton shape="list" />}
        {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
        {data !== undefined && games.length === 0 && (
          <EmptyState
            message={t('history.empty')}
            action={
              <Button asChild variant="outline">
                <Link to={ROUTES.HOME}>{t('history.emptyAction')}</Link>
              </Button>
            }
          />
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
                  <p className="flex flex-wrap gap-x-3 text-sm text-muted-foreground">
                    <span>{t('history.closedAt', { date: new Date(game.closed_at) })}</span>
                    <span>{t('history.players', { count: game.player_count })}</span>
                  </p>
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
        {hasNextPage && (
          <Button
            type="button"
            variant="outline"
            disabled={isFetchingNextPage}
            onClick={() => void fetchNextPage()}
          >
            {isFetchingNextPage ? t('common.loading') : t('history.more')}
          </Button>
        )}
      </div>
    </PageContainer>
  );
}
